"""Tests for the website (registration, permissions, browsing, cart, reviews, password reset)."""
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Order, PasswordResetToken, Product, Review, Store, User

PW = "S3cure-pass-phrase!"


def make_user(username, role):
    """Create and return a user with the given role and a known password."""
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password=PW, role=role
    )


class BaseCase(TestCase):
    """Shared fixtures: two vendors, one buyer, one store and one product."""

    def setUp(self):
        """Create the shared users, store and product."""
        self.vendor = make_user("vendor1", User.VENDOR)
        self.vendor2 = make_user("vendor2", User.VENDOR)
        self.buyer = make_user("buyer1", User.BUYER)
        self.store = Store.objects.create(vendor=self.vendor, name="Shop One")
        self.product = Product.objects.create(
            store=self.store, name="Widget", price=Decimal("9.99"), stock=5
        )


class RegistrationTests(TestCase):
    """Users can register as vendors or buyers."""

    def test_register_as_vendor_and_buyer(self):
        """Both roles can sign up and the role is saved."""
        for role in (User.VENDOR, User.BUYER):
            resp = self.client.post(
                reverse("register"),
                {"username": f"new_{role}", "email": f"{role}@x.com", "role": role,
                 "password1": PW, "password2": PW},
            )
            self.assertRedirects(resp, reverse("home"))
            self.assertEqual(User.objects.get(username=f"new_{role}").role, role)
            self.client.logout()


