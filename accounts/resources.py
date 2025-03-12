# accounts/resources.py
from import_export import resources, fields
from .models import LotIndividuel

class LotIndividuelResource(resources.ModelResource):
    lot_individuel = fields.Field(attribute='lot_individuel', column_name='lot_individuel')

    class Meta:
        model = LotIndividuel
        fields = ('lot_individuel', 'immeuble', 'proprietaire')
        import_id_fields = ['lot_individuel']  # Utiliser 'compte' comme identifiant
        skip_unchanged = True
        report_skipped = True
