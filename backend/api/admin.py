# ===========================================
# api/admin.py
# ===========================================
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, Seller, Client, Produit
import re 
import decimal

def to_float(value):
    """Convertit proprement n'importe quelle valeur en float, sinon 0.0"""
    if value is None or value == '':
        return 0.0
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, decimal.Decimal):
        return float(value)
    try:
        # Nettoie la chaîne (enlève € ou espaces)
        value = str(value).replace('€', '').replace(',', '.').strip()
        return float(value)
    except Exception:
        return 0.0
# ===========================================
# CONFIGURATION ADMIN POUR USER
# ===========================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'is_seller', 'is_client', 'is_staff', 'date_joined')
    list_filter = ('is_seller', 'is_client', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('is_seller', 'is_client'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('email', 'is_seller', 'is_client'),
        }),
    )

# ===========================================
# CONFIGURATION ADMIN POUR SELLER
# ===========================================

@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('nom', 'user_email', 'status', 'numero', 'localisation', 'total_produits_count', 'start')
    list_filter = ('status', 'start', 'localisation')
    search_fields = ('nom', 'user__email', 'numero', 'localisation')
    readonly_fields = ('start', 'total_produits_count')
    ordering = ('-start',)
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('user', 'nom', 'numero', 'localisation')
        }),
        ('Statut et validation', {
            'fields': ('status', 'start')
        }),
        ('Informations supplémentaires', {
            'fields': ('avis',),
            'classes': ('collapse',)
        }),
        ('Statistiques', {
            'fields': ('total_produits_count',),
            'classes': ('collapse',)
        })
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email utilisateur'
    user_email.admin_order_field = 'user__email'
    
    def total_produits_count(self, obj):
        count = obj.total_produits
        if count > 0:
            url = reverse('admin:api_produit_changelist') + f'?seller__id__exact={obj.id}'
            return format_html('<a href="{}">{} produits</a>', url, count)
        return count
    total_produits_count.short_description = 'Nombre de produits'
    
    actions = ['verifier_sellers', 'desactiver_sellers']
    
    def verifier_sellers(self, request, queryset):
        updated = queryset.update(status='verified')
        self.message_user(request, f'{updated} vendeurs ont été vérifiés.')
    verifier_sellers.short_description = 'Vérifier les vendeurs sélectionnés'
    
    def desactiver_sellers(self, request, queryset):
        updated = queryset.update(status='unverified')
        self.message_user(request, f'{updated} vendeurs ont été désactivés.')
    desactiver_sellers.short_description = 'Désactiver les vendeurs sélectionnés'

# ===========================================
# CONFIGURATION ADMIN POUR CLIENT
# ===========================================

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'user_username', 'relation', 'date_joined')
    search_fields = ('user__email', 'user__username', 'relation')
    list_filter = ('user__date_joined',)
    ordering = ('-user__date_joined',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'
    
    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Nom utilisateur'
    user_username.admin_order_field = 'user__username'
    
    def date_joined(self, obj):
        return obj.user.date_joined
    date_joined.short_description = 'Date d\'inscription'
    date_joined.admin_order_field = 'user__date_joined'

# ===========================================
# CONFIGURATION ADMIN POUR PRODUIT
# ===========================================

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'seller_name', 'prix_display', 'categorie', 'status', 'quantite', 'likes', 'created_at')
    list_filter = ('status', 'categorie', 'created_at', 'seller__status')
    search_fields = ('nom', 'description', 'tags', 'seller__nom')
    readonly_fields = ('created_at', 'updated_at', 'prix_avec_reduction_display', 'image_preview')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('nom', 'seller', 'prix', 'ancien_prix', 'reduction', 'prix_avec_reduction_display')
        }),
        ('Classification', {
            'fields': ('categorie', 'tags', 'status')
        }),
        ('Description et médias', {
            'fields': ('description', 'image_url', 'image_preview')
        }),
        ('Caractéristiques', {
            'fields': ('couleur', 'taille', 'quantite')
        }),
        ('Statistiques', {
            'fields': ('likes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ()
    
    def seller_name(self, obj):
        return obj.seller.nom
    seller_name.short_description = 'Vendeur'
    seller_name.admin_order_field = 'seller__nom'


   
    def prix_display(self, obj):
        try:
            prix = to_float(obj.prix)
            reduction = to_float(obj.reduction)
            
            if reduction > 0:
                prix_red = to_float(obj.prix_avec_reduction)
                return format_html(
                    '<span style="text-decoration: line-through;">{} FCFA</span> '
                    '<strong>{} FCFA</strong> '
                    '(-{}%)',
                    f'{prix:.2f}', f'{prix_red:.2f}', f'{reduction:.0f}'
                )
            else:
                return format_html('{} FCFA', f'{prix:.2f}')
        except Exception as e:
            return f'Erreur prix: {str(e)}'

    prix_display.short_description = 'Prix'

    def prix_avec_reduction_display(self, obj):
        try:
            prix = to_float(obj.prix)
            reduction = to_float(obj.reduction)
            
            if reduction > 0:
                prix_red = to_float(obj.prix_avec_reduction)
                return format_html('{} FCFA (prix réduit)', f'{prix_red:.2f}')
            else:
                return format_html('{} FCFA (prix normal)', f'{prix:.2f}')
        except Exception as e:
            return f'Erreur prix: {str(e)}'

    prix_avec_reduction_display.short_description = 'Prix final'


    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px; border-radius: 5px;"/>',
                obj.image_url.url
            )
        return 'Aucune image'
    image_preview.short_description = 'Aperçu image'
    
    actions = ['verifier_produits', 'desactiver_produits', 'appliquer_promotion']
    
    def verifier_produits(self, request, queryset):
        updated = queryset.update(status='verified')
        self.message_user(request, f'{updated} produits ont été vérifiés.')
    verifier_produits.short_description = 'Vérifier les produits sélectionnés'
    
    def desactiver_produits(self, request, queryset):
        updated = queryset.update(status='unverified')
        self.message_user(request, f'{updated} produits ont été désactivés.')
    desactiver_produits.short_description = 'Désactiver les produits sélectionnés'
    
    def appliquer_promotion(self, request, queryset):
        # Applique une réduction de 20% aux produits sélectionnés
        updated = 0
        for produit in queryset:
            if produit.reduction == 0:  # Seulement si pas déjà en promotion
                produit.ancien_prix = produit.prix
                produit.reduction = 20
                produit.categorie = 'promotion'
                produit.save()
                updated += 1
        self.message_user(request, f'{updated} produits ont été mis en promotion (20% de réduction).')
    appliquer_promotion.short_description = 'Appliquer une promotion de 20%%'

# ===========================================
# CONFIGURATION GÉNÉRALE DE L'ADMIN
# ===========================================

# Personnalisation du site admin
admin.site.site_header = 'Administration PinShop'
admin.site.site_title = 'PinShop Admin'
admin.site.index_title = 'Panneau de gestion PinShop'

# Ajout de statistiques sur la page d'accueil de l'admin
def get_admin_stats():
    """Retourne des statistiques pour l'affichage admin"""
    from django.db.models import Count, Sum
    
    stats = {
        'total_users': User.objects.count(),
        'total_sellers': Seller.objects.count(),
        'verified_sellers': Seller.objects.filter(status='verified').count(),
        'total_clients': Client.objects.count(),
        'total_produits': Produit.objects.count(),
        'verified_produits': Produit.objects.filter(status='verified').count(),
        'produits_en_stock': Produit.objects.filter(quantite__gt=0).count(),
    }
    
    return stats