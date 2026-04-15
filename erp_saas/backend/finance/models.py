from django.db import models
from core.models import TenantAwareModel


class Account(TenantAwareModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)


class JournalEntry(TenantAwareModel):
    date = models.DateField()


class EntryLine(TenantAwareModel):
    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="entry_lines")
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)


class Invoice(TenantAwareModel):
    customer = models.ForeignKey("crm.Customer", on_delete=models.CASCADE, related_name="invoices")
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)
