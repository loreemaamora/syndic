from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum
import decimal

class Compte(models.Model):
    compte = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=100)
    type_compte = models.CharField(max_length=50, choices=[
        ('actif', 'Actif'),
        ('passif', 'Passif'),
        ('recette', 'Recette'),
        ('depense', 'Dépense'),
        ('ajustement', 'Ajustement')
    ])

    class Meta:
        ordering = ['compte']

    def __str__(self):
        return f"{self.compte} - {self.libelle.upper()}"

    def save(self, *args, **kwargs):
        self.libelle = self.libelle.upper()
        super().save(*args, **kwargs)

    def get_solde_exercice(self, exercice):
        from .solde_exercice_compte import SoldeExerciceCompte
        return SoldeExerciceCompte.objects.get_or_create(compte=self, exercice=exercice)

    def get_solde_actuel(self, exercice):
        solde_exercice, _ = self.get_solde_exercice(exercice)
        return solde_exercice.solde_actuel

    def get_solde_initial(self, exercice):
        solde_exercice, _ = self.get_solde_exercice(exercice)
        return solde_exercice.solde_initial

    def mettre_a_jour_solde(self, exercice):
        solde_exercice, _ = self.get_solde_exercice(exercice)
        total_debit = self.ecritures.filter(
            type_ecriture='DB', 
            transaction__exercice=exercice
        ).aggregate(Sum('montant'))['montant__sum'] or decimal.Decimal(0.0)
        
        total_credit = self.ecritures.filter(
            type_ecriture='CR', 
            transaction__exercice=exercice
        ).aggregate(Sum('montant'))['montant__sum'] or decimal.Decimal(0.0)
        
        solde_exercice.solde_actuel = (
            decimal.Decimal(solde_exercice.solde_initial) + 
            decimal.Decimal(total_debit) - 
            decimal.Decimal(total_credit)
        )
        solde_exercice.save()