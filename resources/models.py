from decimal import Decimal

from django.db import models

from utils.models import BaseModel


class Resource(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(default=Decimal("0.0"), max_digits=5, decimal_places=2)

    def __str__(self):
        return self.name
