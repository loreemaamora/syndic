from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Compte, ExerciceComptable, SoldeExerciceCompte, EcritureComptable, Transaction

# Enregistrement des modèles
admin.site.register(SoldeExerciceCompte)
admin.site.register(EcritureComptable)

class CompteAdmin(admin.ModelAdmin):
    list_display = ('compte', 'libelle', 'solde_initial_display', 'solde_actuel_display')

    def solde_initial_display(self, obj):
        exercice = ExerciceComptable.get_exercice_actuel()
        return obj.get_solde_initial(exercice)
    solde_initial_display.short_description = 'Solde Initial'

    def solde_actuel_display(self, obj):
        exercice = ExerciceComptable.get_exercice_actuel()
        return obj.get_solde_actuel(exercice)
    solde_actuel_display.short_description = 'Solde Actuel'

admin.site.register(Compte, CompteAdmin)

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

# Configuration de l'admin pour ExerciceComptable
class ExerciceComptableAdmin(admin.ModelAdmin):
    list_display = ('date_debut', 'date_fin', 'est_ouvert', 'est_actuel')
    actions = ['close_exercice']

    def close_exercice(self, request, queryset):
        for exercice in queryset.all():
            exercice.close_exercice()
        self.message_user(request, "Les exercices sélectionnés ont été clôturés.")
    close_exercice.short_description = "Clôturer les exercices sélectionnés"

# Enregistrement de ExerciceComptableAdmin pour ExerciceComptable
admin.site.register(ExerciceComptable, ExerciceComptableAdmin)
