# Accounts App - ERP SaaS

This app handles user authentication, organization management, and multi-tenancy for the ERP SaaS platform.

## Features

- **JWT Authentication**: Secure token-based authentication with access and refresh tokens
- **User Management**: Registration, profile management, password changes
- **Organization/Tenant Management**: Create and manage organizations (tenants)
- **Role-Based Access Control**: Owner, Admin, Manager, Member, Viewer roles
- **Invitation System**: Invite users to join organizations via email
- **Multi-Tenancy Support**: Schema-per-tenant architecture with tenant switching

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/token/` | Obtain JWT token pair | No |
| POST | `/api/token/refresh/` | Refresh access token | No |
| POST | `/api/auth/register/` | Register new user | No |
| GET | `/api/auth/profile/` | Get current user profile | Yes |
| PUT | `/api/auth/profile/` | Update user profile | Yes |
| PUT | `/api/auth/change-password/` | Change password | Yes |

### Organizations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/organizations/` | List user's organizations | Yes |
| POST | `/api/auth/organizations/` | Create new organization | Yes |
| GET | `/api/auth/organizations/{id}/` | Get organization details | Yes |
| PUT | `/api/auth/organizations/{id}/` | Update organization | Yes |
| DELETE | `/api/auth/organizations/{id}/` | Delete organization | Yes |
| POST | `/api/auth/organizations/{id}/switch/` | Switch active tenant | Yes |

### Organization Members

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/organizations/{org_id}/members/` | List members | Yes |
| POST | `/api/auth/organizations/{org_id}/members/add/` | Add member | Yes |
| PUT | `/api/auth/organizations/{org_id}/members/{id}/` | Update member role | Yes |
| DELETE | `/api/auth/organizations/{org_id}/members/{id}/` | Remove member | Yes |

### Invitations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/organizations/{org_id}/invitations/` | List invitations | Yes |
| POST | `/api/auth/organizations/{org_id}/invitations/create/` | Create invitation | Yes |
| POST | `/api/auth/invitations/accept/` | Accept invitation | Yes |
| POST | `/api/auth/invitations/decline/` | Decline invitation | Yes |

### User Organization Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/my-organizations/` | Get all user's orgs | Yes |

## Usage Examples

### Register a New User

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### Login and Get JWT Tokens

```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

### Create an Organization

```bash
curl -X POST http://localhost:8000/api/auth/organizations/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Acme Corporation",
    "description": "Leading innovator in widgets",
    "industry": "Manufacturing",
    "employee_count": 50
  }'
```

### Invite a User to Organization

```bash
curl -X POST http://localhost:8000/api/auth/organizations/ORG_UUID/invitations/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "email": "newmember@example.com",
    "role": "member"
  }'
```

### Accept Invitation

```bash
curl -X POST http://localhost:8000/api/auth/invitations/accept/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "token": "INVITATION_TOKEN_UUID"
  }'
```

### Switch Active Organization

```bash
curl -X POST http://localhost:8000/api/auth/organizations/ORG_UUID/switch/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Role Permissions

| Role | Can Add Members | Can Send Invitations | Can Edit Org | Can Delete Org |
|------|----------------|---------------------|--------------|----------------|
| Owner | ✅ | ✅ | ✅ | ✅ |
| Admin | ✅ | ✅ | ✅ | ❌ |
| Manager | ❌ | ❌ | ✅ | ❌ |
| Member | ❌ | ❌ | ❌ | ❌ |
| Viewer | ❌ | ❌ | ❌ | ❌ |

## Models

### User
- Custom user model extending Django's AbstractUser
- UUID primary key
- Tenant-aware with `tenant_id` field
- Additional fields: phone, avatar, is_verified

### Organization
- Represents a tenant/company in the SaaS
- Auto-creates database schema on save
- Fields: name, schema_name, owner, description, logo, website, industry, etc.

### OrganizationMember
- Links users to organizations with roles
- Tracks who invited whom and when they joined
- Unique constraint on (organization, user)

### Invitation
- Email-based invitations to join organizations
- Token-based acceptance mechanism
- 7-day expiration by default
- Status tracking: pending, accepted, declined, expired

## Security Notes

- All endpoints except registration and token obtain require authentication
- Password validation enforced on registration and password change
- JWT tokens have configurable expiration (default: 30 min access, 1 day refresh)
- Only owners and admins can invite new members
- Users can only accept invitations matching their email

## Running Tests

```bash
python manage.py test accounts
```
