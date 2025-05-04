#mysite/patrimoine/admin.py
#----

from django.db import models

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

    def __str__(self):
        return f"{self.code} - {self.libelle}"