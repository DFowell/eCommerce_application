"""Django admin configuration."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Order, OrderItem, Product, Review, Store, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin for users, showing the vendor/buyer role."""

    fieldsets = UserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff")


class OrderItemInline(admin.TabularInline):
    """Show invoice lines inside the order page."""

    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin for orders with their lines."""

    inlines = [OrderItemInline]


admin.site.register(Store)
admin.site.register(Product)
admin.site.register(Review)
