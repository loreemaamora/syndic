from django.db import models
from django.core.exceptions import ValidationError

class SoldeExerciceCompte(models.Model):
    compte = models.ForeignKey(
        'Compte', 
        on_delete=models.CASCADE, 
        related_name='soldes_exercice'
    )
    exercice = models.ForeignKey(
        'ExerciceComptable', 
        on_delete=models.CASCADE, 
        related_name='soldes_compte'
    )
    solde_initial = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.0
    )
    solde_actuel = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.0
    )

    class Meta:
        unique_together = ('compte', 'exercice')

    def __str__(self):
        return f"Solde {self.compte} pour {self.exercice}"

    def save(self, *args, **kwargs):
        if not self.exercice.est_ouvert:
            raise ValidationError("Impossible de modifier le solde pour un exercice clôturé.")
        super().save(*args, **kwargs)