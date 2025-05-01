# Importations standard de Python
import os
import decimal
from datetime import timedelta, date


# Importations Django
from django.utils import timezone
from django.db import models, transaction
from django.db.models import Sum, F
from django.db.models.signals import post_save, post_delete
from django.core.exceptions import ValidationError
from django.dispatch import receiver

from accounts.models import Lot


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
        # exercice = ExerciceComptable.get_exercice_actuel()
        return f"{self.compte} - {self.libelle.upper()}"

    def save(self, *args, **kwargs):
        self.libelle = self.libelle.upper()
        super().save(*args, **kwargs)

    def get_solde_exercice(self, exercice):
        return SoldeExerciceCompte.objects.get_or_create(compte=self, exercice=exercice)

    def get_solde_actuel(self, exercice):
        solde_exercice, _ = self.get_solde_exercice(exercice)
        return solde_exercice.solde_actuel

    def get_solde_initial(self, exercice):
        solde_exercice, _ = self.get_solde_exercice(exercice)
        return solde_exercice.solde_initial

    def mettre_a_jour_solde(self, exercice):
        solde_exercice, _ = self.get_solde_exercice(exercice)
        total_debit = self.ecritures.filter(type_ecriture='DB', transaction__exercice=exercice).aggregate(Sum('montant'))['montant__sum'] or decimal.Decimal(0.0)
        total_credit = self.ecritures.filter(type_ecriture='CR', transaction__exercice=exercice).aggregate(Sum('montant'))['montant__sum'] or decimal.Decimal(0.0)
        solde_exercice.solde_actuel = decimal.Decimal(solde_exercice.solde_initial) + decimal.Decimal(total_debit) - decimal.Decimal(total_credit)
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
        return ExerciceComptable.objects.filter(est_actuel=True).first()

    def close_exercice(self):
        if not self.est_ouvert:
            raise ValidationError(f"L'exercice {self} est déjà clôturé.")

        with transaction.atomic():            
            compte_resultat_classe8 = Compte.objects.get(compte="'890")
            self.clore_comptes_produits_charges(compte_resultat_classe8)
            compte_resultat_classe1 = Compte.objects.get(compte="'119")
            self.reporter_resultat_net(self.calculer_resultat_net(), compte_resultat_classe8, compte_resultat_classe1)
            new_exercice, created = ExerciceComptable.objects.get_or_create(
                date_debut=self.date_fin + timedelta(days=1),
                date_fin=self.date_fin + timedelta(days=365),
                defaults={'est_ouvert': True}
            )
            self.report_soldes_comptes(new_exercice)
            self.est_ouvert = False
            self.save()
        return new_exercice

    def report_soldes_comptes(self, exercice_suivant):
        comptes = Compte.objects.filter(type_compte__in=['actif', 'passif'])
        for compte in comptes:
            solde_final = compte.get_solde_actuel(self)
            SoldeExerciceCompte.objects.update_or_create(
                compte=compte, exercice=exercice_suivant,
                defaults={'solde_initial': solde_final, 'solde_actuel': solde_final}
            )
    
    @transaction.atomic
    def clore_comptes_produits_charges(self, compte_resultat):
        # Calcul du résultat net
        resultat_net = self.calculer_resultat_net()

        # Créer une transaction pour la clôture
        transaction_cloture = Transaction.objects.create(
            exercice=self,
            date_operation=self.date_fin,
            libelle="Clôture des comptes de produits et charges"
        )

        # Clôturer les comptes de produits
        comptes_produits = Compte.objects.filter(type_compte='recette')
        for compte in comptes_produits:
            solde = compte.get_solde_actuel(self)
            
            # Ignorer les comptes avec un solde nul
            if solde == 0:
                continue
            
            # Créer l'écriture pour le compte de produit
            EcritureComptable.objects.create(
                compte=compte,
                montant=abs(solde),
                type_ecriture='CR' if solde > 0 else 'DB',
                transaction=transaction_cloture
            )

            # Créer l'écriture pour le compte de résultat
            EcritureComptable.objects.create(
                compte=compte_resultat,
                montant=abs(solde),
                type_ecriture='DB' if solde > 0 else 'CR',
                transaction=transaction_cloture
            )


        # Clôturer les comptes de charges
        comptes_charges = Compte.objects.filter(type_compte='depense')
        for compte in comptes_charges:
            solde = compte.get_solde_actuel(self)
            if solde == 0:
                continue
            EcritureComptable.objects.create(
                compte=compte,
                montant=abs(solde),
                type_ecriture = 'CR' if solde > 0 else 'DB',
                transaction=transaction_cloture
            )
            EcritureComptable.objects.create(
                compte=compte_resultat,
                montant=abs(solde),
                type_ecriture = 'CR' if solde < 0 else 'DB',
                transaction=transaction_cloture
            )

    def calculer_resultat_net(self):
        total_produits = EcritureComptable.objects.filter(
            compte__type_compte='recette', transaction__exercice=self, type_ecriture='CR'
        ).aggregate(total=Sum(F('montant')))['total'] or decimal.Decimal(0.0)

        total_charges = EcritureComptable.objects.filter(
            compte__type_compte='depense', transaction__exercice=self, type_ecriture='DB'
        ).aggregate(total=Sum(F('montant')))['total'] or decimal.Decimal(0.0)

        return total_produits - total_charges


    def reporter_resultat_net(self, resultat_net, compte_resultat_classe8, compte_resultat_classe1):

        # Créer une transaction pour le report du résultat
        transaction_report = Transaction.objects.create(
            exercice=self,
            date_operation=self.date_fin,
            libelle="Report du résultat net"
        )

        EcritureComptable.objects.create(
            compte=compte_resultat_classe8,
            montant=abs(resultat_net),
            type_ecriture='CR' if resultat_net < 0 else 'DB',
            transaction=transaction_report
        )
        EcritureComptable.objects.create(
            compte=compte_resultat_classe1,
            montant=abs(resultat_net),
            type_ecriture='CR' if resultat_net > 0 else 'DB',
            transaction=transaction_report
        )


