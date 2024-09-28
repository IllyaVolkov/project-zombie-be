from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Resource


class ResourcesListAPIViewTestCase(APITestCase):
    @property
    def url(self):
        return reverse("resources")

    def setUp(self):
        self.resources = baker.make(Resource, _quantity=10)

    def test_get(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res_data = res.json()
        expected_data = [
            {"id": r.id, "name": r.name, "price": "{:.2f}".format(r.price)}
            for r in self.resources
        ]

        self.assertListEqual(expected_data, res_data)
