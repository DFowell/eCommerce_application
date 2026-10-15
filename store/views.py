"""Website views: browsing, vendor management, cart/checkout, reviews, password reset, Reddit."""
import logging
from decimal import Decimal
from functools import wraps

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from functions.reddit import get_subreddit_posts

from .forms import (
    CartAddForm,
    PasswordResetRequestForm,
    ProductForm,
    RegistrationForm,
    ReviewForm,
    StoreForm,
)
from .models import (
    Order,
    OrderItem,
    PasswordResetToken,
    Product,
    Review,
    Store,
    User,
)

logger = logging.getLogger(__name__)

REDDIT_SUBREDDIT = "django"


# ---------------------------------------------------------------- permissions
def role_required(role):
    """Build a decorator that requires a logged-in user with the given role.

    Anonymous users are redirected to the login page; logged-in users with a
    different role receive a 403 Forbidden response.

    Args:
        role: ``User.VENDOR`` or ``User.BUYER``.

    Returns:
        A view decorator.
    """

    def decorator(view):
        """Wrap ``view`` with the login and role checks."""

        @wraps(view)
        def wrapped(request, *args, **kwargs):
            """Raise PermissionDenied unless the user has the required role."""
            if request.user.role != role:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return login_required(wrapped)

    return decorator


vendor_required = role_required(User.VENDOR)
buyer_required = role_required(User.BUYER)


# ------------------------------------------------------------ authentication
def register(request):
    """Register a new vendor or buyer and log them in."""
    if request.user.is_authenticated:
        return redirect("home")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.username}! Your {user.role} account is ready.")
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})


# ------------------------------------------- public browsing (buyers and visitors)
def product_list(request):
    """List every product from every store, with optional text search (?q=)."""
    products = Product.objects.select_related("store")
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(store__name__icontains=query)
        )
    return render(request, "store/product_list.html", {"products": products, "query": query})


def product_detail(request, pk):
    """Show one product with its reviews, plus add-to-cart and review forms for buyers."""
    product = get_object_or_404(Product.objects.select_related("store__vendor"), pk=pk)
    context = {
        "product": product,
        "reviews": product.reviews.select_related("buyer"),
        "cart_form": CartAddForm(),
    }
    if request.user.is_authenticated and request.user.is_buyer:
        context["review_form"] = ReviewForm()
    return render(request, "store/product_detail.html", context)


def vendor_list(request):
    """Entry point 'Vendors': list all vendors; each links to that vendor's stores."""
    vendors = (
        User.objects.filter(role=User.VENDOR)
        .annotate(store_count=Count("stores"))
        .order_by("username")
    )
    return render(request, "store/vendor_list.html", {"vendors": vendors})


def vendor_stores(request, pk):
    """List the stores of one vendor; each store links to its products."""
    vendor = get_object_or_404(User, pk=pk, role=User.VENDOR)
    stores = vendor.stores.annotate(product_count=Count("products"))
    return render(request, "store/vendor_stores.html", {"vendor": vendor, "stores": stores})


def all_stores(request):
    """Entry point 'Stores': list every store regardless of vendor."""
    stores = Store.objects.select_related("vendor").annotate(product_count=Count("products"))
    return render(request, "store/all_stores.html", {"stores": stores})


def store_products(request, pk):
    """List the products of one store (the buyer can open and purchase them)."""
    store = get_object_or_404(Store.objects.select_related("vendor"), pk=pk)
    return render(request, "store/store_products.html", {"store": store, "products": store.products.all()})


# ------------------------------------------------------------- vendor: stores
@vendor_required
def store_list(request):
    """Entry point 'My stores': list the logged-in vendor's own stores."""
    return render(request, "store/store_list.html", {"stores": request.user.stores.all()})


@vendor_required
def store_create(request):
    """Create a store owned by the logged-in vendor."""
    form = StoreForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        store = form.save(commit=False)
        store.vendor = request.user
        store.save()
        messages.success(request, "Store created.")
        return redirect("store_detail", pk=store.pk)
    return render(request, "store/form.html", {"form": form, "title": "New store"})


@vendor_required
def store_detail(request, pk):
    """Show one of the vendor's own stores and its products (404 for other vendors' stores)."""
    store = get_object_or_404(Store, pk=pk, vendor=request.user)
    return render(request, "store/store_detail.html", {"store": store, "products": store.products.all()})


@vendor_required
def store_edit(request, pk):
    """Edit one of the vendor's own stores."""
    store = get_object_or_404(Store, pk=pk, vendor=request.user)
    form = StoreForm(request.POST or None, instance=store)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Store updated.")
        return redirect("store_detail", pk=store.pk)
    return render(request, "store/form.html", {"form": form, "title": f"Edit {store.name}"})


@vendor_required
def store_delete(request, pk):
    """Ask for confirmation, then delete one of the vendor's own stores."""
    store = get_object_or_404(Store, pk=pk, vendor=request.user)
    if request.method == "POST":
        store.delete()
        messages.success(request, "Store deleted.")
        return redirect("store_list")
    return render(
        request,
        "store/confirm_delete.html",
        {"object": store, "kind": "store", "cancel_url": reverse("store_detail", args=[store.pk])},
    )


