from django.db import models

from resources.models import Resource
from utils.models import BaseModel


class Gender(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Survivor(BaseModel):
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, blank=True, null=True)
    is_infected = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class LocationLog(BaseModel):
    latitude = models.FloatField()
    longitude = models.FloatField()
    survivor = models.ForeignKey(Survivor, on_delete=models.CASCADE)


class InfectionReport(BaseModel):
    author = models.ForeignKey(Survivor, on_delete=models.CASCADE)
    infected_survivor = models.ForeignKey(
        Survivor, on_delete=models.CASCADE, related_name="infection_reports"
    )

    class Meta:
        unique_together = ("author", "infected_survivor")


class InventoryItem(BaseModel):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    owner = models.ForeignKey(
        Survivor, on_delete=models.CASCADE, related_name="inventory_items"
    )

    class Meta:
        unique_together = ("resource", "owner")
