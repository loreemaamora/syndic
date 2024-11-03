import os
from datetime import timedelta
from django.utils import timezone
from django.utils.text import slugify
from django.db import models, transaction
from django.core.exceptions import ValidationError

class Compte(models.Model):
    compte = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=100)
    type_compte = models.CharField(max_length=50, choices=[
        ('actif', 'Actif'),
        ('passif', 'Passif'),
        ('recette', 'Recette'),
        ('depense', 'Dépense')
    ])
    solde_initial = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    solde_actuel = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['compte']

    def mettre_a_jour_solde(self):
        total_debit = sum(e.montant for e in self.ecritures.filter(type_ecriture='DB'))
        total_credit = sum(e.montant for e in self.ecritures.filter(type_ecriture='CR'))
        self.solde_actuel = self.solde_initial + total_debit - total_credit
        self.save()

    def __str__(self):
        return f"{self.compte} - {self.libelle}"

    def save(self, *args, **kwargs):
        self.libelle = self.libelle.upper()
        super().save(*args, **kwargs)

class ExerciceComptable(models.Model):
    date_debut = models.DateField()
    date_fin = models.DateField()
    est_ouvert = models.BooleanField(default=True)
    est_actuel = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['est_actuel'], condition=models.Q(est_actuel=True), name='unique_exercice_actuel')
        ]

    @staticmethod
    def get_exercice_actuel():
        try:
            return ExerciceComptable.objects.get(est_actuel=True)
        except ExerciceComptable.DoesNotExist:
            raise ValidationError("Aucun exercice actuel trouvé.")

    def __str__(self):
        return f"Exercice {self.date_debut} - {self.date_fin}"

    def ouvrir_exercice(self):
        self.est_ouvert = True
        self.save()

    def cloturer_exercice(self):
        if not all(transaction.is_balanced() for transaction in self.transactions.all()):
            raise ValidationError("Toutes les transactions de cet exercice doivent être équilibrées avant la clôture.")
        self.est_ouvert = False
        self.save()

    def clean(self):
        if self.est_actuel and ExerciceComptable.objects.filter(est_actuel=True).exclude(id=self.id).exists():
            raise ValidationError("Il ne peut y avoir qu'un seul exercice actuel.")
        if self.date_fin <= self.date_debut:
            raise ValidationError("La date de fin doit être postérieure à la date de début.")

    @transaction.atomic
    def passer_a_exercice_suivant(self):
        self.est_actuel = False
        self.cloturer_exercice()

        transaction_cloture = Transaction.objects.create(
            date=timezone.now(),
            libelle="Clôture de l'exercice",
            exercice=self
        )

        total_recettes = sum(compte.solde_actuel for compte in Compte.objects.filter(type_compte='recette'))
        total_depenses = sum(compte.solde_actuel for compte in Compte.objects.filter(type_compte='depense'))
        resultat = total_recettes - total_depenses

        compte_resultat = Compte.objects.get(compte="119")

        if resultat != 0:
            EcritureComptable.objects.create(
                date=self.date_fin,
                compte=compte_resultat,
                libelle="Résultat de l'exercice",
                montant=abs(resultat),
                type_ecriture='CR' if resultat > 0 else 'DB',
                exercice=self,
                transaction=transaction_cloture
            )

        nouvel_exercice = ExerciceComptable.objects.create(
            date_debut=self.date_fin + timedelta(days=1),
            date_fin=self.date_fin.replace(year=self.date_fin.year + 1),
            est_ouvert=True,
            est_actuel=True
        )

        transaction_ouverture = Transaction.objects.create(
            date=timezone.now(),
            libelle="Ouverture de l'exercice",
            exercice=nouvel_exercice
        )

        for compte in Compte.objects.filter(type_compte__in=['actif', 'passif']):
            if compte.solde_actuel != 0:
                EcritureComptable.objects.create(
                    date=self.date_fin,
                    compte=compte,
                    libelle="Report solde bilan",
                    montant=compte.solde_actuel,
                    type_ecriture='DB' if compte.solde_actuel > 0 else 'CR',
                    exercice=nouvel_exercice,
                    transaction=transaction_ouverture
                )

        for compte in Compte.objects.filter(type_compte__in=['recette', 'depense']):
            compte.solde_initial = 0
            compte.solde_actuel = 0
            compte.save()

        self.save()

class EcritureComptable(models.Model):
    date = models.DateField()
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE, related_name='ecritures')
    # libelle = models.CharField(max_length=255)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type_ecriture = models.CharField(max_length=2, choices=[('DB', 'Débit'), ('CR', 'Crédit')])
    # exercice = models.ForeignKey(ExerciceComptable, on_delete=models.CASCADE, related_name='ecritures')
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='ecritures')

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.compte.libelle} ({self.type_ecriture}) : {self.montant} DH"

    def save(self, *args, **kwargs):
        if self.transaction and not self.date:
            self.date = self.transaction.date_operation  # Copier la date de Transaction
        super().save(*args, **kwargs)
        self.compte.mettre_a_jour_solde()

    def delete(self, *args, **kwargs):
        compte = self.compte
        super().delete(*args, **kwargs)
        compte.mettre_a_jour_solde()

class Transaction(models.Model):
    date_creation = models.DateField(auto_now_add=True)
    date_operation = models.DateField()
    libelle = models.CharField(max_length=255)
    support = models.FileField(upload_to='uploads/', null=True)
    exercice = models.ForeignKey(ExerciceComptable, on_delete=models.CASCADE, related_name='transactions')

    class Meta:
        ordering = ['-date_operation']

    def __str__(self):
        return f"{self.date_operation} - {self.libelle} - {self.exercice}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Check if it's a new object
            self.exercice = ExerciceComptable.get_exercice_actuel()
        super().save(*args, **kwargs)

    def clean(self):
        if self.pk:
            total_debit = sum(e.montant for e in self.ecritures.filter(type_ecriture='DB'))
            total_credit = sum(e.montant for e in self.ecritures.filter(type_ecriture='CR'))
            if total_debit != total_credit:
                raise ValidationError("Les écritures comptables doivent être équilibrées (Total débit = Total crédit).")
