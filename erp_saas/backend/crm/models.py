from django.db import models
from core.models import TenantAwareModel


class Customer(TenantAwareModel):
    name = models.CharField(max_length=255)
    email = models.EmailField()

    def __str__(self) -> str:
        return self.name
