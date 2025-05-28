from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login
from django.core.files.storage import default_storage
from django.http import Http404
import uuid
import logging
from .models import Produit, Seller, Client, User
from .serializers import (
    ProduitSerializer, ProduitCreateSerializer, SellerSerializer, 
    SellerCreateSerializer, ClientSerializer, ClientCreateSerializer, UserSerializer
)

# Configuration des logs pour le débogage
logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100

# ===========================================
# ENDPOINTS FRONTEND (publics)
# ===========================================

@api_view(['GET'])
@permission_classes([AllowAny])
def api_produits(request):
    try:
        produits = Produit.objects.filter(status='verified').order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(produits, request)
        
        serializer = ProduitSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Exception as e:
        logger.error(f"Erreur dans api_produits: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des produits',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def recherche_produits(request, text):
    """Endpoint GET /recherche/{text}/ - Recherche de produits"""
    try:
        produits = Produit.objects.filter(
            Q(nom__icontains=text) | Q(tags__icontains=text) | Q(description__icontains=text),
            status='verified'
        ).distinct()
        
        if not produits.exists() and len(text) >= 4:
            prefix = text[:4]
            produits = Produit.objects.filter(
                Q(nom__istartswith=prefix) | Q(tags__icontains=prefix),
                status='verified'
            ).distinct()
        
        serializer = ProduitSerializer(produits, many=True)
        return Response({
            'count': produits.count(),
            'results': serializer.data
        })
    
    except Exception as e:
        logger.error(f"Erreur dans recherche_produits: {str(e)}")
        return Response({
            'error': 'Erreur lors de la recherche',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
@permission_classes([AllowAny])
def nombre_total_produits(request):
    try:
        total = Produit.objects.count()  # Compte tous les produits
        total_verifies = Produit.objects.filter(status='verified').count()
        total_sellers = Seller.objects.filter(status='verified').count()
        return Response({
            'total_produits': total,
            'produits_verifies': total_verifies,
            'total_sellers': total_sellers,
            'message': f'Total: {total} produits ({total_verifies} vérifiés), {total_sellers} vendeurs vérifiés'
        })
    except Exception as e:
        logger.error(f"Erreur dans nombre_total_produits: {str(e)}")
        return Response({
            'error': 'Erreur lors du comptage',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
@permission_classes([AllowAny])
def produits_par_categorie(request, nom_categorie):
    """Endpoint GET /categorie/{nom_categorie}/"""
    try:
        categories_valides = dict(Produit.CATEGORIE_CHOICES)
        if nom_categorie not in categories_valides:
            return Response({
                'error': 'Catégorie invalide',
                'categories_disponibles': list(categories_valides.keys())
            }, status=status.HTTP_400_BAD_REQUEST)
        
        produits = Produit.objects.filter(
            categorie=nom_categorie,
            status='verified'
        ).order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(produits, request)
        
        serializer = ProduitSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Exception as e:
        logger.error(f"Erreur dans produits_par_categorie: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération par catégorie',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def trier_produits(request):
    """Endpoint GET /trie/ avec paramètres de requête"""
    try:
        couleur = request.GET.get('couleur')
        prix_min = request.GET.get('prix_min')
        prix_max = request.GET.get('prix_max')
        taille = request.GET.get('taille')
        categorie = request.GET.get('categorie')
        
        produits = Produit.objects.filter(status='verified')
        
        if couleur:
            produits = produits.filter(couleur__icontains=couleur)
        
        if prix_min:
            try:
                produits = produits.filter(prix__gte=float(prix_min))
            except ValueError:
                pass
        
        if prix_max:
            try:
                produits = produits.filter(prix__lte=float(prix_max))
            except ValueError:
                pass
        
        if taille:
            produits = produits.filter(taille__icontains=taille)
        
        if categorie:
            produits = produits.filter(categorie=categorie)
        
        ordre = request.GET.get('ordre', '-created_at')
        if ordre in ['prix', '-prix', 'nom', '-nom', 'created_at', '-created_at']:
            produits = produits.order_by(ordre)
        else:
            produits = produits.order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(produits, request)
        
        serializer = ProduitSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Exception as e:
        logger.error(f"Erreur dans trier_produits: {str(e)}")
        return Response({
            'error': 'Erreur lors du tri',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def actualiser_produits(request):
    """Endpoint GET /actualiser/ - Recharge d'autres produits aléatoires"""
    try:
        exclus = request.GET.get('exclus', '')
        ids_exclus = []
        if exclus:
            try:
                ids_exclus = [int(x) for x in exclus.split(',') if x.isdigit()]
            except:
                pass
        
        produits = Produit.objects.filter(status='verified')
        if ids_exclus:
            produits = produits.exclude(id__in=ids_exclus)
        
        produits = produits.order_by('?')[:30]
        
        serializer = ProduitSerializer(produits, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })
    
    except Exception as e:
        logger.error(f"Erreur dans actualiser_produits: {str(e)}")
        return Response({
            'error': "Erreur lors de l'actualisation",
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
@permission_classes([AllowAny])
def details_produit(request, produit_id):
    """Endpoint GET /produit/<produit_id>/ - Détails d'un produit"""
    try:
        produit = get_object_or_404(Produit, id=produit_id, status='verified')
        serializer = ProduitSerializer(produit)
        return Response(serializer.data)
    except Http404:
        return Response({'error': 'Produit non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur dans details_produit: {str(e)}")
        return Response({'error': 'Erreur lors de la récupération du produit', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ===========================================
# ENDPOINTS ADMINISTRATION - VENDEURS
# ===========================================

@api_view(['GET'])
@permission_classes([AllowAny])  # Accessible à tous, car les vendeurs peuvent voir leurs propres produits
def seller_produits(request, id):
    """Endpoint GET /sellerProduits/{id}/ - Produits d'un vendeur"""
    try:
        seller = get_object_or_404(Seller, id=id)
        produits = seller.produits.all().order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(produits, request)
        
        serializer = ProduitSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Http404:
        return Response({
            'error': 'Vendeur non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur dans seller_produits: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des produits du vendeur',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])  # Restreint aux admins
def ajouter_produit(request):
    """Endpoint GET/POST /ajouterLesProduits/ - Afficher le formulaire ou créer un produit"""
    try:
        if request.method == 'GET':
            categories = dict(Produit.CATEGORIE_CHOICES) if hasattr(Produit, 'CATEGORIE_CHOICES') else {}
            return Response({
                'message': 'Formulaire d\'ajout de produit',
                'categories_disponibles': categories,
                'endpoint': 'POST /ajouterLesProduits/',
                'champs_requis': [
                    'nom', 'description', 'prix', 'categorie', 
                    'seller_id', 'couleur', 'taille', 'tags'
                ]
            })
        
        elif request.method == 'POST':
            # Logique de création existante
            logger.info(f"Requête ajouter_produit par {request.user}: {request.data}")
            serializer = ProduitCreateSerializer(data=request.data)
            if serializer.is_valid():
                produit = serializer.save()
                response_serializer = ProduitSerializer(produit)
                logger.info(f"Produit créé: {produit.nom}")
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
            logger.error(f"Erreurs de validation dans ajouter_produit: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Erreur dans ajouter_produit: {str(e)}")
        return Response({
            'error': 'Erreur lors de la création du produit',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])
def modifier_produit(request, produit_id):
    """Endpoint PUT/PATCH /produits/<produit_id>/update/"""
    try:
        logger.info(f"Requête modifier_produit par {request.user} pour produit {produit_id}: {request.data}")
        produit = get_object_or_404(Produit, id=produit_id)
        serializer = ProduitCreateSerializer(produit, data=request.data, partial=True)
        if serializer.is_valid():
            produit_updated = serializer.save()
            response_serializer = ProduitSerializer(produit_updated)
            logger.info(f"Produit modifié: {produit_updated.nom}")
            return Response(response_serializer.data)
        logger.error(f"Erreurs de validation dans modifier_produit: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Http404:
        return Response({'error': 'Produit non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur dans modifier_produit: {str(e)}")
        return Response({'error': 'Erreur lors de la modification du produit', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def supprimer_produit(request, produit_id):
    """Endpoint DELETE /produits/<produit_id>/delete/"""
    try:
        logger.info(f"Requête supprimer_produit par {request.user} pour produit {produit_id}")
        produit = get_object_or_404(Produit, id=produit_id)
        nom_produit = produit.nom
        produit.delete()
        logger.info(f"Produit supprimé: {nom_produit}")
        return Response({'message': f'Produit "{nom_produit}" supprimé avec succès'})
    except Http404:
        return Response({'error': 'Produit non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur dans supprimer_produit: {str(e)}")
        return Response({'error': 'Erreur lors de la suppression du produit', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===========================================
# ENDPOINTS ADMINISTRATION - ADMINISTRATEUR
# ===========================================

@api_view(['GET'])
@permission_classes([IsAdminUser])  # Restreint aux admins
def produits_non_verifies(request):
    """Endpoint GET /produits-non-verifies/ - Produits non vérifiés"""
    try:
        logger.info(f"Requête produits_non_verifies par {request.user}")
        produits = Produit.objects.filter(status='unverified').order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(produits, request)
        
        serializer = ProduitSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Exception as e:
        logger.error(f"Erreur dans produits_non_verifies: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des produits non vérifiés',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])  # Restreint aux admins
def verifier_produit(request, id):
    """Endpoint PUT/PATCH /verifier-produit/{id}/ - Vérifier un produit"""
    try:
        logger.info(f"Requête verifier_produit par {request.user} pour produit {id}")
        produit = get_object_or_404(Produit, id=id)
        
        produit.status = 'verified'
        produit.save()
        
        serializer = ProduitSerializer(produit)
        logger.info(f"Produit vérifié: {produit.nom}")
        return Response({
            'message': f'Produit "{produit.nom}" vérifié avec succès',
            'produit': serializer.data
        })
    
    except Http404:
        return Response({
            'error': 'Produit non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur dans verifier_produit: {str(e)}")
        return Response({
            'error': 'Erreur lors de la vérification du produit',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ===========================================
# FONCTIONS MANQUANTES POUR LES URLs
# ===========================================

@api_view(['GET'])
@permission_classes([AllowAny])
def detail_seller(request, seller_id):
    """Endpoint GET /seller/{seller_id}/ - Détails d'un vendeur"""
    try:
        seller = get_object_or_404(Seller, id=seller_id)
        serializer = SellerSerializer(seller)
        return Response(serializer.data)
    
    except Http404:
        return Response({
            'error': 'Vendeur non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur dans detail_seller: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération du vendeur',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def produits_seller(request, seller_id):
    """Endpoint GET /seller/{seller_id}/produits/ - Produits d'un vendeur"""
    try:
        seller = get_object_or_404(Seller, id=seller_id)
        produits = seller.produits.filter(status='verified').order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(produits, request)
        
        serializer = ProduitSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Http404:
        return Response({
            'error': 'Vendeur non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur dans produits_seller: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des produits du vendeur',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Endpoint POST /auth/login/ - Connexion utilisateur"""
    try:
        logger.info(f"Requête login_user: {request.data}")
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            logger.error("Username ou password manquant")
            return Response({
                'error': 'Username et password requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            serializer = UserSerializer(user)
            logger.info(f"Connexion réussie pour {username}")
            return Response({
                'message': 'Connexion réussie',
                'user': serializer.data
            })
        else:
            logger.error("Identifiants invalides")
            return Response({
                'error': 'Identifiants invalides'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    except Exception as e:
        logger.error(f"Erreur dans login_user: {str(e)}")
        return Response({
            'error': 'Erreur lors de la connexion',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Endpoint POST /auth/logout/ - Déconnexion utilisateur"""
    try:
        logger.info(f"Déconnexion de {request.user}")
        return Response({
            'message': 'Déconnexion réussie'
        })
    
    except Exception as e:
        logger.error(f"Erreur dans logout_user: {str(e)}")
        return Response({
            'error': 'Erreur lors de la déconnexion',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_seller(request):
    """Endpoint POST /auth/register/seller/ - Inscription vendeur"""
    try:
        logger.info(f"Requête register_seller: {request.data}")
        serializer = SellerCreateSerializer(data=request.data)
        if serializer.is_valid():
            seller = serializer.save()
            response_serializer = SellerSerializer(seller)
            logger.info(f"Vendeur créé: {seller.nom}")
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        logger.error(f"Erreurs de validation dans register_seller: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Erreur dans register_seller: {str(e)}")
        return Response({
            'error': "Erreur lors de l'inscription du vendeur",
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_client(request):
    """Endpoint POST /auth/register/client/ - Inscription client"""
    try:
        logger.info(f"Requête register_client: {request.data}")
        serializer = ClientCreateSerializer(data=request.data)
        if serializer.is_valid():
            client = serializer.save()
            response_serializer = ClientSerializer(client)
            logger.info(f"Client créé: {client.user.email}")
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        logger.error(f"Erreurs de validation dans register_client: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Erreur dans register_client: {str(e)}")
        return Response({
            'error': "Erreur lors de l'inscription du client",
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def liste_produits(request):
    """Endpoint GET /produits/ - Liste de tous les produits"""
    try:
        produits = Produit.objects.all().order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(produits, request)
        
        serializer = ProduitSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Exception as e:
        logger.error(f"Erreur dans liste_produits: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des produits',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ...existing code...

@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])  # Restreint aux admins
def creer_produit(request):
    """Endpoint GET/POST /produits/create/ - Afficher le formulaire ou créer un produit"""
    try:
        if request.method == 'GET':
            categories = dict(Produit.CATEGORIE_CHOICES) if hasattr(Produit, 'CATEGORIE_CHOICES') else {}
            return Response({
                'message': 'Formulaire de création de produit',
                'categories_disponibles': categories,
                'endpoint': 'POST /produits/create/',
                'champs_requis': [
                    'nom', 'description', 'prix', 'categorie', 
                    'seller_id', 'couleur', 'taille', 'tags'
                ]
            })
        
        elif request.method == 'POST':
            logger.info(f"Requête creer_produit par {request.user}: {request.data}")
            serializer = ProduitCreateSerializer(data=request.data)
            if serializer.is_valid():
                produit = serializer.save()
                response_serializer = ProduitSerializer(produit)
                logger.info(f"Produit créé: {produit.nom}")
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
            logger.error(f"Erreurs de validation dans creer_produit: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Erreur dans creer_produit: {str(e)}")
        return Response({
            'error': 'Erreur lors de la création du produit',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ...existing code...

@api_view(['GET'])
@permission_classes([IsAdminUser])  # ou AllowAny selon ton besoin
def liste_sellers(request):
    try:
        logger.info(f"Requête liste_sellers par {request.user}")
        sellers = Seller.objects.all().order_by('-start')  # Remplace '-created_at' par '-start'
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(sellers, request)
        
        serializer = SellerSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Exception as e:
        logger.error(f"Erreur dans liste_sellers: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des vendeurs',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])  # Restreint aux admins
def verifier_seller(request, seller_id):
    """Endpoint PUT/PATCH /sellers/{seller_id}/verify/ - Vérifier un vendeur"""
    try:
        logger.info(f"Requête verifier_seller par {request.user} pour vendeur {seller_id}")
        seller = get_object_or_404(Seller, id=seller_id)
        seller.status = 'verified'
        seller.save()
        
        serializer = SellerSerializer(seller)
        logger.info(f"Vendeur vérifié: {seller.nom}")
        return Response({
            'message': f'Vendeur "{seller.nom}" vérifié avec succès',
            'seller': serializer.data
        })
    
    except Http404:
        return Response({
            'error': 'Vendeur non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur dans verifier_seller: {str(e)}")
        return Response({
            'error': 'Erreur lors de la vérification du vendeur',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAdminUser])  # Restreint aux admins
def liste_clients(request):
    """Endpoint GET /clients/ - Liste des clients"""
    try:
        logger.info(f"Requête liste_clients par {request.user}")
        clients = Client.objects.all().order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(clients, request)
        
        serializer = ClientSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Exception as e:
        logger.error(f"Erreur dans liste_clients: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des clients',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAdminUser])  # Restreint aux admins
def upload_image(request):
    """Endpoint POST /upload/image/ - Upload d'image"""
    try:
        logger.info(f"Requête upload_image par {request.user}")
        if 'image' not in request.FILES:
            logger.error("Aucune image fournie")
            return Response({
                'error': 'Aucune image fournie'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        image = request.FILES['image']
        extension = image.name.split('.')[-1]
        filename = f"{uuid.uuid4()}.{extension}"
        
        path = default_storage.save(f'images/{filename}', image)
        
        logger.info(f"Image uploadée: {path}")
        return Response({
            'message': 'Image uploadée avec succès',
            'path': path,
            'url': default_storage.url(path)
        })
    
    except Exception as e:
        logger.error(f"Erreur dans upload_image: {str(e)}")
        return Response({
            'error': "Erreur lors de l'upload de l'image",
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAdminUser])  # Restreint aux admins
def statistiques_dashboard(request):
    """Endpoint GET /stats/ - Statistiques générales"""
    try:
        logger.info(f"Requête statistiques_dashboard par {request.user}")
        stats = {
            'total_produits': Produit.objects.count(),
            'produits_verifies': Produit.objects.filter(status='verified').count(),
            'produits_non_verifies': Produit.objects.filter(status='unverified').count(),
            'total_sellers': Seller.objects.count(),
            'sellers_verifies': Seller.objects.filter(status='verified').count(),
            'sellers_non_verifies': Seller.objects.filter(status='unverified').count(),
            'total_clients': Client.objects.count(),
            'produits_par_categorie': {}
        }
        
        if hasattr(Produit, 'CATEGORIE_CHOICES'):
            for key, value in Produit.CATEGORIE_CHOICES:
                stats['produits_par_categorie'][key] = Produit.objects.filter(
                    categorie=key, status='verified'
                ).count()
        
        return Response(stats)
    
    except Exception as e:
        logger.error(f"Erreur dans statistiques_dashboard: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des statistiques',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAdminUser])  # Restreint aux admins
def statistiques_seller(request, seller_id):
    """Endpoint GET /stats/seller/{seller_id}/ - Statistiques d'un vendeur"""
    try:
        logger.info(f"Requête statistiques_seller par {request.user} pour vendeur {seller_id}")
        seller = get_object_or_404(Seller, id=seller_id)
        
        stats = {
            'seller': SellerSerializer(seller).data,
            'total_produits': seller.produits.count(),
            'produits_verifies': seller.produits.filter(status='verified').count(),
            'produits_non_verifies': seller.produits.filter(status='unverified').count(),
        }
        
        return Response(stats)
    
    except Http404:
        return Response({
            'error': 'Vendeur non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur dans statistiques_seller: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des statistiques du vendeur',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)