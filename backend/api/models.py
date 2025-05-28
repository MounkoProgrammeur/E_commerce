from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from PIL import Image
import os
import json

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_seller = models.BooleanField(default=False)
    is_client = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='api_user_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='api_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class Seller(models.Model):
    STATUS_CHOICES = [
        ('verified', 'Vérifié'),
        ('unverified', 'Non vérifié'),  # Corrigé: 'univerified' → 'unverified'
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    nom = models.CharField(max_length=25)
    numero = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unverified')
    start = models.DateTimeField(auto_now_add=True)
    avis = models.TextField(blank=True)
    localisation = models.CharField(max_length=255)

    def __str__(self):
        return self.nom
    
    @property
    def total_produits(self):
        return self.produits.count()

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    relation = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.email

class Produit(models.Model):
    STATUS_CHOICES = [
        ('verified', 'Vérifié'),
        ('unverified', 'Non vérifié'),
    ]
    CATEGORIE_CHOICES = [
        ('tendances', 'Tendances'),
        ('nouveautés', 'Nouveautés'),
        ('populaire', 'Populaire'),
        ('promotion', 'Promotion'),
        ('chere', 'Chère'),
    ]
    nom = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unverified')
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    couleur = models.JSONField(default=list, help_text='Liste des couleurs disponibles')
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)
    tags = models.TextField(help_text='Séparer les tags par des virgules')
    description = models.TextField()
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='produits')
    ancien_prix = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    likes = models.PositiveIntegerField(default=0)
    reduction = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    image_url = models.ImageField(upload_to='produits/', blank=True, null=True)
    taille = models.JSONField(default=list, help_text='Liste des tailles disponibles')
    quantite = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.nom

    def clean(self):
        # Valider que couleur et taille sont des listes
        if not isinstance(self.couleur, list):
            raise ValidationError({'couleur': 'Le champ couleur doit être une liste.'})
        if not isinstance(self.taille, list):
            raise ValidationError({'taille': 'Le champ taille doit être une liste.'})

    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    @property
    def prix_avec_reduction(self):
        try:
            prix = float(self.prix or 0.0)  # Gérer None ou valeurs invalides
            reduction = float(self.reduction or 0.0)  # Gérer None ou valeurs invalides
            if reduction > 0:
                return prix * (1 - reduction / 100)
            return prix
        except (ValueError, TypeError):
            return 0.0  # Valeur par défaut en cas d'erreur