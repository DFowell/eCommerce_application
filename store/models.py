"""Database models for the eCommerce application."""
import hashlib
import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """A site user who is either a vendor (sells) or a buyer (shops)."""

    VENDOR = "vendor"
    BUYER = "buyer"
    ROLE_CHOICES = [(VENDOR, "Vendor"), (BUYER, "Buyer")]

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=BUYER)

    @property
    def is_vendor(self):
        """Return True if this user registered as a vendor."""
        return self.role == self.VENDOR

    @property
    def is_buyer(self):
        """Return True if this user registered as a buyer."""
        return self.role == self.BUYER


class Store(models.Model):
    """A store owned by one vendor. A vendor may own many stores."""

    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stores"
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Order stores alphabetically."""

        ordering = ["name"]

    def __str__(self):
        """Return the store name."""
        return self.name


class Product(models.Model):
    """A product sold in exactly one store."""

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Order products alphabetically."""

        ordering = ["name"]

    def __str__(self):
        """Return the product name."""
        return self.name


class Order(models.Model):
    """A completed checkout by a buyer; its lines are OrderItem rows (the invoice)."""

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Show the newest orders first."""

        ordering = ["-created_at"]

    @property
    def total(self):
        """Return the order total as a Decimal (sum of all line totals)."""
        return sum((item.line_total for item in self.items.all()), Decimal("0.00"))

    def __str__(self):
        """Return a short label such as 'Order #3'."""
        return f"Order #{self.pk}"


class OrderItem(models.Model):
    """One invoice line. Name and price are copied so history survives later edits."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items"
    )
    product_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    @property
    def line_total(self):
        """Return unit price multiplied by quantity."""
        return self.unit_price * self.quantity

    def __str__(self):
        """Return a label such as '2 x Widget'."""
        return f"{self.quantity} x {self.product_name}"


class Review(models.Model):
    """A buyer's opinion of a product at one point in time.

    A buyer may leave several reviews of the same product: each review is a
    snapshot of how the buyer saw the product when it was written, so later
    reviews do not overwrite earlier ones. ``verified`` is True when the buyer
    had already purchased the product at the time of writing.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Show the newest reviews first."""

        ordering = ["-created_at"]

    def __str__(self):
        """Return a label such as 'Widget: 4/5 by buyer1'."""
        return f"{self.product}: {self.rating}/5 by {self.buyer}"


class PasswordResetToken(models.Model):
    """Single-use, expiring password-reset token. Only a hash of it is stored."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reset_tokens"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    @staticmethod
    def _hash(raw):
        """Return the SHA-256 hex digest of a raw token string."""
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def issue(cls, user):
        """Invalidate the user's older tokens, create a new one and return the raw token.

        Args:
            user: The User asking for a password reset.

        Returns:
            The raw token string to put in the emailed link (never stored).
        """
        cls.objects.filter(user=user, used=False).update(used=True)
        raw = secrets.token_urlsafe(32)
        cls.objects.create(user=user, token_hash=cls._hash(raw))
        return raw

    @classmethod
    def lookup(cls, raw):
        """Find the valid (unused, unexpired) token matching a raw token string.

        Args:
            raw: The token taken from the reset link.

        Returns:
            The PasswordResetToken, or None if it is unknown, used or expired.
        """
        try:
            token = cls.objects.select_related("user").get(
                token_hash=cls._hash(raw), used=False
            )
        except cls.DoesNotExist:
            return None
        return None if token.is_expired else token

    @property
    def is_expired(self):
        """Return True once the token is older than PASSWORD_RESET_TOKEN_HOURS."""
        lifetime = timedelta(hours=settings.PASSWORD_RESET_TOKEN_HOURS)
        return timezone.now() > self.created_at + lifetime

    def __str__(self):
        """Return a label that does not reveal the token."""
        return f"Reset token for {self.user}"
