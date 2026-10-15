"""URL routes for the REST API (mounted under /api/)."""
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import api_views

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="api_token"),
    path("vendors/", api_views.VendorList.as_view(), name="api_vendor_list"),
    path("vendors/<int:vendor_pk>/stores/", api_views.VendorStoreList.as_view(), name="api_vendor_stores"),
    path("stores/", api_views.StoreListCreate.as_view(), name="api_store_list"),
    path("stores/<int:pk>/", api_views.StoreDetail.as_view(), name="api_store_detail"),
    path("stores/<int:store_pk>/products/", api_views.StoreProductListCreate.as_view(), name="api_store_products"),
    path("products/<int:pk>/", api_views.ProductDetail.as_view(), name="api_product_detail"),
    path("products/<int:product_pk>/reviews/", api_views.ProductReviewListCreate.as_view(), name="api_product_reviews"),
    path("reviews/", api_views.ReviewList.as_view(), name="api_review_list"),
    path("reviews/<int:pk>/", api_views.ReviewDetail.as_view(), name="api_review_detail"),
]