class PermissionTests(BaseCase):
    """Login status and role decide which pages can be opened."""

    def test_anonymous_redirected_to_login(self):
        """Anonymous users are sent to the login page."""
        resp = self.client.get(reverse("store_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_buyer_cannot_use_vendor_pages(self):
        """Buyers get 403 on vendor pages, including the vendor Reviews page."""
        self.client.login(username="buyer1", password=PW)
        self.assertEqual(self.client.get(reverse("store_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("vendor_reviews")).status_code, 403)

    def test_vendor_cannot_use_buyer_pages(self):
        """Vendors get 403 on buyer pages."""
        self.client.login(username="vendor1", password=PW)
        self.assertEqual(self.client.get(reverse("cart")).status_code, 403)

    def test_vendor_cannot_touch_other_vendors_store_or_product(self):
        """Another vendor's store and product return 404 and are left unchanged."""
        self.client.login(username="vendor2", password=PW)
        self.assertEqual(self.client.get(reverse("store_edit", args=[self.store.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("product_delete", args=[self.product.pk])).status_code, 404)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())


class MenuTests(BaseCase):
    """The navigation menu order and entries for each kind of user."""

    def test_vendor_menu_order(self):
        """Vendors see: My stores, Shop, Reviews, then Reddit."""
        self.client.login(username="vendor1", password=PW)
        html = self.client.get(reverse("store_list")).content.decode()
        positions = [html.index(label) for label in
                     ("My stores</a>", "Shop</a>", "Reviews</a>", "Reddit</a>")]
        self.assertEqual(positions, sorted(positions))

    def test_buyer_menu_has_vendors_and_stores(self):
        """Buyers see Products, Vendors, Stores and Reddit entry points."""
        self.client.login(username="buyer1", password=PW)
        html = self.client.get(reverse("home")).content.decode()
        for label in ("Products</a>", "Vendors</a>", "Stores</a>", "Reddit</a>"):
            self.assertIn(label, html)


class BrowsingTests(BaseCase):
    """Buyers can drill down Vendors -> Stores -> Products, or start from Stores."""

    def test_vendor_to_store_to_product_path(self):
        """Vendors list -> a vendor's stores -> a store's products."""
        self.client.login(username="buyer1", password=PW)
        resp = self.client.get(reverse("vendor_list"))
        self.assertContains(resp, "vendor1")
        self.assertContains(resp, reverse("vendor_stores", args=[self.vendor.pk]))
        resp = self.client.get(reverse("vendor_stores", args=[self.vendor.pk]))
        self.assertContains(resp, "Shop One")
        self.assertContains(resp, reverse("store_products", args=[self.store.pk]))
        resp = self.client.get(reverse("store_products", args=[self.store.pk]))
        self.assertContains(resp, "Widget")
        self.assertContains(resp, reverse("product_detail", args=[self.product.pk]))

    def test_stores_entry_point_lists_all_stores(self):
        """The Stores page lists stores from every vendor."""
        Store.objects.create(vendor=self.vendor2, name="Other Shop")
        resp = self.client.get(reverse("all_stores"))
        self.assertContains(resp, "Shop One")
        self.assertContains(resp, "Other Shop")

    def test_unknown_vendor_404(self):
        """A buyer id is not a vendor, so its stores page is 404."""
        self.assertEqual(self.client.get(reverse("vendor_stores", args=[self.buyer.pk])).status_code, 404)


class VendorCrudTests(BaseCase):
    """Vendors can create, read, update and delete their stores and products."""

    def setUp(self):
        """Log in as the first vendor."""
        super().setUp()
        self.client.login(username="vendor1", password=PW)

    def test_store_and_product_crud(self):
        """Walk through create, update and delete for a store and a product."""
        self.client.post(reverse("store_create"), {"name": "Second", "description": "d"})
        store = Store.objects.get(name="Second")
        self.client.post(reverse("product_create", args=[store.pk]),
                         {"name": "Gizmo", "description": "", "price": "3.50", "stock": 2})
        product = Product.objects.get(name="Gizmo")
        self.client.post(reverse("product_edit", args=[product.pk]),
                         {"name": "Gizmo 2", "description": "", "price": "4.00", "stock": 7})
        product.refresh_from_db()
        self.assertEqual((product.name, product.stock), ("Gizmo 2", 7))
        self.client.post(reverse("product_delete", args=[product.pk]))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.client.post(reverse("store_delete", args=[store.pk]))
        self.assertFalse(Store.objects.filter(pk=store.pk).exists())


class CartAndCheckoutTests(BaseCase):
    """The session cart and the checkout process."""

    def setUp(self):
        """Log in as the buyer."""
        super().setUp()
        self.client.login(username="buyer1", password=PW)

    def test_cart_persists_in_session(self):
        """Items added to the cart are shown on the cart page."""
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 2})
        resp = self.client.get(reverse("cart"))
        self.assertContains(resp, "Widget")
        self.assertContains(resp, "19.98")

    def test_cannot_add_more_than_stock(self):
        """Quantities above the stock are refused."""
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 6})
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_checkout_creates_order_clears_cart_sends_invoice(self):
        """Checkout creates the order, reduces stock, empties the cart and emails the invoice."""
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 2})
        resp = self.client.post(reverse("checkout"))
        order = Order.objects.get(buyer=self.buyer)
        self.assertRedirects(resp, reverse("order_detail", args=[order.pk]))
        self.assertEqual(order.total, Decimal("19.98"))
        self.assertEqual(self.client.session["cart"], {})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["buyer1@example.com"])
        self.assertIn("Widget", mail.outbox[0].body)

    def test_checkout_fails_cleanly_when_stock_dropped(self):
        """If stock drops before checkout nothing is created and the cart is kept."""
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 4})
        Product.objects.filter(pk=self.product.pk).update(stock=1)
        self.client.post(reverse("checkout"))
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.client.session["cart"], {str(self.product.pk): 4})
        self.assertEqual(len(mail.outbox), 0)

    def test_other_buyer_cannot_view_order(self):
        """A buyer cannot open another buyer's invoice."""
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 1})
        self.client.post(reverse("checkout"))
        order = Order.objects.get()
        make_user("buyer2", User.BUYER)
        self.client.login(username="buyer2", password=PW)
        self.assertEqual(self.client.get(reverse("order_detail", args=[order.pk])).status_code, 404)


class ReviewTests(BaseCase):
    """Buyers can add several reviews per product; purchases make them verified."""

    def review(self, rating, comment=""):
        """Post a review for the shared product as the logged-in buyer."""
        return self.client.post(
            reverse("review_create", args=[self.product.pk]), {"rating": rating, "comment": comment}
        )

    def test_unverified_then_verified(self):
        """A review before buying is unverified; one after buying is verified."""
        self.client.login(username="buyer1", password=PW)
        self.review(4, "ok")
        self.assertFalse(Review.objects.get().verified)
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 1})
        self.client.post(reverse("checkout"))
        self.review(5, "great")
        self.assertEqual(Review.objects.filter(verified=True).count(), 1)

    def test_multiple_reviews_are_kept(self):
        """Posting again adds a new review instead of overwriting the old one."""
        self.client.login(username="buyer1", password=PW)
        self.review(2, "first impression")
        self.review(5, "grew on me")
        reviews = Review.objects.order_by("created_at", "pk")
        self.assertEqual([r.rating for r in reviews], [2, 5])
        self.assertEqual([r.comment for r in reviews], ["first impression", "grew on me"])

    def test_invalid_rating_rejected(self):
        """A rating outside 1-5 creates nothing."""
        self.client.login(username="buyer1", password=PW)
        self.review(9)
        self.assertEqual(Review.objects.count(), 0)


