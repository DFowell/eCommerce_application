"""URL routes for the website (the REST API routes are in api_urls.py)."""
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # catalogue (public)
    path("", views.product_list, name="home"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/review/", views.review_create, name="review_create"),
    path("vendors/", views.vendor_list, name="vendor_list"),
    path("vendors/<int:pk>/", views.vendor_stores, name="vendor_stores"),
    path("stores/", views.all_stores, name="all_stores"),
    path("stores/<int:pk>/", views.store_products, name="store_products"),
    # third-party API
    path("reddit/", views.reddit_feed, name="reddit_feed"),
    # auth
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("password-reset/<str:token>/", views.password_reset_confirm, name="password_reset_confirm"),
    # vendor
    path("vendor/stores/", views.store_list, name="store_list"),
    path("vendor/stores/new/", views.store_create, name="store_create"),
    path("vendor/stores/<int:pk>/", views.store_detail, name="store_detail"),
    path("vendor/stores/<int:pk>/edit/", views.store_edit, name="store_edit"),
    path("vendor/stores/<int:pk>/delete/", views.store_delete, name="store_delete"),
    path("vendor/stores/<int:store_pk>/products/new/", views.product_create, name="product_create"),
    path("vendor/products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("vendor/products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("vendor/reviews/", views.vendor_reviews, name="vendor_reviews"),
    # buyer
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
]
