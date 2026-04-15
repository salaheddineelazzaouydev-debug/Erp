"""
Serializers for accounts app - handling user, organization, and invitation data.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers

from .models import Organization, OrganizationMember, Invitation

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'avatar', 'is_verified', 'tenant_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'avatar'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password."""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        return attrs


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model."""
    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'schema_name', 'owner', 'description',
            'logo', 'website', 'industry', 'employee_count',
            'is_active', 'member_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'schema_name', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an organization."""

    class Meta:
        model = Organization
        fields = ['name', 'description', 'website', 'industry', 'employee_count']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['owner'] = request.user
        return super().create(validated_data)


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """Serializer for OrganizationMember model."""
    user = UserSerializer(read_only=True)
    invited_by = UserSerializer(read_only=True)

    class Meta:
        model = OrganizationMember
        fields = [
            'id', 'organization', 'user', 'role', 'joined_at',
            'invited_by', 'is_active'
        ]
        read_only_fields = ['id', 'joined_at']


class OrganizationMemberCreateSerializer(serializers.ModelSerializer):
    """Serializer for adding a member to an organization."""
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = OrganizationMember
        fields = ['user_id', 'role']

    def create(self, validated_data):
        user_id = validated_data.pop('user_id')
        organization = self.context.get('organization')
        user = User.objects.get(id=user_id)
        
        # Check if user is already a member
        if OrganizationMember.objects.filter(
            organization=organization, 
            user=user, 
            is_active=True
        ).exists():
            raise serializers.ValidationError("User is already a member of this organization.")
        
        validated_data['organization'] = organization
        validated_data['user'] = user
        validated_data['invited_by'] = self.context.get('request').user
        return super().create(validated_data)


class InvitationSerializer(serializers.ModelSerializer):
    """Serializer for Invitation model."""
    invited_by = UserSerializer(read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Invitation
        fields = [
            'id', 'organization', 'organization_name', 'email', 'role',
            'token', 'status', 'invited_by', 'expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'token', 'status', 'expires_at', 'created_at', 'invited_by']


class InvitationCreateSerializer(serializers.Serializer):
    """Serializer for creating an invitation."""
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(
        choices=OrganizationMember.ROLE_CHOICES,
        default='member'
    )

    def validate_email(self, value):
        # Check if user already exists
        if User.objects.filter(email=value).exists():
            # Check if already a member
            organization = self.context.get('organization')
            if OrganizationMember.objects.filter(
                user__email=value,
                organization=organization,
                is_active=True
            ).exists():
                raise serializers.ValidationError("User is already a member of this organization.")
        
        # Check if pending invitation exists
        organization = self.context.get('organization')
        if Invitation.objects.filter(
            email=value,
            organization=organization,
            status='pending'
        ).exists():
            raise serializers.ValidationError("An invitation has already been sent to this email.")
        
        return value

    def create(self, validated_data):
        organization = self.context.get('organization')
        request = self.context.get('request')
        
        invitation = Invitation.objects.create(
            organization=organization,
            email=validated_data['email'],
            role=validated_data['role'],
            invited_by=request.user,
            expires_at=timezone.now() + timedelta(days=7)
        )
        return invitation


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer for accepting an invitation."""
    token = serializers.UUIDField(required=True)

    def validate_token(self, value):
        try:
            invitation = Invitation.objects.get(token=value)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation token.")
        
        if invitation.status != 'pending':
            raise serializers.ValidationError(f"Invitation is already {invitation.status}.")
        
        if invitation.expires_at < timezone.now():
            invitation.status = 'expired'
            invitation.save()
            raise serializers.ValidationError("Invitation has expired.")
        
        return value
