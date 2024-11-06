from datetime import timedelta
from django.utils import timezone
from django.db import models, transaction
from django.core.exceptions import ValidationError
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
        exercice = ExerciceComptable.get_exercice_actuel()  # Get current exercise
        solde_initial = self.get_solde_initial(exercice)
        solde_actuel = self.get_solde_actuel(exercice)  # Calculate current balance
        return f"{self.compte} - {self.libelle} - {solde_initial} - {solde_actuel}"

    def save(self, *args, **kwargs):
        self.libelle = self.libelle.upper()
        super().save(*args, **kwargs)

    def get_solde_initial(self, exercice):
        try:
            solde_exercice = SoldeExerciceCompte.objects.get(compte=self, exercice=exercice)
            return solde_exercice.solde_initial
        except SoldeExerciceCompte.DoesNotExist:
            # Handle case where no SoldeExerciceCompte exists for this Compte and Exercice
            return decimal.Decimal(0.0)  # Default to zero balance

    def get_solde_actuel(self, exercice):
        try:
            solde_exercice = SoldeExerciceCompte.objects.get(compte=self, exercice=exercice)
            return solde_exercice.solde_actuel
        except SoldeExerciceCompte.DoesNotExist:
            # Handle case where no SoldeExerciceCompte exists for this Compte and Exercice
            return decimal.Decimal(0.0)  # Default to zero balance

    def mettre_a_jour_solde(self, exercice):
        try:
            solde_exercice = SoldeExerciceCompte.objects.get(compte=self, exercice=exercice)
        except SoldeExerciceCompte.DoesNotExist:
            # Create a new SoldeExerciceCompte if it doesn't exist
            solde_exercice = SoldeExerciceCompte.objects.create(
                compte=self,
                exercice=exercice,
                solde_initial=decimal.Decimal(0.0),  # Use initial balance from Compte
                solde_actuel=decimal.Decimal(0.0),
            )

        # Ensure `e.montant` is a decimal.Decimal
        total_debit = sum(decimal.Decimal(e.montant) for e in self.ecritures.filter(type_ecriture='DB', transaction__exercice=exercice))
        total_credit = sum(decimal.Decimal(e.montant) for e in self.ecritures.filter(type_ecriture='CR', transaction__exercice=exercice))

        solde_exercice.solde_actuel = decimal.Decimal(solde_exercice.solde_initial) + total_debit - total_credit
        solde_exercice.save()

    def get_solde_initial_for_exercice(self, exercice):
        try:
            previous_exercices = ExerciceComptable.objects.filter(date_fin__lt=exercice.date_debut).order_by('-date_fin')
            solde_exercice = SoldeExerciceCompte.objects.get(compte=self, exercice=previous_exercices.first())
            return solde_exercice.solde_actuel
        except (ExerciceComptable.DoesNotExist, SoldeExerciceCompte.DoesNotExist):
            return decimal.Decimal(0.0)

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

            # Vérifier si l'exercice suivant existe déjà
            new_exercice, created = ExerciceComptable.objects.get_or_create(
                date_debut=self.date_fin + timedelta(days=1),
                date_fin=self.date_fin + timedelta(days=365),
                defaults={'est_ouvert': True}
            )
            self.report_soldes_comptes(new_exercice)

        return new_exercice

    def report_soldes_comptes(self, exercice_suivant):
        for compte in Compte.objects.filter(type_compte__in=['actif', 'passif']):
            # Récupérer toutes les écritures du compte pour l'exercice en cours
            ecritures = EcritureComptable.objects.filter(compte=compte, transaction__exercice=self)

            # Calculer le solde final de l'exercice en cours en tenant compte de toutes les écritures
            solde_final = compte.get_solde_actuel(self)

            # Créer ou mettre à jour le solde pour le nouvel exercice
            solde_exercice, created = SoldeExerciceCompte.objects.get_or_create(
                compte=compte,
                exercice=exercice_suivant,
                defaults={'solde_initial': solde_final, 'solde_actuel': solde_final}
            )

            # Si des écritures ont déjà été enregistrées dans le nouvel exercice, mettre à jour le solde actuel
            if not created:
                # Récupérer les écritures du compte pour le nouvel exercice
                ecritures_suivant = EcritureComptable.objects.filter(compte=compte, transaction__exercice=exercice_suivant)

                # Calculer le solde actuel en ajoutant les écritures du nouvel exercice
                solde_actuel = solde_final + sum(e.montant for e in ecritures_suivant if e.type_ecriture == 'DB') - sum(e.montant for e in ecritures_suivant if e.type_ecriture == 'CR')

                solde_exercice.solde_actuel = solde_actuel
                solde_exercice.save()

class SoldeExerciceCompte(models.Model):
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE, related_name='soldes_exercice')
    exercice = models.ForeignKey(ExerciceComptable, on_delete=models.CASCADE, related_name='soldes_compte')
    solde_initial = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    solde_actuel = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ('compte', 'exercice')

    def __str__(self):
        return f"Solde {self.compte} pour {self.exercice}"

class EcritureComptable(models.Model):
    date = models.DateField()
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE, related_name='ecritures')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type_ecriture = models.CharField(max_length=2, choices=[('DB', 'Débit'), ('CR', 'Crédit')])
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='ecritures')

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.compte.compte} - {self.type_ecriture} - {self.montant}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.compte.mettre_a_jour_solde(self.transaction.exercice)

class Transaction(models.Model):
    date_creation = models.DateField(auto_now_add=True)
    date_operation = models.DateField()
    libelle = models.CharField(max_length=255)
    exercice = models.ForeignKey(ExerciceComptable, on_delete=models.CASCADE, related_name='transactions', limit_choices_to={'est_ouvert': True})

    class Meta:
        ordering = ['-date_operation']

    def __str__(self):
        return f"{self.date_operation} - {self.libelle} - {self.exercice}"

    def save(self, *args, **kwargs):
        self.libelle = self.libelle.upper()
        super().save(*args, **kwargs)

    def clean(self):
        if self.pk:
            total_debit = sum(e.montant for e in self.ecritures.filter(type_ecriture='DB'))
            total_credit = sum(e.montant for e in self.ecritures.filter(type_ecriture='CR'))
            if total_debit != total_credit:
                raise ValidationError("Les écritures comptables doivent être équilibrées (Total débit = Total crédit).")