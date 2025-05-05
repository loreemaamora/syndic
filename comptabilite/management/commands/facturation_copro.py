from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction, models
from django.db.models.functions import ExtractMonth, ExtractYear
from datetime import timedelta
from comptabilite.models import Abonnement, Transaction, EcritureComptable, Compte, ExerciceComptable

class Command(BaseCommand):
    help = "Facture les abonnements mensuels avec contrôle des doublons par mois"

    def add_arguments(self, parser):
        parser.add_argument('--date', help="Date de simulation (format YYYY-MM-DD)")
        parser.add_argument('--force', action='store_true', help="Forcer la facturation même si déjà faite")

    def handle(self, *args, **options):
        try:
            # Gestion de la date
            aujourdhui = (
                timezone.datetime.strptime(options['date'], '%Y-%m-%d').date() 
                if options.get('date') 
                else timezone.now().date()
            )
        except ValueError:
            self.stderr.write("❌ Format de date invalide. Utilisez YYYY-MM-DD")
            return

        debut_mois = aujourdhui.replace(day=1)
        fin_mois = (debut_mois + timedelta(days=32)).replace(day=1)

        self.stdout.write(f"\n📅 Traitement des abonnements pour {aujourdhui} (mois: {debut_mois} à {fin_mois})")

        with transaction.atomic():
            exercice = ExerciceComptable.get_exercice_actuel()
            if not exercice:
                self.stderr.write("❌ Aucun exercice comptable actif!")
                return

            compte_recette, _ = Compte.objects.get_or_create(
                compte="7111", 
                defaults={'libelle': 'Appels de fonds', 'type_compte': 'recette'}
            )
            compte_client, _ = Compte.objects.get_or_create(
                compte="3421", 
                defaults={'libelle': 'Copropriétaire individualisé', 'type_compte': 'actif'}
            )

            # Préchargement des transactions existantes pour le mois
            transactions_existantes = Transaction.objects.filter(
                date_operation__gte=debut_mois,
                date_operation__lt=fin_mois,
                libelle__startswith="CONTRIBUTION MENSUELLE"
            ).annotate(
                annee=ExtractYear('date_operation'),
                mois=ExtractMonth('date_operation')
            ).values_list('libelle', 'annee', 'mois')

            transactions_existantes = set(transactions_existantes)

            abonnements = Abonnement.objects.filter(
                frequence='mensuel',
                actif=True,
                date_debut__lte=aujourdhui
            ).select_related('lot')

            total, existants, nouveaux = 0, 0, 0

            for abo in abonnements:
                libelle = f"CONTRIBUTION MENSUELLE LOT#{abo.lot.code} - {aujourdhui.strftime('%Y-%m')}"
                cle_doublon = (libelle, aujourdhui.year, aujourdhui.month)
                total += 1

                if not options['force'] and cle_doublon in transactions_existantes:
                    self.stdout.write(f"⏭️ {str(abo.lot):5} : déjà facturé (mois en cours)")
                    existants += 1
                    continue

                transac = Transaction.objects.create(
                    date_operation=aujourdhui,
                    libelle=libelle,
                    exercice=exercice
                )

                EcritureComptable.objects.bulk_create([
                    EcritureComptable(
                        compte=compte_client,
                        montant=abo.montant,
                        type_ecriture='DB',
                        transaction=transac,
                        lot=abo.lot
                    ),
                    EcritureComptable(
                        compte=compte_recette,
                        montant=abo.montant,
                        type_ecriture='CR',
                        transaction=transac
                    )
                ])

                nouveaux += 1
                self.stdout.write(f"✅ {str(abo.lot):5} : {abo.montant:8.2f} MAD")

        self.stdout.write(f"\n📊 Récapitulatif:")
        self.stdout.write(f"• Factures trouvées    : {total}")
        self.stdout.write(f"• Déjà facturés         : {existants}")
        self.stdout.write(f"• Nouvelles facturations  : {nouveaux}")
        self.stdout.write(f"🎯 Traitement terminé avec succès!")