# ----------------------------------------------------------- vendor: products
@vendor_required
def product_create(request, store_pk):
    """Add a product to one of the vendor's own stores."""
    store = get_object_or_404(Store, pk=store_pk, vendor=request.user)
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        product = form.save(commit=False)
        product.store = store
        product.save()
        messages.success(request, "Product added.")
        return redirect("store_detail", pk=store.pk)
    return render(request, "store/form.html", {"form": form, "title": f"Add product to {store.name}"})


@vendor_required
def product_edit(request, pk):
    """Edit a product in one of the vendor's own stores."""
    product = get_object_or_404(Product, pk=pk, store__vendor=request.user)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product updated.")
        return redirect("store_detail", pk=product.store_id)
    return render(request, "store/form.html", {"form": form, "title": f"Edit {product.name}"})


@vendor_required
def product_delete(request, pk):
    """Ask for confirmation, then remove a product from the vendor's own store."""
    product = get_object_or_404(Product, pk=pk, store__vendor=request.user)
    if request.method == "POST":
        store_id = product.store_id
        product.delete()
        messages.success(request, "Product removed.")
        return redirect("store_detail", pk=store_id)
    return render(
        request,
        "store/confirm_delete.html",
        {"object": product, "kind": "product", "cancel_url": reverse("store_detail", args=[product.store_id])},
    )


# ------------------------------------------------------------ vendor: reviews
@vendor_required
def vendor_reviews(request):
    """Entry point 'Reviews': every review on the vendor's products in one list.

    Each row shows the store and product the review belongs to, so the vendor
    does not have to open products one by one. The list can be narrowed with
    ``?store=<id>`` and ``?product=<id>`` (used by the filter form).
    """
    reviews = Review.objects.filter(product__store__vendor=request.user).select_related(
        "product__store", "buyer"
    )
    selected_store = request.GET.get("store", "")
    selected_product = request.GET.get("product", "")
    if selected_store.isdigit():
        reviews = reviews.filter(product__store_id=int(selected_store))
    else:
        selected_store = ""
    if selected_product.isdigit():
        reviews = reviews.filter(product_id=int(selected_product))
    else:
        selected_product = ""
    context = {
        "reviews": reviews,
        "stores": request.user.stores.all(),
        "products": Product.objects.filter(store__vendor=request.user).select_related("store"),
        "selected_store": selected_store,
        "selected_product": selected_product,
    }
    return render(request, "store/vendor_reviews.html", context)


# ------------------------------------------------------------------ buyer: cart
def _cart(request):
    """Return the cart dict stored in the session ({product_id (str): quantity})."""
    return request.session.setdefault("cart", {})


def _cart_lines(request):
    """Build the cart display data.

    Products that no longer exist are removed from the cart and the buyer is warned.

    Returns:
        A tuple ``(lines, total)`` where ``lines`` is a list of dicts with
        ``product``, ``quantity`` and ``line_total``.
    """
    cart = _cart(request)
    products = Product.objects.select_related("store").in_bulk([int(pk) for pk in cart])
    lines, total, dropped = [], Decimal("0.00"), False
    for pk_str, qty in list(cart.items()):
        product = products.get(int(pk_str))
        if product is None:
            del cart[pk_str]
            dropped = True
            continue
        line_total = product.price * qty
        total += line_total
        lines.append({"product": product, "quantity": qty, "line_total": line_total})
    if dropped:
        request.session.modified = True
        messages.warning(request, "Some items in your cart are no longer available and were removed.")
    return lines, total


@buyer_required
@require_POST
def cart_add(request, pk):
    """Add a product to the session cart, refusing quantities above the stock."""
    product = get_object_or_404(Product, pk=pk)
    form = CartAddForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please enter a valid quantity.")
        return redirect("product_detail", pk=pk)
    cart = _cart(request)
    new_qty = cart.get(str(pk), 0) + form.cleaned_data["quantity"]
    if new_qty > product.stock:
        messages.error(request, f"Only {product.stock} of {product.name} in stock.")
        return redirect("product_detail", pk=pk)
    cart[str(pk)] = new_qty
    request.session.modified = True
    messages.success(request, f"Added {product.name} to your cart.")
    return redirect("cart")


@buyer_required
@require_POST
def cart_remove(request, pk):
    """Remove a product from the session cart."""
    cart = _cart(request)
    if cart.pop(str(pk), None) is not None:
        request.session.modified = True
        messages.success(request, "Item removed from cart.")
    return redirect("cart")


@buyer_required
def cart_view(request):
    """Show the buyer's cart and its total."""
    lines, total = _cart_lines(request)
    return render(request, "store/cart.html", {"lines": lines, "total": total})


