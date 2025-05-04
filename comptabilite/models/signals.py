from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete])
def update_solde(sender, **kwargs):
    if sender.__name__ == 'EcritureComptable':
        instance = kwargs['instance']
        instance.compte.mettre_a_jour_solde(instance.transaction.exercice)