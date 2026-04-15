"""
Tests for accounts app - authentication, organizations, and invitations.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Organization, OrganizationMember, Invitation

User = get_user_model()


class UserRegistrationTest(TestCase):
    """Test user registration endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
    
    def test_register_user_success(self):
        """Test successful user registration."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'test@example.com')
    
    def test_register_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = {
            'username': 'testuser2',
            'email': 'test2@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'DifferentPass123!',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)


class OrganizationTest(TestCase):
    """Test organization CRUD operations."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='orgowner',
            email='owner@example.com',
            password='SecurePass123!'
        )
        self.client.force_authenticate(user=self.user)
        self.org_create_url = reverse('organization-list')
    
    def test_create_organization(self):
        """Test creating a new organization."""
        data = {
            'name': 'Test Company',
            'description': 'A test company',
            'industry': 'Technology',
            'employee_count': 10
        }
        response = self.client.post(self.org_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Company')
        
        # Verify user is added as owner member
        org = Organization.objects.get(id=response.data['id'])
        member = OrganizationMember.objects.get(organization=org, user=self.user)
        self.assertEqual(member.role, 'owner')
    
    def test_list_organizations(self):
        """Test listing user's organizations."""
        # Create an organization
        org = Organization.objects.create(
            name='Test Org',
            owner=self.user
        )
        OrganizationMember.objects.create(
            organization=org,
            user=self.user,
            role='owner'
        )
        
        response = self.client.get(self.org_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class InvitationTest(TestCase):
    """Test invitation functionality."""
    
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='SecurePass123!'
        )
        self.org = Organization.objects.create(
            name='Test Org',
            owner=self.owner
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.owner,
            role='owner'
        )
        self.client.force_authenticate(user=self.owner)
    
    def test_create_invitation(self):
        """Test creating an invitation."""
        url = reverse('invitation-create', kwargs={'organization_pk': self.org.id})
        data = {
            'email': 'newmember@example.com',
            'role': 'member'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newmember@example.com')
        self.assertEqual(response.data['role'], 'member')
    
    def test_accept_invitation(self):
        """Test accepting an invitation."""
        # Create invitation
        invitation = Invitation.objects.create(
            organization=self.org,
            email='invitee@example.com',
            role='member',
            invited_by=self.owner
        )
        
        # Create user and accept invitation
        invitee = User.objects.create_user(
            username='invitee',
            email='invitee@example.com',
            password='SecurePass123!'
        )
        self.client.force_authenticate(user=invitee)
        
        url = reverse('invitation-accept')
        data = {'token': str(invitation.token)}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify membership created
        self.assertTrue(
            OrganizationMember.objects.filter(
                organization=self.org,
                user=invitee
            ).exists()
        )


class SwitchOrganizationTest(TestCase):
    """Test switching between organizations."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='multiorg',
            email='multi@example.com',
            password='SecurePass123!'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create two organizations
        self.org1 = Organization.objects.create(name='Org 1', owner=self.user)
        self.org2 = Organization.objects.create(name='Org 2', owner=self.user)
        
        OrganizationMember.objects.bulk_create([
            OrganizationMember(organization=self.org1, user=self.user, role='owner'),
            OrganizationMember(organization=self.org2, user=self.user, role='owner'),
        ])
    
    def test_switch_organization(self):
        """Test switching active organization."""
        url = reverse('switch-organization', kwargs={'organization_id': self.org2.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user's tenant_id updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.tenant_id, self.org2.id)
