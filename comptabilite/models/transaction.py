import os
from datetime import date
from django.db import models
from django.core.exceptions import ValidationError

class Transaction(models.Model):
    date_creation = models.DateField(auto_now_add=True)
    date_operation = models.DateField()
    libelle = models.CharField(max_length=255)
    justif = models.FileField(upload_to='transactions/', null=True, blank=True)
    exercice = models.ForeignKey(
        'ExerciceComptable', 
        on_delete=models.CASCADE, 
        related_name='transactions_exercice', 
        limit_choices_to={'est_ouvert': True}
    )

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
            from django.db.models import Sum
            from decimal import Decimal
            
            balance = self.ecritures.values('type_ecriture').annotate(total=Sum('montant'))
            total_debit = next((b['total'] for b in balance if b['type_ecriture'] == 'DB'), Decimal(0.0))
            total_credit = next((b['total'] for b in balance if b['type_ecriture'] == 'CR'), Decimal(0.0))
            
            if total_debit != total_credit:
                raise ValidationError("Les écritures comptables doivent être équilibrées (Total débit = Total crédit).")

    def clean_justif(self):
        if self.justif:
            ext = os.path.splitext(self.justif.name)[1].lower()
            if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
                raise ValidationError("Le justificatif doit être un fichier PDF ou une image (PDF, JPG, JPEG, PNG).")
            
            if self.justif.size > 1 * 1024 * 1024:  # 1 MB
                raise ValidationError("La taille du justificatif ne doit pas dépasser 1 MB.")

            if self.date_operation > date.today():
                raise ValidationError("La date de l'opération ne peut pas être postérieure à la date d'aujourd'hui.")