from django.db import models

class EcritureComptable(models.Model):
    compte = models.ForeignKey(
        'Compte', 
        on_delete=models.CASCADE, 
        related_name='ecritures'
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type_ecriture = models.CharField(
        max_length=2, 
        choices=[('DB', 'Débit'), ('CR', 'Crédit')]
    )
    transaction = models.ForeignKey(
        'Transaction', 
        on_delete=models.CASCADE, 
        related_name='ecritures'
    )

    class Meta:
        ordering = ['-transaction__id']

    def __str__(self):
        return f"{self.compte.compte} - {self.type_ecriture} - {self.montant}"