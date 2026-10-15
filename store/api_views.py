"""REST API views (Django REST Framework)."""
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied

from .models import OrderItem, Product, Review, Store, User
from .permissions import IsBuyerOrReadOnly, IsOwnerOrReadOnly, IsVendorOrReadOnly
from .serializers import (
    ProductSerializer,
    ReviewSerializer,
    StoreSerializer,
    VendorSerializer,
)


class VendorList(generics.ListAPIView):
    """GET /api/vendors/ - list all vendors."""

    serializer_class = VendorSerializer
    queryset = User.objects.filter(role=User.VENDOR)


class VendorStoreList(generics.ListAPIView):
    """GET /api/vendors/<id>/stores/ - the stores listed under one vendor."""

    serializer_class = StoreSerializer

    def get_queryset(self):
        """Return the stores of the vendor in the URL (404 if no such vendor)."""
        vendor = get_object_or_404(User, pk=self.kwargs["vendor_pk"], role=User.VENDOR)
        return Store.objects.filter(vendor=vendor).select_related("vendor").prefetch_related("products")


class StoreListCreate(generics.ListCreateAPIView):
    """GET /api/stores/ - list all stores. POST - create a store (vendors only)."""

    serializer_class = StoreSerializer
    permission_classes = [IsVendorOrReadOnly]
    queryset = Store.objects.select_related("vendor").prefetch_related("products")

    def perform_create(self, serializer):
        """Save the new store with the logged-in vendor as its owner."""
        serializer.save(vendor=self.request.user)


class StoreDetail(generics.RetrieveUpdateDestroyAPIView):
    """GET, PUT, PATCH or DELETE /api/stores/<id>/ (writes: owning vendor only)."""

    serializer_class = StoreSerializer
    permission_classes = [IsVendorOrReadOnly, IsOwnerOrReadOnly]
    queryset = Store.objects.select_related("vendor").prefetch_related("products")


class StoreProductListCreate(generics.ListCreateAPIView):
    """GET /api/stores/<id>/products/ - list products. POST - add one (owning vendor only)."""

    serializer_class = ProductSerializer
    permission_classes = [IsVendorOrReadOnly]

    def get_store(self):
        """Return the store named in the URL, or raise 404."""
        return get_object_or_404(Store, pk=self.kwargs["store_pk"])

    def get_queryset(self):
        """Return the products of the store in the URL."""
        return Product.objects.filter(store=self.get_store())

    def perform_create(self, serializer):
        """Save the new product, but only if the caller owns the store."""
        store = self.get_store()
        if store.vendor != self.request.user:
            raise PermissionDenied("You can only add products to your own stores.")
        serializer.save(store=store)


class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    """GET, PUT, PATCH or DELETE /api/products/<id>/ (writes: owning vendor only)."""

    serializer_class = ProductSerializer
    permission_classes = [IsVendorOrReadOnly, IsOwnerOrReadOnly]
    queryset = Product.objects.select_related("store__vendor")


class ProductReviewListCreate(generics.ListCreateAPIView):
    """GET /api/products/<id>/reviews/ - list reviews. POST - add one (buyers only).

    A buyer may post any number of reviews for the same product.
    """

    serializer_class = ReviewSerializer
    permission_classes = [IsBuyerOrReadOnly]

    def get_product(self):
        """Return the product named in the URL, or raise 404."""
        return get_object_or_404(Product, pk=self.kwargs["product_pk"])

    def get_queryset(self):
        """Return the reviews of the product in the URL."""
        return Review.objects.filter(product=self.get_product()).select_related("buyer", "product__store")

    def perform_create(self, serializer):
        """Save the review; it is verified if the buyer has bought the product."""
        product = self.get_product()
        verified = OrderItem.objects.filter(order__buyer=self.request.user, product=product).exists()
        serializer.save(product=product, buyer=self.request.user, verified=verified)


class ReviewList(generics.ListAPIView):
    """GET /api/reviews/ - reviews across all products, so nobody clicks product by product.

    Vendors see the reviews of every product in their stores; buyers see the
    reviews they wrote. Optional filters: ``?store=<id>`` and ``?product=<id>``.
    """

    serializer_class = ReviewSerializer

    def get_queryset(self):
        """Return the caller's reviews, narrowed by the optional filters."""
        user = self.request.user
        reviews = Review.objects.select_related("buyer", "product__store")
        if user.is_vendor:
            reviews = reviews.filter(product__store__vendor=user)
        else:
            reviews = reviews.filter(buyer=user)
        store = self.request.query_params.get("store", "")
        product = self.request.query_params.get("product", "")
        if store.isdigit():
            reviews = reviews.filter(product__store_id=int(store))
        if product.isdigit():
            reviews = reviews.filter(product_id=int(product))
        return reviews


class ReviewDetail(generics.RetrieveUpdateDestroyAPIView):
    """GET, PUT, PATCH or DELETE /api/reviews/<id>/ (writes: the buyer who wrote it)."""

    serializer_class = ReviewSerializer
    permission_classes = [IsBuyerOrReadOnly, IsOwnerOrReadOnly]
    queryset = Review.objects.select_related("buyer", "product__store")
