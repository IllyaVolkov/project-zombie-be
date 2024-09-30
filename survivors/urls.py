from django.urls import path, include
from .views import (
    GendersListAPIView,
    LocationLogsListAPIView,
    SurvivorsListCreateAPIView,
    SurvivorInventoryListAPIView,
    SurvivorLocationLogsCreateAPIView,
    SurvivorInfectionReportsCreateAPIView,
    TradeAPIView,
)


survivor_details_urlpatterns = [
    path(
        "inventory-items/",
        SurvivorInventoryListAPIView.as_view(),
        name="survivor-inventory",
    ),
    path(
        "location-logs/",
        SurvivorLocationLogsCreateAPIView.as_view(),
        name="survivor-location-logs",
    ),
    path(
        "infection-reports/",
        SurvivorInfectionReportsCreateAPIView.as_view(),
        name="survivor-infection-reports",
    ),
    path("trade", TradeAPIView.as_view(), name="trade"),
]


urlpatterns = [
    path("", SurvivorsListCreateAPIView.as_view(), name="survivors"),
    path("<int:pk>/", include(survivor_details_urlpatterns)),
    path("genders", GendersListAPIView.as_view(), name="genders"),
    path("location-logs", LocationLogsListAPIView.as_view(), name="location-logs"),
]
