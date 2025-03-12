#accounts/models.py
#----

from django.db import models
from authemail.models import EmailUserManager, EmailAbstractUser

class MyUser(EmailAbstractUser):
	# Custom fields
	# date_of_birth = models.DateField('Date of birth', null=True, blank=True)
    
	# Required
	objects = EmailUserManager()

class Tiers(models.Model):
    TYPE_TIERS_CHOICES = [
        ('coproprietaire', 'Copropriétaire'),
        ('fournisseur', 'Fournisseur'),
        # Ajoutez d'autres types ici
    ]
    type_tiers = models.CharField(max_length=20, choices=TYPE_TIERS_CHOICES)
    user=models.ForeignKey(MyUser, on_delete=models.SET_NULL, related_name='lots', blank=True, null=True)

    def __str__(self):
        return self.nom


class LotIndividuel (models.Model):
	immeuble=models.CharField(max_length=2)
	lot_individuel=models.CharField(max_length=3)
	proprietaire = models.ForeignKey(
        Tiers,
        on_delete=models.SET_NULL,
        related_name="lots",
        blank=True,
        null=True,
        limit_choices_to={"type_tiers": "coproprietaire"},  # Filter by type
    )

	def __str__(self):
		if self.proprietaire:
			return f"{self.lot_individuel} - {self.proprietaire.email}"
		else:
			return f"{self.lot_individuel} - Non affecté"