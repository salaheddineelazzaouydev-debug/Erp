import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.tenant_schema import ensure_schema_exists, normalize_schema_name


class User(AbstractUser):
    """Custom user model with tenant awareness."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.email or self.username


class Organization(models.Model):
    """Organization/Tenant model representing a company in the SaaS."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    schema_name = models.CharField(max_length=63, unique=True, db_index=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_organizations")
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    employee_count = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations'
        ordering = ['-created_at']
        verbose_name_plural = 'Organizations'

    def save(self, *args, **kwargs):
        if not self.schema_name:
            self.schema_name = normalize_schema_name(self.name)
        else:
            self.schema_name = normalize_schema_name(self.schema_name)

        super().save(*args, **kwargs)
        ensure_schema_exists(self.schema_name)

    def __str__(self) -> str:
        return self.name


class OrganizationMember(models.Model):
    """Model to track users membership in organizations with roles."""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='invitations_sent'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'organization_members'
        unique_together = ['organization', 'user']
        ordering = ['-joined_at']

    def __str__(self) -> str:
        return f"{self.user.email} - {self.organization.name} ({self.role})"


class Invitation(models.Model):
    """Model for tracking organization invitations."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=OrganizationMember.ROLE_CHOICES, default='member')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invitations'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Invitation for {self.email} to {self.organization.name}"
