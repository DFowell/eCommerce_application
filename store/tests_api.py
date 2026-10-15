"""Tests for the REST API: authentication, vendor CRUD, buyer reads, review CRUD."""
from decimal import Decimal

from rest_framework.test import APITestCase

from .models import Order, OrderItem, Product, Review, Store, User

PW = "S3cure-pass-phrase!"


def make_user(username, role):
    """Create and return a user with the given role and a known password."""
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password=PW, role=role
    )


class ApiBase(APITestCase):
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


class AuthTests(ApiBase):
    """Token authentication."""

    def test_token_login_and_use(self):
        """A token from /api/auth/token/ can be used on other endpoints."""
        resp = self.client.post("/api/auth/token/", {"username": "vendor1", "password": PW})
        self.assertEqual(resp.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + resp.data["token"])
        self.assertEqual(self.client.get("/api/stores/").status_code, 200)

    def test_anonymous_rejected(self):
        """Requests without a token are refused with 401."""
        self.assertEqual(self.client.get("/api/stores/").status_code, 401)
        self.assertEqual(self.client.post("/api/stores/", {"name": "x"}).status_code, 401)


class VendorWriteTests(ApiBase):
    """Vendors can create, update and delete their own stores and products."""

    def setUp(self):
        """Authenticate as the first vendor."""
        super().setUp()
        self.client.force_authenticate(self.vendor)

    def test_create_store_sets_owner_from_token(self):
        """The owner is the caller even if another vendor id is sent."""
        resp = self.client.post("/api/stores/", {"name": "New", "description": "d", "vendor": self.vendor2.pk})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Store.objects.get(name="New").vendor, self.vendor)

    def test_update_and_delete_own_store(self):
        """A vendor can edit and delete a store they own."""
        url = f"/api/stores/{self.store.pk}/"
        self.assertEqual(self.client.patch(url, {"name": "Renamed"}).status_code, 200)
        self.store.refresh_from_db()
        self.assertEqual(self.store.name, "Renamed")
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_add_product_to_own_store(self):
        """A vendor can add a product to their store."""
        resp = self.client.post(
            f"/api/stores/{self.store.pk}/products/",
            {"name": "Gizmo", "description": "", "price": "3.50", "stock": 4},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Product.objects.get(name="Gizmo").store, self.store)

    def test_invalid_product_rejected(self):
        """A negative price is rejected with 400."""
        resp = self.client.post(
            f"/api/stores/{self.store.pk}/products/", {"name": "Bad", "price": "-1", "stock": 1}
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_and_delete_own_product(self):
        """A vendor can edit and delete their own product."""
        url = f"/api/products/{self.product.pk}/"
        self.assertEqual(self.client.patch(url, {"stock": 9}).status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 9)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_cannot_touch_other_vendors_resources(self):
        """Another vendor's store and product cannot be changed (403)."""
        self.client.force_authenticate(self.vendor2)
        self.assertEqual(
            self.client.post(f"/api/stores/{self.store.pk}/products/",
                             {"name": "Hack", "price": "1.00", "stock": 1}).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/stores/{self.store.pk}/", {"name": "Mine"}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/products/{self.product.pk}/").status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())


