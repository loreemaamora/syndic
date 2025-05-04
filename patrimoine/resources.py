# accounts/resources.py
from import_export import resources, fields
from .models import Lot

class LotResource(resources.ModelResource):
    lot_individuel = fields.Field(attribute='code', column_name='code')

    class Meta:
        model = Lot
        fields = ('code', 'immeuble')
        import_id_fields = ['code']
        skip_unchanged = True
        report_skipped = True
