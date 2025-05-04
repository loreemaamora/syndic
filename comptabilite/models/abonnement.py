from django.db import models

class Abonnement(models.Model):
    FREQUENCE_CHOICES = [
        ('mensuel', 'Mensuel'),
        ('trimestriel', 'Trimestriel'),
        ('annuel', 'Annuel'),
    ]

    lot = models.ForeignKey(
        'patrimoine.Lot',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False
    )
    montant = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Montant récurrent"
    )
    frequence = models.CharField(
        max_length=20,
        choices=FREQUENCE_CHOICES,
        default='mensuel',
        verbose_name="Fréquence de facturation"
    )
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Date de fin (si résiliable)"
    )
    actif = models.BooleanField(
        default=True, 
        verbose_name="Abonnement actif ?"
    )
    description = models.TextField(
        blank=True, 
        verbose_name="Détails (ex: charges, services inclus)"
    )

    def __str__(self):
        return f"Abonnement {self.frequence} - {self.lot} ({self.montant}€)"

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"