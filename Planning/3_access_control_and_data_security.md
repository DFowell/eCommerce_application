# 3. Access Control and Data Security

## Permission matrix

| Area | Anonymous | Buyer | Vendor |
|------|:--:|:--:|:--:|
| Product list / detail | yes | yes | yes |
| Register / login / password reset | yes | yes | yes |
| Cart, checkout, orders, reviews | no | yes | no |
| Store and product management | no | no | yes (own only) |

## Enforcement
* `@login_required` redirects anonymous users to login.
* A `role_required` decorator raises 403 when a logged-in user has the wrong role.
* **Object-level ownership:** vendor views fetch objects with `get_object_or_404(..., vendor=request.user)`, so another vendor's store/product returns 404. Buyers can only open their own orders.
* State-changing actions (add to cart, remove, checkout, delete) accept POST only and are CSRF-protected.

## Data security
* Passwords: Django's PBKDF2 hashing + password validators.
* Password reset tokens: generated with `secrets.token_urlsafe(32)`; only the SHA-256 hash is stored; expire after 1 hour; single use; issuing a new token invalidates earlier ones. The request page gives the same response whether or not the email exists (prevents account enumeration).
* Secrets and DB credentials come from environment variables, not source code.
* ORM queries only (no raw SQL), so no SQL injection; templates auto-escape output (XSS).
* In production: `DEBUG=False`, HTTPS, secure cookies.
