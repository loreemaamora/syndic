from django.db import models, transaction
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
import decimal
from datetime import timedelta

class ExerciceComptable(models.Model):
    date_debut = models.DateField()
    date_fin = models.DateField()
    est_ouvert = models.BooleanField(default=True)
    est_actuel = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['est_actuel'], 
                condition=models.Q(est_actuel=True), 
                name='unique_exercice_actuel'
            )
        ]

    def __str__(self):
        return f"Exercice {self.date_debut} - {self.date_fin}"

    @staticmethod
    def get_exercice_actuel():
        return ExerciceComptable.objects.filter(est_actuel=True).first()

    def close_exercice(self):
        from .compte import Compte
        from .transaction import Transaction
        from .ecriture_comptable import EcritureComptable
        
        if not self.est_ouvert:
            raise ValidationError(f"L'exercice {self} est déjà clôturé.")

        with transaction.atomic():            
            compte_resultat_classe8 = Compte.objects.get(compte="890")
            self.clore_comptes_produits_charges(compte_resultat_classe8)
            compte_resultat_classe1 = Compte.objects.get(compte="119")
            self.reporter_resultat_net(
                self.calculer_resultat_net(), 
                compte_resultat_classe8, 
                compte_resultat_classe1
            )
            
            new_exercice = ExerciceComptable.objects.create(
                date_debut=self.date_fin + timedelta(days=1),
                date_fin=self.date_fin + timedelta(days=365),
                est_ouvert=True
            )
            
            self.report_soldes_comptes(new_exercice)
            self.est_ouvert = False
            self.save()
            
        return new_exercice

    def report_soldes_comptes(self, exercice_suivant):
        from .compte import Compte
        from .solde_exercice_compte import SoldeExerciceCompte
        
        comptes = Compte.objects.filter(type_compte__in=['actif', 'passif'])
        for compte in comptes:
            solde_final = compte.get_solde_actuel(self)
            SoldeExerciceCompte.objects.update_or_create(
                compte=compte, 
                exercice=exercice_suivant,
                defaults={
                    'solde_initial': solde_final, 
                    'solde_actuel': solde_final
                }
            )
    
    @transaction.atomic
    def clore_comptes_produits_charges(self, compte_resultat):
        resultat_net = self.calculer_resultat_net()
        from .transaction import Transaction
        from .ecriture_comptable import EcritureComptable
        from .compte import Compte

        transaction_cloture = Transaction.objects.create(
            exercice=self,
            date_operation=self.date_fin,
            libelle="Clôture des comptes de produits et charges"
        )

        # Clôturer les comptes de produits
        comptes_produits = Compte.objects.filter(type_compte='recette')
        for compte in comptes_produits:
            solde = compte.get_solde_actuel(self)
            if solde == 0:
                continue
            
            EcritureComptable.objects.create(
                compte=compte,
                montant=abs(solde),
                type_ecriture='CR' if solde > 0 else 'DB',
                transaction=transaction_cloture
            )

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
                type_ecriture='CR' if solde > 0 else 'DB',
                transaction=transaction_cloture
            )
            
            EcritureComptable.objects.create(
                compte=compte_resultat,
                montant=abs(solde),
                type_ecriture='CR' if solde < 0 else 'DB',
                transaction=transaction_cloture
            )

    def calculer_resultat_net(self):
        from .ecriture_comptable import EcritureComptable

        total_produits = EcritureComptable.objects.filter(
            compte__type_compte='recette', 
            transaction__exercice=self, 
            type_ecriture='CR'
        ).aggregate(total=Sum(F('montant')))['total'] or decimal.Decimal(0.0)

        total_charges = EcritureComptable.objects.filter(
            compte__type_compte='depense', 
            transaction__exercice=self, 
            type_ecriture='DB'
        ).aggregate(total=Sum(F('montant')))['total'] or decimal.Decimal(0.0)

        return total_produits - total_charges

    def reporter_resultat_net(self, resultat_net, compte_resultat_classe8, compte_resultat_classe1):
        from .transaction import Transaction
        from .ecriture_comptable import EcritureComptable

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