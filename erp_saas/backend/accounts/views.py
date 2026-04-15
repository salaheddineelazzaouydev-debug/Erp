"""
Views for accounts app - handling authentication, user management, 
organizations, and invitations with JWT token support.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django.db import transaction
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Organization, OrganizationMember, Invitation
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    ChangePasswordSerializer, OrganizationSerializer,
    OrganizationCreateSerializer, OrganizationMemberSerializer,
    OrganizationMemberCreateSerializer, InvitationSerializer,
    InvitationCreateSerializer, AcceptInvitationSerializer
)

User = get_user_model()


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners of an object to edit it."""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return hasattr(obj, 'owner') and obj.owner == request.user


class IsOrganizationMember(permissions.BasePermission):
    """Permission to check if user is a member of the organization."""
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Organization):
            organization = obj
        elif hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            return False
        
        return OrganizationMember.objects.filter(
            user=request.user,
            organization=organization,
            is_active=True
        ).exists()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view that includes user data in response."""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = User.objects.get(email=request.data.get('email'))
            response.data['user'] = UserSerializer(user).data
            # Add organizations list
            memberships = OrganizationMember.objects.filter(
                user=user, is_active=True
            ).select_related('organization')
            response.data['organizations'] = [
                {
                    'id': m.organization.id,
                    'name': m.organization.name,
                    'role': m.role
                }
                for m in memberships
            ]
        return response


class RegisterView(generics.CreateAPIView):
    """API endpoint for user registration."""
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """API endpoint for viewing and updating current user profile."""
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserSerializer
        return UserUpdateSerializer


class ChangePasswordView(generics.UpdateAPIView):
    """API endpoint for changing user password."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {"old_password": "Wrong password."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({"message": "Password changed successfully."})


class OrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing organizations."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Return organizations where user is a member
        return Organization.objects.filter(
            members__user=self.request.user,
            members__is_active=True
        ).distinct()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrganizationCreateSerializer
        return OrganizationSerializer
    
    def perform_create(self, serializer):
        with transaction.atomic():
            organization = serializer.save()
            # Make the creator an owner member
            OrganizationMember.objects.create(
                organization=organization,
                user=self.request.user,
                role='owner',
                invited_by=self.request.user
            )
            # Set user's tenant_id to this organization
            self.request.user.tenant_id = organization.id
            self.request.user.save()


class OrganizationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Detailed view for a single organization."""
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    
    def get_queryset(self):
        return Organization.objects.filter(
            members__user=self.request.user,
            members__is_active=True
        ).distinct()


class OrganizationMemberViewSet(viewsets.ModelViewSet):
    """ViewSet for managing organization members."""
    serializer_class = OrganizationMemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    
    def get_queryset(self):
        organization_pk = self.kwargs.get('organization_pk')
        return OrganizationMember.objects.filter(
            organization_id=organization_pk,
            is_active=True
        ).select_related('user', 'invited_by')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        organization_pk = self.kwargs.get('organization_pk')
        context['organization'] = Organization.objects.get(pk=organization_pk)
        return context


class OrganizationMemberAddView(generics.CreateAPIView):
    """API endpoint for adding a member to an organization."""
    serializer_class = OrganizationMemberCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        organization_pk = self.kwargs.get('organization_pk')
        context['organization'] = Organization.objects.get(pk=organization_pk)
        return context
    
    def get_queryset(self):
        organization_pk = self.kwargs.get('organization_pk')
        return OrganizationMember.objects.filter(organization_id=organization_pk)
    
    def perform_create(self, serializer):
        # Only owners and admins can add members
        organization = Organization.objects.get(pk=self.kwargs.get('organization_pk'))
        member_role = OrganizationMember.objects.get(
            user=self.request.user,
            organization=organization
        ).role
        
        if member_role not in ['owner', 'admin']:
            raise permissions.PermissionDenied(
                "Only owners and admins can add members."
            )
        
        serializer.save()


class InvitationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing invitations."""
    serializer_class = InvitationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    
    def get_queryset(self):
        organization_pk = self.kwargs.get('organization_pk')
        return Invitation.objects.filter(
            organization_id=organization_pk
        ).select_related('invited_by', 'organization')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        organization_pk = self.kwargs.get('organization_pk')
        context['organization'] = Organization.objects.get(pk=organization_pk)
        return context


class InvitationCreateView(generics.CreateAPIView):
    """API endpoint for creating invitations."""
    serializer_class = InvitationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        organization_pk = self.kwargs.get('organization_pk')
        context['organization'] = Organization.objects.get(pk=organization_pk)
        return context
    
    def perform_create(self, serializer):
        # Only owners and admins can invite
        organization = Organization.objects.get(pk=self.kwargs.get('organization_pk'))
        member_role = OrganizationMember.objects.get(
            user=self.request.user,
            organization=organization
        ).role
        
        if member_role not in ['owner', 'admin']:
            raise permissions.PermissionDenied(
                "Only owners and admins can send invitations."
            )
        
        serializer.save()


class AcceptInvitationView(APIView):
    """API endpoint for accepting an invitation."""
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        invitation = Invitation.objects.get(token=serializer.validated_data['token'])
        
        # Check if email matches authenticated user
        if invitation.email != request.user.email:
            return Response(
                {"error": "Invitation email does not match your account."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add user to organization
        OrganizationMember.objects.create(
            organization=invitation.organization,
            user=request.user,
            role=invitation.role,
            invited_by=invitation.invited_by
        )
        
        # Update invitation status
        invitation.status = 'accepted'
        invitation.save()
        
        # If this is user's first organization, set as tenant
        if not request.user.tenant_id:
            request.user.tenant_id = invitation.organization.id
            request.user.save()
        
        return Response({
            "message": "Invitation accepted successfully.",
            "organization": OrganizationSerializer(invitation.organization).data
        })


class DeclineInvitationView(APIView):
    """API endpoint for declining an invitation."""
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        token = request.data.get('token')
        
        try:
            invitation = Invitation.objects.get(token=token)
        except Invitation.DoesNotExist:
            return Response(
                {"error": "Invalid invitation token."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if invitation.email != request.user.email:
            return Response(
                {"error": "Invitation email does not match your account."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        invitation.status = 'declined'
        invitation.save()
        
        return Response({"message": "Invitation declined."})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_organizations(request):
    """Get all organizations the current user belongs to."""
    memberships = OrganizationMember.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('organization')
    
    data = [
        {
            'id': m.organization.id,
            'name': m.organization.name,
            'schema_name': m.organization.schema_name,
            'role': m.role,
            'joined_at': m.joined_at,
            'logo': m.organization.logo.url if m.organization.logo else None,
        }
        for m in memberships
    ]
    
    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def switch_organization(request, organization_id):
    """Switch current user's active organization/tenant."""
    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        return Response(
            {"error": "Organization not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user is a member
    if not OrganizationMember.objects.filter(
        user=request.user,
        organization=organization,
        is_active=True
    ).exists():
        return Response(
            {"error": "You are not a member of this organization."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    request.user.tenant_id = organization.id
    request.user.save()
    
    return Response({
        "message": "Organization switched successfully.",
        "organization": OrganizationSerializer(organization).data
    })
