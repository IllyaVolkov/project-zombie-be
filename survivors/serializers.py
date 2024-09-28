from django.db import transaction
from rest_framework import serializers

from .models import (
    Gender,
    Survivor,
    LocationLog,
    InfectionReport,
    InventoryItem,
)
from resources.models import Resource


def validate_survivor_not_infected(value):
    survivor = Survivor.objects.get(id=value)
    if survivor.is_infected:
        raise serializers.ValidationError(
            ["Infected survivors cannot perform such action."]
        )
    return value


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gender
        fields = ["id", "name"]


class LocationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationLog
        fields = ["id", "latitude", "longitude", "created_at"]
        read_only_fields = ["created_at", "updated_at"]


class InventoryItemSerializer(serializers.ModelSerializer):
    resource = serializers.CharField(source="resource.name", read_only=True)
    resource_price = serializers.DecimalField(
        max_digits=5, decimal_places=2, source="resource.price", read_only=True
    )
    resource_id = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all(), write_only=True
    )

    class Meta:
        model = InventoryItem
        fields = ["id", "resource", "resource_price", "resource_id", "quantity"]
        read_only_fields = ["id"]


class SurvivorSerializer(serializers.ModelSerializer):
    gender = serializers.CharField(source="gender.name", read_only=True)
    gender_id = serializers.PrimaryKeyRelatedField(
        queryset=Gender.objects.all(), write_only=True
    )
    resources = InventoryItemSerializer(many=True, write_only=True)

    class Meta:
        model = Survivor
        fields = [
            "id",
            "name",
            "age",
            "gender",
            "gender_id",
            "resources",
            "is_infected",
        ]
        read_only_fields = ["created_at", "updated_at"]

    @transaction.atomic
    def create(self, validated_data):
        resources = validated_data.pop("resources")
        instance = Survivor.objects.create(**validated_data)
        inventory_items = [
            InventoryItem(survivor=instance, **resource_data)
            for resource_data in resources
        ]
        InventoryItem.objects.bulk_create(inventory_items)
        return instance


class SurvivorLocationLogSerializer(LocationLogSerializer):
    survivor = SurvivorSerializer(read_only=True)
    survivor_id = serializers.PrimaryKeyRelatedField(
        queryset=Survivor.objects.all(), write_only=True
    )

    validate_survivor_id = validate_survivor_not_infected

    class Meta(LocationLogSerializer.Meta):
        fields = [*LocationLogSerializer.Meta.fields, "survivor"]


class InfectionReportSerializer(serializers.ModelSerializer):
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Survivor.objects.all(), write_only=True
    )
    infected_survivor_id = serializers.PrimaryKeyRelatedField(
        queryset=Survivor.objects.all(), write_only=True
    )

    validate_author_id = validate_survivor_not_infected

    class Meta:
        model = InfectionReport
        fields = ["author_id", "infected_survivor_id"]

    def validate(self, attrs):
        author_id = attrs.get("author_id")
        infected_survivor_id = attrs.get("infected_survivor_id")

        if InfectionReport.objects.filter(
            author_id=author_id, infected_survivor_id=infected_survivor_id
        ).exists():
            raise serializers.ValidationError(
                {"infected_survivor_id": ["You cannot report same survivor twice!"]}
            )
        return super().validate(attrs)

    @transaction.atomic
    def create(self, validated_data):
        instance = super().create(validated_data)
        potentially_infected_survivor = instance.infected_survivor
        if potentially_infected_survivor.infection_reports.count >= 3:
            potentially_infected_survivor.is_infected = True
            potentially_infected_survivor.save()
        return instance


class TradeSerializer(serializers.Serializer):
    survivor_id = serializers.PrimaryKeyRelatedField(
        queryset=Survivor.objects.all(), write_only=True
    )
    partner_id = serializers.PrimaryKeyRelatedField(
        queryset=Survivor.objects.all(), write_only=True
    )
    offered_items = InventoryItemSerializer(many=True, write_only=True)
    requested_items = InventoryItemSerializer(many=True, write_only=True)

    validate_survivor_id = validate_survivor_not_infected
    validate_partner_id = validate_survivor_not_infected

    def validate_offered_items(self, value):
        survivor = Survivor.objects.get(id=self.initial_data["survivor_id"])

        for item in value:
            if not survivor.inventory_items.filter(
                resource__name=item["name"], quantity__lte=item["quantity"]
            ).exists():
                raise serializers.ValidationError(
                    {
                        "offered_items": [
                            "Some offered items are missing from survivor's inventory."
                        ]
                    }
                )
        return value

    def validate_requested_items(self, value):
        partner = Survivor.objects.get(id=self.initial_data["partner_id"])

        for item in value:
            if not partner.inventory_items.filter(
                resource__name=item["name"], quantity__lte=item["quantity"]
            ).exists():
                raise serializers.ValidationError(
                    {
                        "requested_items": [
                            "Some requested items are missing from partner's inventory."
                        ]
                    }
                )
        return value

    def validate(self, attrs):
        resources = Resource.objects.values("name", "price")
        resource_price_map = {r["name"]: r["price"] for r in resources}

        offered_value = sum(
            [
                resource_price_map[item["name"]] * item["quantity"]
                for item in attrs["offered_items"]
            ]
        )
        requested_value = sum(
            [
                resource_price_map[item["name"]] * item["quantity"]
                for item in attrs["offered_items"]
            ]
        )
        if offered_value != requested_value:
            raise serializers.ValidationError(
                {
                    "requested_items": [
                        "Value of requested items does not match with offered items."
                    ]
                }
            )
        return super().validate(attrs)
