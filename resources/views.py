from rest_framework.generics import ListAPIView

from .models import Resource
from .serializers import ResourceSerializer


class ResourcesListAPIView(ListAPIView):
    serializer_class = ResourceSerializer

    def get_queryset(self):
        return Resource.objects.all()
