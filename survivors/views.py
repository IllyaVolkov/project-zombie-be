from django.db.models import Max, F
from django.db import transaction
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    CreateAPIView,
)
from rest_framework.response import Response


from .models import Gender, LocationLog, Survivor, InventoryItem
from .serializers import (
    GenderSerializer,
    InfectionReportSerializer,
    InventoryItemSerializer,
    SurvivorLocationLogSerializer,
    SurvivorSerializer,
    TradeSerializer,
)
from resources.models import Resource


class GendersListAPIView(ListAPIView):
    serializer_class = GenderSerializer

    def get_queryset(self):
        return Gender.objects.all()


class LocationLogsListAPIView(ListAPIView):
    serializer_class = SurvivorLocationLogSerializer

    def get_queryset(self):
        return (
            LocationLog.objects.annotate(
                latest_created_at=Max("survivor__location_logs__created_at")
            )
            .filter(created_at=F("latest_created_at"))
            .select_related("survivor")
        )


class SurvivorsListCreateAPIView(ListCreateAPIView):
    serializer_class = SurvivorSerializer

    def get_queryset(self):
        return Survivor.objects.select_related("gender")


class SurvivorInfectionReportsCreateAPIView(CreateAPIView):
    serializer_class = InfectionReportSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data={"infected_survivor_id": kwargs["pk"], **request.data}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class SurvivorLocationLogsCreateAPIView(CreateAPIView):
    serializer_class = SurvivorLocationLogSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data={"survivor_id": kwargs["pk"], **request.data}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class SurvivorInventoryListAPIView(ListAPIView):
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        return InventoryItem.objects.select_related("resource")

    def filter_queryset(self, queryset):
        return queryset.filter(owner_id=self.kwargs["pk"])


class TradeAPIView(GenericAPIView):
    serializer_class = TradeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data={"survivor_id": kwargs["pk"], **request.data}
        )
        serializer.is_valid(raise_exception=True)

        survivor = serializer.validated_data["survivor_id"]
        partner = serializer.validated_data["partner_id"]

        resources = Resource.objects.values("name", "id")
        resource_id_map = {r["name"]: r["id"] for r in resources}
        survivor_items = {
            item.resource.name: item
            for item in survivor.inventory_items.select_related("resource")
        }
        partner_items = {
            item.resource.name: item
            for item in partner.inventory_items.select_related("resource")
        }
        inventory_items_bulk_create_list = []
        inventory_items_bulk_update_list = []
        inventory_items_bulk_delete_list = []

        for item in serializer.validated_data["offered_items"]:
            survivor_item_obj = survivor_items[item["resource"].name]

            if survivor_item_obj.quantity > item["quantity"]:
                survivor_item_obj.quantity -= item["quantity"]
                inventory_items_bulk_update_list.append(survivor_item_obj)
            else:
                inventory_items_bulk_delete_list.append(survivor_item_obj)

            partner_item_obj = partner_items.get(item["resource"].name)
            if partner_item_obj:
                partner_item_obj.quantity += item["quantity"]
                inventory_items_bulk_update_list.append(partner_item_obj)
            else:
                inventory_items_bulk_create_list.append(
                    InventoryItem(
                        owner=partner,
                        resource_id=resource_id_map[item["resource"].name],
                        quantity=item["quantity"],
                    )
                )

        for item in serializer.validated_data["requested_items"]:
            survivor_item_obj = survivor_items.get(item["resource"].name)
            if survivor_item_obj:
                survivor_item_obj = survivor_items[item["resource"].name]
                survivor_item_obj.quantity += item["quantity"]
                if survivor_item_obj not in inventory_items_bulk_update_list:
                    inventory_items_bulk_update_list.append(survivor_item_obj)
            else:
                inventory_items_bulk_create_list.append(
                    InventoryItem(
                        owner=survivor,
                        resource_id=resource_id_map[item["resource"].name],
                        quantity=item["quantity"],
                    )
                )

            partner_item_obj = partner_items[item["resource"].name]
            if partner_item_obj.quantity > item["quantity"]:
                partner_item_obj.quantity -= item["quantity"]
                if partner_item_obj not in inventory_items_bulk_update_list:
                    inventory_items_bulk_update_list.append(partner_item_obj)
            else:
                inventory_items_bulk_delete_list.append(partner_item_obj)

        with transaction.atomic():
            InventoryItem.objects.filter(
                resource_id__in=[
                    i.resource_id for i in inventory_items_bulk_delete_list
                ]
            ).delete()
            InventoryItem.objects.bulk_create(inventory_items_bulk_create_list)
            InventoryItem.objects.bulk_update(
                inventory_items_bulk_update_list, ["quantity"]
            )

        return Response(serializer.data, status=status.HTTP_200_OK)
