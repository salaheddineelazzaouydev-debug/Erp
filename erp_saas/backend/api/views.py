from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from finance.models import Invoice
from .serializers import InvoiceSerializer


class InvoiceViewSet(ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.request.user.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.user.tenant_id)