class BuyerTests(ApiBase):
    """Buyers can read stores and products but not change them."""

    def setUp(self):
        """Authenticate as the buyer."""
        super().setUp()
        self.client.force_authenticate(self.buyer)

    def test_buyer_can_read(self):
        """Buyers can list stores, a vendor's stores, and a store's products."""
        self.assertEqual(self.client.get("/api/stores/").status_code, 200)
        resp = self.client.get(f"/api/vendors/{self.vendor.pk}/stores/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]["products"][0]["name"], "Widget")
        self.assertEqual(self.client.get(f"/api/stores/{self.store.pk}/products/").status_code, 200)

    def test_buyer_cannot_write_stores_or_products(self):
        """Buyers get 403 when trying to create or delete vendor resources."""
        self.assertEqual(self.client.post("/api/stores/", {"name": "Nope"}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/products/{self.product.pk}/").status_code, 403)

    def test_unknown_vendor_404(self):
        """A buyer id is not a vendor, so its stores endpoint is 404."""
        self.assertEqual(self.client.get(f"/api/vendors/{self.buyer.pk}/stores/").status_code, 404)


class ReviewApiTests(ApiBase):
    """Review CRUD: buyers write their own reviews, vendors read reviews of their products."""

    def test_buyer_creates_multiple_reviews(self):
        """A buyer can post several reviews of one product; none overwrite the others."""
        self.client.force_authenticate(self.buyer)
        url = f"/api/products/{self.product.pk}/reviews/"
        first = self.client.post(url, {"rating": 2, "comment": "meh"})
        second = self.client.post(url, {"rating": 5, "comment": "better now"})
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertEqual(Review.objects.filter(product=self.product).count(), 2)
        self.assertFalse(first.data["verified"])

    def test_review_is_verified_after_purchase(self):
        """Reviews written after buying the product are verified."""
        order = Order.objects.create(buyer=self.buyer)
        OrderItem.objects.create(order=order, product=self.product, product_name="Widget",
                                 unit_price=Decimal("9.99"), quantity=1)
        self.client.force_authenticate(self.buyer)
        resp = self.client.post(f"/api/products/{self.product.pk}/reviews/", {"rating": 5})
        self.assertTrue(resp.data["verified"])

    def test_buyer_updates_and_deletes_own_review(self):
        """Buyers can edit and delete their own reviews."""
        review = Review.objects.create(product=self.product, buyer=self.buyer, rating=3, comment="ok")
        self.client.force_authenticate(self.buyer)
        url = f"/api/reviews/{review.pk}/"
        self.assertEqual(self.client.patch(url, {"comment": "updated"}).status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.comment, "updated")
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_other_buyer_cannot_change_review(self):
        """A buyer cannot edit or delete someone else's review."""
        review = Review.objects.create(product=self.product, buyer=self.buyer, rating=3)
        self.client.force_authenticate(make_user("buyer2", User.BUYER))
        url = f"/api/reviews/{review.pk}/"
        self.assertEqual(self.client.patch(url, {"rating": 1}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)

    def test_vendor_cannot_write_reviews(self):
        """Vendors can read reviews but not create them."""
        self.client.force_authenticate(self.vendor)
        resp = self.client.post(f"/api/products/{self.product.pk}/reviews/", {"rating": 5})
        self.assertEqual(resp.status_code, 403)

    def test_invalid_rating_rejected(self):
        """A rating outside 1-5 is rejected with 400."""
        self.client.force_authenticate(self.buyer)
        resp = self.client.post(f"/api/products/{self.product.pk}/reviews/", {"rating": 9})
        self.assertEqual(resp.status_code, 400)

    def test_vendor_reads_all_reviews_with_filters(self):
        """/api/reviews/ lists reviews across the vendor's products, filterable by store/product."""
        store_b = Store.objects.create(vendor=self.vendor, name="Shop Two")
        product_b = Product.objects.create(store=store_b, name="Gadget", price=Decimal("5.00"), stock=1)
        rival_store = Store.objects.create(vendor=self.vendor2, name="Rival")
        rival = Product.objects.create(store=rival_store, name="Rival Thing", price=Decimal("1.00"), stock=1)
        Review.objects.create(product=self.product, buyer=self.buyer, rating=5, comment="a")
        Review.objects.create(product=product_b, buyer=self.buyer, rating=4, comment="b")
        Review.objects.create(product=rival, buyer=self.buyer, rating=1, comment="c")
        self.client.force_authenticate(self.vendor)
        resp = self.client.get("/api/reviews/")
        self.assertEqual(sorted(r["comment"] for r in resp.data), ["a", "b"])
        self.assertEqual({r["store_name"] for r in resp.data}, {"Shop One", "Shop Two"})
        resp = self.client.get(f"/api/reviews/?store={store_b.pk}")
        self.assertEqual([r["comment"] for r in resp.data], ["b"])
        resp = self.client.get(f"/api/reviews/?product={self.product.pk}")
        self.assertEqual([r["comment"] for r in resp.data], ["a"])

    def test_buyer_review_list_shows_only_own(self):
        """For a buyer, /api/reviews/ shows only the reviews they wrote."""
        other = make_user("buyer2", User.BUYER)
        Review.objects.create(product=self.product, buyer=self.buyer, rating=5, comment="mine")
        Review.objects.create(product=self.product, buyer=other, rating=1, comment="theirs")
        self.client.force_authenticate(self.buyer)
        resp = self.client.get("/api/reviews/")
        self.assertEqual([r["comment"] for r in resp.data], ["mine"])
