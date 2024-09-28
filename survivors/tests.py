import json
import time

from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Gender,
    Survivor,
    LocationLog,
    InfectionReport,
    InventoryItem,
)
from resources.models import Resource


class GendersListAPIViewTestCase(APITestCase):
    @property
    def url(self):
        return reverse("genders")

    def setUp(self):
        self.genders = baker.make(Gender, _quantity=10)

    def test_get(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res_data = res.json()
        expected_data = [{"id": g.id, "name": g.name} for g in self.genders]

        self.assertListEqual(expected_data, res_data)


class LocationLogsListAPIViewTestCase(APITestCase):
    @property
    def url(self):
        return reverse("location-logs")

    def setUp(self):
        self.survivors = baker.make(Survivor, _quantity=10)

        self.outdated_locations = [
            baker.make(LocationLog, survivor=survivor) for survivor in self.survivors
        ]
        time.sleep(1)
        self.up_to_date_locations = [
            baker.make(LocationLog, survivor=survivor) for survivor in self.survivors
        ]

    def test_get(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res_data = res.json()
        expected_data = [
            {
                "id": l.id,
                "latitude": l.latitude,
                "longitude": l.longitude,
                "created_at": l.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }
            for l in self.up_to_date_locations
        ]
        for item in res_data:
            item.pop("survivor")

        self.assertListEqual(expected_data, res_data)


class SurvivorsListCreateAPIView(APITestCase):
    @property
    def url(self):
        return reverse("survivors")

    def setUp(self):
        self.genders = baker.make(Gender, _quantity=2)
        self.resources = baker.make(Resource, _quantity=2)
        self.survivors = baker.make(Survivor, gender=self.genders[0], _quantity=5)
        self.survivors.extend(baker.make(Survivor, gender=self.genders[1], _quantity=5))

    def test_get(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res_data = res.json()
        expected_data = [
            {
                "id": s.id,
                "name": s.name,
                "age": s.age,
                "gender": s.gender.name,
                "is_infected": s.is_infected,
            }
            for s in self.survivors
        ]

        self.assertListEqual(expected_data, res_data)

    def test_post(self):
        data = {
            "name": "Survivor 123",
            "age": 32,
            "gender_id": self.genders[0].id,
            "inventory_items": [
                {
                    "resource_id": r.id,
                    "quantity": 2,
                }
                for r in self.resources
            ],
        }

        res = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        survivor_id = res.json()["id"]
        survivors = Survivor.objects.filter(id=survivor_id)
        self.assertTrue(survivors.exists())
        survivor = survivors.first()
        self.assertFalse(survivor.is_infected)
        self.assertEqual("Survivor 123", survivor.name)
        self.assertEqual(self.genders[0].id, survivor.gender_id)
        inventory_items = survivor.inventory_items.all()
        self.assertEqual(len(inventory_items), 2)


class SurvivorInfectionReportsCreateAPIViewTestCase(APITestCase):
    @property
    def url(self):
        return reverse(
            "survivor-infection-reports", kwargs={"pk": self.suspected_survivor.id}
        )

    def setUp(self):
        self.suspected_survivor = baker.make(Survivor, is_infected=False)

    def test_post(self):
        report_author = baker.make(Survivor, is_infected=False)

        res = self.client.post(
            self.url,
            json.dumps({"author_id": report_author.id}),
            content_type="application/json",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            InfectionReport.objects.filter(
                author=report_author, infected_survivor=self.suspected_survivor
            ).exists()
        )
        self.suspected_survivor.refresh_from_db()
        self.assertFalse(self.suspected_survivor.is_infected)

        self.client.post(
            self.url,
            json.dumps({"author_id": baker.make(Survivor, is_infected=False).id}),
            content_type="application/json",
        )

        self.suspected_survivor.refresh_from_db()
        self.assertFalse(self.suspected_survivor.is_infected)

        self.client.post(
            self.url,
            json.dumps({"author_id": baker.make(Survivor, is_infected=False).id}),
            content_type="application/json",
        )

        self.suspected_survivor.refresh_from_db()
        self.assertEqual(
            3,
            InfectionReport.objects.filter(
                infected_survivor=self.suspected_survivor
            ).count(),
        )
        self.assertTrue(self.suspected_survivor.is_infected)

    def test_post_infected_author(self):
        report_author = baker.make(Survivor, is_infected=True)

        res = self.client.post(
            self.url,
            json.dumps({"author_id": report_author.id}),
            content_type="application/json",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_duplicate(self):
        report_author = baker.make(Survivor, is_infected=False)

        res = self.client.post(
            self.url,
            json.dumps({"author_id": report_author.id}),
            content_type="application/json",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.post(
            self.url,
            json.dumps({"author_id": report_author.id}),
            content_type="application/json",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class SurvivorLocationLogsCreateAPIViewTestCase(APITestCase):
    @property
    def url(self):
        return reverse("survivor-location-logs", kwargs={"pk": self.survivor.id})

    def setUp(self):
        self.survivor = baker.make(Survivor, is_infected=False)

    def test_post(self):
        data = {
            "latitude": 123.456,
            "longitude": 789.012,
        }

        res = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        location_log_id = res.json()["id"]
        location_logs = LocationLog.objects.filter(id=location_log_id)
        self.assertTrue(location_logs.exists())
        location_log = location_logs.first()
        self.assertEqual(self.survivor.id, location_log.survivor_id)
        self.assertEqual(123.456, location_log.latitude)
        self.assertEqual(789.012, location_log.longitude)

    def test_post_infected(self):
        self.survivor.is_infected = True
        self.survivor.save()
        data = {
            "latitude": 123.456,
            "longitude": 789.012,
        }

        res = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class SurvivorInventoryListAPIViewTestCase(APITestCase):
    @property
    def url(self):
        return reverse("survivor-inventory", kwargs={"pk": self.survivor.id})

    def setUp(self):
        self.survivor = baker.make(Survivor, is_infected=False)
        self.resources = baker.make(Resource, _quantity=10)
        self.inventory_items = [
            baker.make(InventoryItem, owner=self.survivor, resource=r)
            for r in self.resources
        ]

    def test_get(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res_data = res.json()
        expected_data = [
            {
                "id": self.inventory_items[i].id,
                "resource": self.resources[i].name,
                "resource_price": "{:.2f}".format(self.resources[i].price),
                "quantity": self.inventory_items[i].quantity,
            }
            for i in range(10)
        ]

        self.assertListEqual(expected_data, res_data)


class TradeAPIViewTestCase(APITestCase):
    @property
    def url(self):
        return reverse("trade", kwargs={"pk": self.survivor.id})

    def setUp(self):
        self.survivor = baker.make(Survivor, is_infected=False)
        self.resources = baker.make(Resource, price=1, _quantity=10)
        self.survivor_inventory_items = [
            baker.make(InventoryItem, owner=self.survivor, resource=r, quantity=4)
            for r in self.resources[:5]
        ]

        self.partner = baker.make(Survivor, is_infected=False)
        self.partner_inventory_items = [
            baker.make(InventoryItem, owner=self.partner, resource=r, quantity=2)
            for r in self.resources
        ]

    def test_post(self):
        data = {
            "partner_id": self.partner.id,
            "offered_items": [
                {
                    "resource_id": r.id,
                    "quantity": 2,
                }
                for r in self.resources[:5]
            ],
            "requested_items": [
                {
                    "resource_id": r.id,
                    "quantity": 1,
                }
                for r in self.resources
            ],
        }

        res = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(
            5,
            InventoryItem.objects.filter(
                owner=self.survivor, resource__in=self.resources[:5], quantity=3
            ).count(),
        )
        self.assertEqual(
            5,
            InventoryItem.objects.filter(
                owner=self.survivor, resource__in=self.resources[5:], quantity=1
            ).count(),
        )
        self.assertEqual(
            5,
            InventoryItem.objects.filter(
                owner=self.partner, resource__in=self.resources[:5], quantity=3
            ).count(),
        )
        self.assertEqual(
            5,
            InventoryItem.objects.filter(
                owner=self.partner, resource__in=self.resources[5:], quantity=1
            ).count(),
        )

    def test_post_missing_resources(self):
        data = {
            "partner_id": self.partner.id,
            "offered_items": [
                {
                    "resource_id": r.id,
                    "quantity": 1,
                }
                for r in self.resources
            ],
            "requested_items": [
                {
                    "resource_id": r.id,
                    "quantity": 1,
                }
                for r in self.resources
            ],
        }

        res = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_not_equal_trade(self):
        data = {
            "partner_id": self.partner.id,
            "offered_items": [
                {
                    "resource_id": r.id,
                    "quantity": 1,
                }
                for r in self.resources[:5]
            ],
            "requested_items": [
                {
                    "resource_id": r.id,
                    "quantity": 1,
                }
                for r in self.resources
            ],
        }

        res = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
