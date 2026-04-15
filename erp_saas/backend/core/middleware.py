from .tenant_schema import reset_connection_schema, set_connection_schema


class TenantSchemaMiddleware:
    """Switch PostgreSQL search_path per request using X-Tenant-Schema header."""

    header_name = "HTTP_X_TENANT_SCHEMA"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        schema_name = request.META.get(self.header_name)
        if schema_name:
            set_connection_schema(schema_name)

        try:
            return self.get_response(request)
        finally:
            reset_connection_schema()
