from rest_framework import serializers
from finance.models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "customer", "total", "status", "tenant_id", "created_at"]
        read_only_fields = ["id", "tenant_id", "created_at"]
