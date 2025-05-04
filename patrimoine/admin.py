#mysite/patrimoine/admin.py
#----

from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .resources import LotResource
from .models import Immeuble, Lot

admin.site.register(Immeuble)

@admin.register(Lot)
class LotAdmin(ImportExportModelAdmin):
    resource_class = LotResource
    list_display = ('code', 'immeuble')