class VendorReviewsPageTests(BaseCase):
    """The vendor 'Reviews' page lists reviews across all of the vendor's products."""

    def setUp(self):
        """Create two vendors' stores and products, each with a review."""
        super().setUp()
        self.store_b = Store.objects.create(vendor=self.vendor, name="Shop Two")
        self.product_b = Product.objects.create(
            store=self.store_b, name="Gadget", price=Decimal("5.00"), stock=3
        )
        other_store = Store.objects.create(vendor=self.vendor2, name="Rival")
        other_product = Product.objects.create(store=other_store, name="Rival Thing", price=Decimal("1.00"), stock=1)
        Review.objects.create(product=self.product, buyer=self.buyer, rating=5, comment="Widget is great")
        Review.objects.create(product=self.product_b, buyer=self.buyer, rating=3, comment="Gadget is fine")
        Review.objects.create(product=other_product, buyer=self.buyer, rating=1, comment="Rival is bad")
        self.client.login(username="vendor1", password=PW)

    def test_lists_reviews_with_store_and_product(self):
        """All of this vendor's reviews appear, with store and product names, and no one else's."""
        resp = self.client.get(reverse("vendor_reviews"))
        for text in ("Widget is great", "Gadget is fine", "Shop One", "Shop Two", "Gadget"):
            self.assertContains(resp, text)
        self.assertNotContains(resp, "Rival is bad")

    def test_filter_by_store_and_product(self):
        """The store and product filters narrow the list."""
        resp = self.client.get(reverse("vendor_reviews"), {"store": self.store_b.pk})
        self.assertContains(resp, "Gadget is fine")
        self.assertNotContains(resp, "Widget is great")
        resp = self.client.get(reverse("vendor_reviews"), {"product": self.product.pk})
        self.assertContains(resp, "Widget is great")
        self.assertNotContains(resp, "Gadget is fine")


class PasswordResetTests(BaseCase):
    """Password reset by emailed, expiring, single-use link."""

    def _request(self, email):
        """Submit the 'forgot password' form for an email address."""
        return self.client.post(reverse("password_reset_request"), {"email": email})

    def test_full_flow_and_single_use(self):
        """The emailed link works once and then becomes invalid."""
        self._request("buyer1@example.com")
        self.assertEqual(len(mail.outbox), 1)
        token = mail.outbox[0].body.split("/password-reset/")[1].split("/")[0]
        new_pw = "Brand-new-pass-99!"
        resp = self.client.post(reverse("password_reset_confirm", args=[token]),
                                {"new_password1": new_pw, "new_password2": new_pw})
        self.assertRedirects(resp, reverse("login"))
        self.assertTrue(self.client.login(username="buyer1", password=new_pw))
        self.assertEqual(self.client.get(reverse("password_reset_confirm", args=[token])).status_code, 400)

    def test_unknown_email_gives_same_response_and_sends_nothing(self):
        """An unknown email looks identical to a known one and sends no mail."""
        resp = self._request("nobody@example.com")
        self.assertRedirects(resp, reverse("login"))
        self.assertEqual(len(mail.outbox), 0)

    def test_expired_token_rejected(self):
        """Tokens older than the lifetime are rejected."""
        raw = PasswordResetToken.issue(self.buyer)
        PasswordResetToken.objects.update(created_at=timezone.now() - timedelta(hours=2))
        self.assertIsNone(PasswordResetToken.lookup(raw))
        self.assertEqual(self.client.get(reverse("password_reset_confirm", args=[raw])).status_code, 400)

    def test_new_token_invalidates_old(self):
        """Requesting a new token cancels the previous one."""
        first = PasswordResetToken.issue(self.buyer)
        PasswordResetToken.issue(self.buyer)
        self.assertIsNone(PasswordResetToken.lookup(first))
