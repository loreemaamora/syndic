from datetime import timedelta
from django.utils import timezone
from django.db import models, transaction
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
        ('depense', 'Dépense')
    ])

    class Meta:
        ordering = ['compte']

    def __str__(self):
        exercice = ExerciceComptable.get_exercice_actuel()
        return f"{self.compte} - {self.libelle.upper()} - {self.get_solde_initial(exercice)} - {self.get_solde_actuel(exercice)}"

    def save(self, *args, **kwargs):
        self.libelle = self.libelle.upper()
        super().save(*args, **kwargs)

    def get_solde_initial(self, exercice):
        solde_exercice = SoldeExerciceCompte.objects.filter(compte=self, exercice=exercice).first()
        return solde_exercice.solde_initial if solde_exercice else decimal.Decimal(0.0)

    def get_solde_actuel(self, exercice):
        solde_exercice = SoldeExerciceCompte.objects.filter(compte=self, exercice=exercice).first()
        return solde_exercice.solde_actuel if solde_exercice else decimal.Decimal(0.0)

    def mettre_a_jour_solde(self, exercice):
        solde_exercice, created = SoldeExerciceCompte.objects.get_or_create(
            compte=self, exercice=exercice,
            defaults={'solde_initial': decimal.Decimal(0.0), 'solde_actuel': decimal.Decimal(0.0)}
        )
        total_debit = self.ecritures.filter(type_ecriture='DB', transaction__exercice=exercice).aggregate(Sum('montant'))['montant__sum'] or decimal.Decimal(0.0)
        total_credit = self.ecritures.filter(type_ecriture='CR', transaction__exercice=exercice).aggregate(Sum('montant'))['montant__sum'] or decimal.Decimal(0.0)
        solde_exercice.solde_actuel = solde_exercice.solde_initial + total_debit - total_credit
        solde_exercice.save()

class ExerciceComptable(models.Model):
    date_debut = models.DateField()
    date_fin = models.DateField()
    est_ouvert = models.BooleanField(default=True)
    est_actuel = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['est_actuel'], condition=models.Q(est_actuel=True), name='unique_exercice_actuel')
        ]

    def __str__(self):
        return f"Exercice {self.date_debut} - {self.date_fin}"

    @staticmethod
    def get_exercice_actuel():
        try:
            return ExerciceComptable.objects.get(est_actuel=True)
        except ExerciceComptable.DoesNotExist:
            raise ValidationError("Aucun exercice actuel trouvé.")

    def close_exercice(self):
        if not self.est_ouvert:
            raise ValidationError(f"L'exercice {self} est déjà clôturé.")

        with transaction.atomic():
            self.est_ouvert = False
            self.save()
            new_exercice, created = ExerciceComptable.objects.get_or_create(
                date_debut=self.date_fin + timedelta(days=1),
                date_fin=self.date_fin + timedelta(days=365),
                defaults={'est_ouvert': True}
            )
            self.report_soldes_comptes(new_exercice)
        return new_exercice

    def report_soldes_comptes(self, exercice_suivant):
        comptes = Compte.objects.filter(type_compte__in=['actif', 'passif']).select_related('soldes_exercice')
        for compte in comptes:
            solde_final = compte.get_solde_actuel(self)
            SoldeExerciceCompte.objects.update_or_create(
                compte=compte, exercice=exercice_suivant,
                defaults={'solde_initial': solde_final, 'solde_actuel': solde_final}
            )

class Transaction(models.Model):
    date_creation = models.DateField(auto_now_add=True)
    date_operation = models.DateField()
    libelle = models.CharField(max_length=255)
    justif = models.FileField(upload_to='uploads/', null=True, blank=True)
    exercice = models.ForeignKey(ExerciceComptable, on_delete=models.CASCADE, related_name='transactions', limit_choices_to={'est_ouvert': True})

    class Meta:
        ordering = ['-date_operation']

    def __str__(self):
        return f"{self.date_operation} - {self.libelle.upper()} - {self.exercice}"

    def save(self, *args, **kwargs):
        self.libelle = self.libelle.upper()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.justif:
            self.justif.delete(False)
        super().delete(*args, **kwargs)

    def clean(self):
        if self.pk:
            total_debit = self.ecritures.filter(type_ecriture='DB').aggregate(Sum('montant'))['montant__sum'] or decimal.Decimal(0.0)
            total_credit = self.ecritures.filter(type_ecriture='CR').aggregate(Sum('montant'))['montant__sum'] or decimal.Decimal(0.0)
            if total_debit != total_credit:
                raise ValidationError("Les écritures comptables doivent être équilibrées (Total débit = Total crédit).")

class EcritureComptable(models.Model):
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE, related_name='ecritures')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type_ecriture = models.CharField(max_length=2, choices=[('DB', 'Débit'), ('CR', 'Crédit')])
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='ecritures')

    class Meta:
        ordering = ['-transaction__id']

    def __str__(self):
        return f"{self.compte.compte} - {self.type_ecriture} - {self.montant}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.compte.mettre_a_jour_solde(self.transaction.exercice)

class SoldeExerciceCompte(models.Model):
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE, related_name='soldes_exercice')
    exercice = models.ForeignKey(ExerciceComptable, on_delete=models.CASCADE, related_name='soldes_compte')
    solde_initial = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    solde_actuel = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ('compte', 'exercice')

    def __str__(self):
        return f"Solde {self.compte} pour {self.exercice}"