from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models.ecriture_comptable import EcritureComptable

@receiver(post_save, sender=EcritureComptable)
@receiver(post_delete, sender=EcritureComptable)
def update_solde(sender, instance, **kwargs):
    instance.compte.mettre_a_jour_solde(instance.transaction.exercice)