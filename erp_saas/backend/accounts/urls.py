"""
URL routing for accounts app - authentication, user management, 
organizations, and invitations endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView, UserProfileView, ChangePasswordView,
    OrganizationViewSet, OrganizationDetailView,
    OrganizationMemberViewSet, OrganizationMemberAddView,
    InvitationViewSet, InvitationCreateView,
    AcceptInvitationView, DeclineInvitationView,
    my_organizations, switch_organization
)

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')

# Nested routers for organization members and invitations
organization_router = DefaultRouter()
organization_router.register(
    r'members',
    OrganizationMemberViewSet,
    basename='organization-member'
)
organization_router.register(
    r'invitations',
    InvitationViewSet,
    basename='organization-invitation'
)

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # Organizations
    path('', include(router.urls)),
    path('organizations/<uuid:pk>/', OrganizationDetailView.as_view(), name='organization-detail'),
    
    # Organization members management
    path(
        'organizations/<uuid:organization_pk>/members/add/',
        OrganizationMemberAddView.as_view(),
        name='organization-member-add'
    ),
    path(
        'organizations/<uuid:organization_pk>/',
        include(organization_router.urls)
    ),
    
    # Invitation creation
    path(
        'organizations/<uuid:organization_pk>/invitations/create/',
        InvitationCreateView.as_view(),
        name='invitation-create'
    ),
    
    # Accept/Decline invitation
    path('invitations/accept/', AcceptInvitationView.as_view(), name='invitation-accept'),
    path('invitations/decline/', DeclineInvitationView.as_view(), name='invitation-decline'),
    
    # User organization management
    path('my-organizations/', my_organizations, name='my-organizations'),
    path(
        'organizations/<uuid:organization_id>/switch/',
        switch_organization,
        name='switch-organization'
    ),
]