def _invoice_text(order):
    """Return the plain-text invoice for an order (used as the email body)."""
    rows = [f"Invoice for order #{order.pk}", f"Date: {order.created_at:%d %b %Y %H:%M}", ""]
    for item in order.items.all():
        rows.append(f"{item.quantity} x {item.product_name} @ £{item.unit_price} = £{item.line_total}")
    rows += ["", f"TOTAL: £{order.total}", "", "Thank you for your order!"]
    return "\n".join(rows)


@buyer_required
@require_POST
def checkout(request):
    """Turn the cart into an order, reduce stock, empty the cart and email the invoice.

    Everything database-related runs in one transaction with the products
    locked, so a failure (for example not enough stock) leaves no partial
    order. If only the email fails, the order stays and the buyer is told.
    """
    cart = _cart(request)
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect("cart")

    try:
        with transaction.atomic():
            products = Product.objects.select_for_update().in_bulk([int(pk) for pk in cart])
            order = Order.objects.create(buyer=request.user)
            for pk_str, qty in cart.items():
                product = products.get(int(pk_str))
                if product is None:
                    raise ValueError("One of the products in your cart is no longer available.")
                if qty > product.stock:
                    raise ValueError(f"Not enough stock for {product.name} (only {product.stock} left).")
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=qty,
                )
                product.stock -= qty
                product.save(update_fields=["stock"])
    except ValueError as exc:
        # Transaction rolled back: no partial order, stock and cart untouched.
        messages.error(request, str(exc))
        return redirect("cart")

    request.session["cart"] = {}
    request.session.modified = True

    try:
        send_mail(
            subject=f"Your invoice for order #{order.pk}",
            message=_invoice_text(order),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
        )
        messages.success(request, "Thank you! Your invoice has been emailed to you.")
    except Exception:
        logger.exception("Invoice email failed for order %s", order.pk)
        messages.warning(
            request, "Your order was placed, but we could not email the invoice. You can view it below."
        )
    return redirect("order_detail", pk=order.pk)


@buyer_required
def order_list(request):
    """List the logged-in buyer's past orders."""
    return render(request, "store/order_list.html", {"orders": request.user.orders.all()})


@buyer_required
def order_detail(request, pk):
    """Show one invoice (404 if the order belongs to another buyer)."""
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    return render(request, "store/order_detail.html", {"order": order})


# ----------------------------------------------------------------- buyer: reviews
@buyer_required
@require_POST
def review_create(request, pk):
    """Add a NEW review to a product.

    Buyers can review the same product many times; earlier reviews are never
    overwritten because each one records how the buyer felt at that moment. The
    review is marked verified if the buyer has already purchased the product.
    """
    product = get_object_or_404(Product, pk=pk)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.buyer = request.user
        review.verified = OrderItem.objects.filter(
            order__buyer=request.user, product=product
        ).exists()
        review.save()
        messages.success(
            request, "Verified review added." if review.verified else "Review added (unverified)."
        )
    else:
        messages.error(request, "Please give a rating from 1 to 5.")
    return redirect("product_detail", pk=pk)


# --------------------------------------------------------------- password reset
def password_reset_request(request):
    """Email a one-time, expiring reset link (same response whether or not the email exists)."""
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.filter(email__iexact=form.cleaned_data["email"]).first()
        if user:
            raw = PasswordResetToken.issue(user)
            link = request.build_absolute_uri(reverse("password_reset_confirm", args=[raw]))
            try:
                send_mail(
                    subject="Reset your password",
                    message=(
                        f"Hi {user.username},\n\nUse this link to choose a new password:\n{link}\n\n"
                        f"It expires in {settings.PASSWORD_RESET_TOKEN_HOURS} hour(s) and can be used once.\n"
                        "If you didn't ask for this, ignore this email."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                )
            except Exception:
                logger.exception("Password reset email failed for user %s", user.pk)
        messages.info(request, "If that email is registered, a reset link has been sent.")
        return redirect("login")
    return render(request, "registration/password_reset_request.html", {"form": form})


def password_reset_confirm(request, token):
    """Let the user choose a new password if the token is valid, unused and unexpired."""
    token_obj = PasswordResetToken.lookup(token)
    if token_obj is None:
        return render(request, "registration/password_reset_invalid.html", status=400)
    form = SetPasswordForm(token_obj.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        token_obj.used = True
        token_obj.save(update_fields=["used"])
        messages.success(request, "Password changed. You can now log in.")
        return redirect("login")
    return render(request, "registration/password_reset_confirm.html", {"form": form})


# ------------------------------------------------------------ third-party API
def reddit_feed(request):
    """Show the latest posts from a subreddit fetched from Reddit's public JSON API."""
    posts = []
    try:
        posts = get_subreddit_posts(REDDIT_SUBREDDIT)
    except (requests.RequestException, ValueError):
        logger.exception("Could not fetch Reddit posts")
        messages.error(request, "Sorry, we couldn't load the Reddit feed right now. Please try again later.")
    return render(request, "store/reddit_feed.html", {"posts": posts, "subreddit": REDDIT_SUBREDDIT})
