from django.db import models
from django.core.validators import RegexValidator

class Fournisseur(models.Model):
    """
    Modèle simplifié représentant un fournisseur avec raison sociale
    """
    # Identifiant unique (requis)
    code = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex='^[A-Z0-9_-]+$',
                message='Le code doit contenir seulement des majuscules, chiffres, - ou _'
            )
        ],
        help_text="Code unique du fournisseur (ex: FRN-ELEC-001)",
        verbose_name="Code fournisseur"
    )
    
    # Informations légales
    raison_sociale = models.CharField(
        max_length=200,
        help_text="Raison sociale complète du fournisseur",
        verbose_name="Raison sociale"
    )
    
    # Coordonnées
    adresse = models.TextField(blank=True, verbose_name="Adresse")
    ville = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    
    # Contacts
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
    email = models.EmailField(
        blank=True,
        verbose_name="Email"
    )
    
    # Métadonnées
    date_creation = models.DateField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    actif = models.BooleanField(
        default=True,
        help_text="Désactivez au lieu de supprimer",
        verbose_name="Actif"
    )

    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ['raison_sociale']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['raison_sociale']),
        ]

    def __str__(self):
        return f"{self.code} - {self.raison_sociale}"

    @property
    def coordonnees(self):
        """Formatage des coordonnées complètes"""
        coordonnees = []
        if self.adresse:
            coordonnees.append(self.adresse)
        if self.ville:
            coordonnees.append(self.ville)
        if self.telephone:
            coordonnees.append(f"Tél: {self.telephone}")
        if self.email:
            coordonnees.append(f"Email: {self.email}")
        return "\n".join(coordonnees) if coordonnees else "Aucune coordonnée"