# Django ERP SaaS Boilerplate (Production-Ready)

## Stack
- Django 5
- Django REST Framework
- PostgreSQL
- Redis + Celery
- JWT Auth (SimpleJWT)
- Multi-tenancy via `tenant_id` + PostgreSQL schema per tenant

## Project Structure

```text
erp_saas/
├── backend/
│   ├── config/
│   ├── core/
│   ├── accounts/
│   ├── finance/
│   ├── crm/
│   ├── api/
│   └── manage.py
```

## Tenant Schema Support
- `accounts.Organization` stores a unique `schema_name` for each tenant.
- Schema names are normalized to valid PostgreSQL identifiers.
- Schema is auto-created after organization save.
- `TenantSchemaMiddleware` switches DB `search_path` using `X-Tenant-Schema` header.
- Connection search path resets to `public` after each request.

## Production Notes
- Use Nginx as reverse proxy.
- Add HTTPS (Let's Encrypt).
- Add Sentry for error tracking.
- Add structured logging (structlog).
- Backup PostgreSQL daily.
