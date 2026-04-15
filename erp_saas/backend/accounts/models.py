import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from core.tenant_schema import ensure_schema_exists, normalize_schema_name


class User(AbstractUser):
    tenant_id = models.UUIDField(db_index=True, null=True, blank=True)


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    schema_name = models.CharField(max_length=63, unique=True, db_index=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organizations")

    def save(self, *args, **kwargs):
        if not self.schema_name:
            self.schema_name = normalize_schema_name(self.name)
        else:
            self.schema_name = normalize_schema_name(self.schema_name)

        super().save(*args, **kwargs)
        ensure_schema_exists(self.schema_name)

    def __str__(self) -> str:
        return self.name
