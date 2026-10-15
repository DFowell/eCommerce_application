"""Tiny script showing the API being used with the ``requests`` module.

1. Start the server:  python manage.py runserver
2. In a second terminal (same virtual environment), run:
       python api_demo.py <vendor_username> <password>
"""
import sys

import requests

BASE = "http://127.0.0.1:8000/api"


def main(username, password):
    """Log in as a vendor, create a store and product, then read stores and reviews."""
    # 1. log in and get a token
    response = requests.post(f"{BASE}/auth/token/", data={"username": username, "password": password})
    response.raise_for_status()
    headers = {"Authorization": f"Token {response.json()['token']}"}

    # 2. create a store
    store = requests.post(f"{BASE}/stores/", json={"name": "API Store", "description": "Made via API"}, headers=headers)
    print("create store:", store.status_code, store.json())

    # 3. add a product to it
    product = requests.post(
        f"{BASE}/stores/{store.json()['id']}/products/",
        json={"name": "API Widget", "description": "", "price": "4.99", "stock": 10},
        headers=headers,
    )
    print("add product:", product.status_code, product.json())

    # 4. list the stores, and all reviews of this vendor's products
    print("stores:", requests.get(f"{BASE}/stores/", headers=headers).json())
    print("reviews:", requests.get(f"{BASE}/reviews/", headers=headers).json())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
