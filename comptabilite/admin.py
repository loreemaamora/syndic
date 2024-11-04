from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Compte, ExerciceComptable, SoldeExerciceCompte, EcritureComptable, Transaction

# Enregistrement des modèles
admin.site.register(Compte)
admin.site.register(ExerciceComptable)
admin.site.register(SoldeExerciceCompte)
admin.site.register(EcritureComptable)

# Inline pour les écritures comptables
class EcritureComptableInline(admin.TabularInline):
    model = EcritureComptable
    extra = 1  # Nombre de formulaires vierges à afficher

# Configuration de l'admin pour Transaction
class TransactionAdmin(admin.ModelAdmin):
    inlines = [EcritureComptableInline]

    def save_model(self, request, obj, form, change):
        # Appeler la validation avant de sauvegarder l'objet principal
        obj.clean()  # Pour vérifier l’équilibre si des changements sont apportés
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        # Enregistrer les écritures dans une transaction atomique
        with transaction.atomic():
            super().save_related(request, form, formsets, change)

            # Valider l'équilibre des écritures associées
            total_debit = sum(e.montant for e in form.instance.ecritures.all() if e.type_ecriture == 'DB')
            total_credit = sum(e.montant for e in form.instance.ecritures.all() if e.type_ecriture == 'CR')

            if total_debit != total_credit:
                raise ValidationError("Les écritures comptables doivent être équilibrées (Total débit = Total crédit).")

# Enregistrement de TransactionAdmin pour Transaction
admin.site.register(Transaction, TransactionAdmin)
