#mysite/patrimoine/models.py
#----

from django.db import models
from accounts.models import MyUser

class Immeuble(models.Model):
    code = models.CharField(max_length=2)
    libelle = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.code} - {self.libelle}"

class Lot(models.Model):
    code = models.CharField(max_length=3)
    libelle = models.CharField(max_length=20)
    immeuble = models.ForeignKey(
        Immeuble, 
        on_delete=models.CASCADE, 
        related_name="lots"
    )

    proprietaire = models.ForeignKey(
        MyUser,
        on_delete=models.SET_NULL,
        related_name="lots_proprietaire",
        blank=True,
        null=True
    )
    num_TF = models.CharField(max_length=20, null=True, blank=True)
    titre_foncier = models.FileField(upload_to='titres/', null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.libelle}"