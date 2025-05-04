from django.db import models
from django.db.models import Q
from authemail.models import EmailUserManager, EmailAbstractUser

from django.core.validators import RegexValidator

class MyUser(EmailAbstractUser):
    telephone = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                regex='^[0-9]{10}$',
                message='Le numéro de téléphone doit contenir exactement 10 chiffres.',
            )
        ],
        null=True,
        blank=True
    )    
    # Required
    objects = EmailUserManager()

# class Tier(models.Model):  # Renommé au singulier
#     TYPE_TIER_CHOICES = [
#         ('coproprietaire', 'Copropriétaire'),
#         ('immeuble', 'Immeuble'),
#         ('fournisseur', 'Fournisseur'),
#     ]
#     type_tier = models.CharField(max_length=20, choices=TYPE_TIER_CHOICES)
#     user = models.ForeignKey(
#         MyUser, 
#         on_delete=models.SET_NULL, 
#         related_name='tiers',
#         blank=True, 
#         null=True
#     )

#     def __str__(self):
#         return f"{self.type_tier} - {self.user.email if self.user else 'Anonyme'}"

# class Immeuble(models.Model):
#     code = models.CharField(max_length=2)
#     libelle = models.CharField(max_length=20)
    
#     def __str__(self):
#         return f"{self.code} - {self.libelle}"

# class Lot(models.Model):
#     code = models.CharField(max_length=3)
#     libelle = models.CharField(max_length=20)
#     immeuble = models.ForeignKey(
#         Immeuble, 
#         on_delete=models.CASCADE, 
#         related_name="lots"
#     )
#     proprietaire = models.ForeignKey(
#         Tier,
#         on_delete=models.SET_NULL,
#         related_name="lots_proprietaire",
#         blank=True,
#         null=True,
#         limit_choices_to=Q(type_tier='coproprietaire') | Q(type_tier='immeuble')
#     )
#     num_TF = models.CharField(max_length=20, null=True, blank=True)
#     titre_foncier = models.FileField(upload_to='titres/', null=True, blank=True)

#     def __str__(self):
#         if self.proprietaire:
#             return f"{self.code} - {self.proprietaire.user.email if self.proprietaire.user else 'Propriétaire sans email'}"
#         return f"{self.code} - Non affecté"