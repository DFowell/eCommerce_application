"""Serializers that turn models into JSON (and validate incoming JSON)."""
from rest_framework import serializers

from .models import Product, Review, Store, User


class ProductSerializer(serializers.ModelSerializer):
    """JSON representation of a product. The store is set by the server."""

    class Meta:
        """Model and fields for the product serializer."""

        model = Product
        fields = ("id", "store", "name", "description", "price", "stock")
        read_only_fields = ("id", "store")


class StoreSerializer(serializers.ModelSerializer):
    """JSON representation of a store, including its products (read only)."""

    vendor_name = serializers.CharField(source="vendor.username", read_only=True)
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        """Model and fields for the store serializer."""

        model = Store
        fields = ("id", "vendor", "vendor_name", "name", "description", "created_at", "products")
        read_only_fields = ("id", "vendor", "created_at")


class ReviewSerializer(serializers.ModelSerializer):
    """JSON representation of a review.

    Clients may only send ``rating`` and ``comment``. The product, buyer and
    verified flag are filled in by the server.
    """

    buyer_name = serializers.CharField(source="buyer.username", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    store_name = serializers.CharField(source="product.store.name", read_only=True)

    class Meta:
        """Model and fields for the review serializer."""

        model = Review
        fields = (
            "id", "product", "product_name", "store_name", "buyer_name",
            "rating", "comment", "verified", "created_at",
        )
        read_only_fields = (
            "id", "product", "product_name", "store_name", "buyer_name", "verified", "created_at",
        )


class VendorSerializer(serializers.ModelSerializer):
    """Minimal public representation of a vendor."""

    class Meta:
        """Model and fields for the vendor serializer."""

        model = User
        fields = ("id", "username")
