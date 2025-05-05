from django.db import models
from django.core.exceptions import ValidationError
from patrimoine.models import Lot
from .compte import Compte
from .transaction import Transaction
from .fournisseur import Fournisseur

class EcritureComptable(models.Model):
    compte = models.ForeignKey(
        Compte,
        on_delete=models.CASCADE,
        related_name='ecritures',
        verbose_name="Compte comptable"
    )
    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant"
    )
    type_ecriture = models.CharField(
        max_length=2,
        choices=[('DB', 'Débit'), ('CR', 'Crédit')],
        verbose_name="Type d'écriture"
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='ecritures',
        verbose_name="Transaction liée"
    )
    
    # Références aux tiers
    lot = models.ForeignKey(
        Lot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecritures',
        verbose_name="Lot associé"
    )
    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecritures',
        verbose_name="Fournisseur associé"
    )

    class Meta:
        verbose_name = "Écriture comptable"
        verbose_name_plural = "Écritures comptables"
        ordering = ['-transaction__id']
        
    def __str__(self):
        return f"{self.compte} - {self.get_type_ecriture_display()} - {self.montant}"

    def clean(self):
        """Validation des règles métiers"""
        # Un seul tiers autorisé (lot OU fournisseur)
        if self.lot and self.fournisseur:
            raise ValidationError("Une écriture ne peut référencer qu'un seul type de tiers (lot ou fournisseur)")