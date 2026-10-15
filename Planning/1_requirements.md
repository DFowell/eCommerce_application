# 1. System Requirements

## Users and how they interact with the system

| User | Goals | Main interactions |
|------|-------|-------------------|
| Anonymous visitor | Browse | View product list and product details (incl. reviews); register; log in; request a password reset |
| Buyer | Shop | Browse products across all stores, add to / remove from cart, check out, receive an invoice by email, view past orders, leave reviews |
| Vendor | Sell | Create, view, edit, delete their own stores; add, view, edit, remove products in their own stores |

## Functional requirements

1. Registration and login with a role chosen at sign-up (vendor or buyer).
2. Vendors: full CRUD on their own stores, and on products in those stores.
3. Buyers: view products from all stores, add to cart, check out, leave reviews.
4. The cart lives in the Django session so it persists while the buyer browses.
5. Checkout: remove items from the cart, create an order and its invoice lines, email the invoice to the buyer, reduce stock.
6. Reviews are **verified** when the buyer has previously purchased the product, otherwise **unverified**. Both are shown, labelled. A buyer can leave **several reviews** of the same product: each review is a snapshot of their opinion at that time, so a new review never overwrites an older one.
6a. Vendors have a **Reviews** page listing all reviews of all their products (with store and product shown), filterable by store and product.
6b. Buyers can browse **Vendors -> Stores -> Products** or start from **Stores**, as well as the full **Products** list.
7. Forgotten password: emailed one-time URL containing a token that expires (1 hour) and can only be used once.
8. MariaDB (MySQL-compatible) database with Django migrations.
9. Authentication and role-based permissions on every protected view.

## Data entities

User (role), Store, Product, Order, OrderItem, Review, PasswordResetToken. Cart is session data only.

## Non-functional requirements

* Passwords hashed (Django default) and validated by Django's password validators.
* Prices stored as `Decimal`, never float.
* Order history must survive product deletion (OrderItem snapshots name and price).
