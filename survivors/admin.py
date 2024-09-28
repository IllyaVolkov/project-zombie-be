from django.contrib import admin

from .models import (
    Gender,
    InfectionReport,
    InventoryItem,
    LocationLog,
    Survivor,
)


admin.site.register(Gender)
admin.site.register(InfectionReport)
admin.site.register(InventoryItem)
admin.site.register(LocationLog)
admin.site.register(Survivor)
