# ===========================================
# api/urls.py
# ===========================================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router pour les ViewSets (si nécessaire plus tard)
router = DefaultRouter()

urlpatterns = [
    # URLs du router
    path('', include(router.urls)),
    
    # ===========================================
    # ENDPOINTS FRONTEND (publics)
    # ===========================================
    
    # Endpoint principal - Liste des produits vérifiés
    path('', views.api_produits, name='api-produits'),
    
    # Recherche de produits
    path('recherche/<str:text>/', views.recherche_produits, name='recherche-produits'),
    
    # Statistiques générales
    path('nbretotaleDeDroduitsEtDeStart/', views.nombre_total_produits, name='nombre-total'),
    
    # Produits par catégorie
    path('categorie/<str:nom_categorie>/', views.produits_par_categorie, name='produits-categorie'),
    
    # Tri et filtrage des produits
    path('trie/', views.trier_produits, name='trier-produits'),
    
    # Détail d'un produit
    path('produit/<int:produit_id>/', views.details_produit, name='detail-produit'),
    
    # Informations sur un vendeur
    path('seller/<int:seller_id>/', views.detail_seller, name='detail-seller'),
    
    # Produits d'un vendeur spécifique
    path('seller/<int:seller_id>/produits/', views.produits_seller, name='produits-seller'),
    
    # ===========================================
    # ENDPOINTS ADMINISTRATION/GESTION
    # ===========================================
    
    # Authentification
    path('auth/login/', views.login_user, name='login'),
    path('auth/logout/', views.logout_user, name='logout'),
    path('auth/register/seller/', views.register_seller, name='register-seller'),
    path('auth/register/client/', views.register_client, name='register-client'),
    
    # Gestion des produits (CRUD)
    path('produits/', views.liste_produits, name='liste-produits'),
    path('produits/create/', views.creer_produit, name='creer-produit'),
    path('produits/<int:produit_id>/update/', views.modifier_produit, name='modifier-produit'),
    path('produits/<int:produit_id>/delete/', views.supprimer_produit, name='supprimer-produit'),
    
    # Gestion des vendeurs
    path('sellers/', views.liste_sellers, name='liste-sellers'),
    path('sellers/<int:seller_id>/verify/', views.verifier_seller, name='verifier-seller'),
    
    
    # Gestion des clients
    path('clients/', views.liste_clients, name='liste-clients'),
    
    # Upload d'images
    path('upload/image/', views.upload_image, name='upload-image'),
    
    # Statistiques détaillées
    path('stats/', views.statistiques_dashboard, name='statistiques'),
    path('stats/seller/<int:seller_id>/', views.statistiques_seller, name='stats-seller'),
]