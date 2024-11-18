# comptabilite/resources.py
from import_export import resources, fields
from .models import Compte

class CompteResource(resources.ModelResource):
    compte = fields.Field(attribute='compte', column_name='compte')

    class Meta:
        model = Compte
        fields = ('compte', 'libelle', 'type_compte')
        import_id_fields = ['compte']  # Utiliser 'compte' comme identifiant
        skip_unchanged = True
        report_skipped = True
