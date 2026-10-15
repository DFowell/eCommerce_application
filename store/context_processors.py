"""Template context processors."""


def cart_count(request):
    """Expose the number of items in the session cart to every template.

    Args:
        request: The current HttpRequest.

    Returns:
        A dict with the key ``cart_count``.
    """
    cart = request.session.get("cart", {})
    return {"cart_count": sum(cart.values()) if cart else 0}