class Transaction(models.Model):
    date_creation = models.DateField(auto_now_add=True)
    date_operation = models.DateField()
    libelle = models.CharField(max_length=255)
    justif = models.FileField(upload_to='transactions/', null=True, blank=True)
    exercice = models.ForeignKey(ExerciceComptable, on_delete=models.CASCADE, related_name='transactions_exercice', limit_choices_to={'est_ouvert': True})

    class Meta:
        ordering = ['-date_operation']

    def __str__(self):
        return f"{self.date_operation} - {self.libelle.upper()} - {self.exercice}"

    def save(self, *args, **kwargs):
        self.libelle = self.libelle.upper()
        self.clean_justif()
        if self.justif:
            self.justif.name = self.generate_filename()
        super().save(*args, **kwargs)
        
    def generate_filename(self):
        return f"{self.date_operation.strftime('%Y%m%d')}_{self.libelle.replace(' ', '_')}_{self.justif.name.split('/')[-1]}"

    def delete(self, *args, **kwargs):
        if self.justif:
            self.justif.delete(False)
        super().delete(*args, **kwargs)

    def clean(self):
        if self.pk:
            balance = self.ecritures.values('type_ecriture').annotate(total=Sum('montant'))
            total_debit = next((b['total'] for b in balance if b['type_ecriture'] == 'DB'), decimal.Decimal(0.0))
            total_credit = next((b['total'] for b in balance if b['type_ecriture'] == 'CR'), decimal.Decimal(0.0))
            if total_debit != total_credit:
                raise ValidationError("Les écritures comptables doivent être équilibrées (Total débit = Total crédit).")

    def clean_justif(self):
        """
        Méthode de validation du fichier justificatif.
        """
        # Vérifier si le justificatif est fourni
        if self.justif:
            # Obtenir l'extension du fichier
            ext = os.path.splitext(self.justif.name)[1].lower()
            # Définir les extensions autorisées
            extensions_autorisees = ['.pdf', '.jpg', '.jpeg', '.png']
            # Vérifier l'extension
            if ext not in extensions_autorisees:
                raise ValidationError(
                    "Le justificatif doit être un fichier PDF ou une image (PDF, JPG, JPEG, PNG)."
                )
            # Limiter la taille à 1 MB
            taille_max = 1 * 1024 * 1024  # 1 MB
            if self.justif.size > taille_max:
                raise ValidationError("La taille du justificatif ne doit pas dépasser 1 MB.")

            # Vérifier la date du fichier justificatif
            if self.date_operation > date.today():
                raise ValidationError(
                    "La date de l'opération ne peut pas être postérieure à la date d'aujourd'hui."
                )

class EcritureComptable(models.Model):
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE, related_name='ecritures')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type_ecriture = models.CharField(max_length=2, choices=[('DB', 'Débit'), ('CR', 'Crédit')])
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='ecritures')

    class Meta:
        ordering = ['-transaction__id']

    def __str__(self):
        return f"{self.compte.compte} - {self.type_ecriture} - {self.montant}"

class SoldeExerciceCompte(models.Model):
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE, related_name='soldes_exercice')
    exercice = models.ForeignKey(ExerciceComptable, on_delete=models.CASCADE, related_name='soldes_compte')
    solde_initial = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    solde_actuel = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ('compte', 'exercice')

    def __str__(self):
        return f"Solde {self.compte} pour {self.exercice}"

    def save(self, *args, **kwargs):
        if not self.exercice.est_ouvert:
            raise ValidationError("Impossible de modifier le solde pour un exercice clôturé.")
        super().save(*args, **kwargs)

class Abonnement(models.Model):
    FREQUENCE_CHOICES = [
        ('mensuel', 'Mensuel'),
        ('trimestriel', 'Trimestriel'),
        ('annuel', 'Annuel'),
    ]

    lot = models.ForeignKey(
        'accounts.Lot',  # Spécifiez l'app cible
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False  # Permet de garder la référence même si le lot est supprimé
    )
    montant = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant récurrent")
    frequence = models.CharField(
        max_length=20,
        choices=FREQUENCE_CHOICES,
        default='mensuel',
        verbose_name="Fréquence de facturation"
    )
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(null=True, blank=True, verbose_name="Date de fin (si résiliable)")
    actif = models.BooleanField(default=True, verbose_name="Abonnement actif ?")
    description = models.TextField(blank=True, verbose_name="Détails (ex: charges, services inclus)")

    def __str__(self):
        return f"Abonnement {self.frequence} - {self.lot} ({self.montant}€)"

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"

# Signaux

@receiver(post_save, sender=EcritureComptable)
@receiver(post_delete, sender=EcritureComptable)
def update_solde(sender, instance, **kwargs):
    instance.compte.mettre_a_jour_solde(instance.transaction.exercice)
