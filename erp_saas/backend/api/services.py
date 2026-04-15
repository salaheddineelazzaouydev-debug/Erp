from finance.models import Invoice


class InvoiceService:
    @staticmethod
    def create_invoice(data, tenant_id):
        customer = data.get("customer")
        total = data.get("total")

        return Invoice.objects.create(
            customer=customer,
            total=total,
            status="draft",
            tenant_id=tenant_id,
        )
