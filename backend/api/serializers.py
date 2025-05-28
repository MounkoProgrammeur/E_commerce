from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Produit, Seller, Client, User

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_seller', 'is_client', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

class SellerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    total_produits = serializers.ReadOnlyField()
    
    class Meta:
        model = Seller
        fields = ['id', 'user', 'nom', 'numero', 'status', 'start', 'avis', 'localisation', 'total_produits']

class SellerCreateSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Seller
        fields = ['user', 'nom', 'numero', 'localisation', 'avis']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['is_seller'] = True
        user_data['is_client'] = False
        user_serializer = UserSerializer(data=user_data)
        if user_serializer.is_valid():
            user = user_serializer.save()
            seller = Seller.objects.create(user=user, **validated_data)
            return seller
        else:
            raise serializers.ValidationError(user_serializer.errors)

class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Client
        fields = ['id', 'user', 'relation']

class ClientCreateSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Client
        fields = ['user', 'relation']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['is_client'] = True
        user_data['is_seller'] = False
        user_serializer = UserSerializer(data=user_data)
        if user_serializer.is_valid():
            user = user_serializer.save()
            client = Client.objects.create(user=user, **validated_data)
            return client
        else:
            raise serializers.ValidationError(user_serializer.errors)

class ProduitSerializer(serializers.ModelSerializer):
    seller_info = serializers.SerializerMethodField()
    prix_avec_reduction = serializers.ReadOnlyField()
    image_url = serializers.ImageField(required=False)
    
    class Meta:
        model = Produit
        fields = ['id', 'nom', 'status', 'prix', 'couleur', 'categorie', 
                 'tags', 'description', 'seller', 'ancien_prix', 'likes', 
                 'reduction', 'image_url', 'taille', 'quantite', 'created_at', 
                 'updated_at', 'seller_info', 'prix_avec_reduction']
    
    def get_seller_info(self, obj):
        return {
            'id': obj.seller.id,
            'nom': obj.seller.nom,
            'localisation': obj.seller.localisation,
            'status': obj.seller.status,
            'numero': obj.seller.numero
        }

class ProduitCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produit
        fields = ['nom', 'prix', 'couleur', 'categorie', 'tags', 'description', 
                 'seller', 'ancien_prix', 'reduction', 'image_url', 'taille', 'quantite']
    
    def validate_seller(self, value):
        """Valider que le seller existe et est valide"""
        if not Seller.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Le vendeur spécifié n'existe pas.")
        return value
    
    def validate(self, data):
        """Valider que couleur et taille sont des listes"""
        if not isinstance(data.get('couleur', []), list):
            raise serializers.ValidationError({'couleur': 'Le champ couleur doit être une liste.'})
        if not isinstance(data.get('taille', []), list):
            raise serializers.ValidationError({'taille': 'Le champ taille doit être une liste.'})
        return data