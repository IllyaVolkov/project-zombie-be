from django.urls import path
from .views import ResourcesListAPIView


urlpatterns = [
    path("", ResourcesListAPIView.as_view(), name="resources"),
]
