"""Custom permission classes for the REST API."""
from rest_framework import permissions

from .models import Review, Store


class IsVendorOrReadOnly(permissions.BasePermission):
    """Any authenticated user may read; only vendors may write."""

    def has_permission(self, request, view):
        """Allow logged-in users to read, and logged-in vendors to write."""
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in permissions.SAFE_METHODS or user.is_vendor


class IsBuyerOrReadOnly(permissions.BasePermission):
    """Any authenticated user may read; only buyers may write."""

    def has_permission(self, request, view):
        """Allow logged-in users to read, and logged-in buyers to write."""
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in permissions.SAFE_METHODS or user.is_buyer


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Writes are only allowed to the owner of the object.

    The owner of a store or product is its vendor; the owner of a review is
    the buyer who wrote it.
    """

    def has_object_permission(self, request, view, obj):
        """Allow safe methods for everyone, and writes only to the owner."""
        if request.method in permissions.SAFE_METHODS:
            return True
        if isinstance(obj, Store):
            owner = obj.vendor
        elif isinstance(obj, Review):
            owner = obj.buyer
        else:  # Product
            owner = obj.store.vendor
        return owner == request.user
