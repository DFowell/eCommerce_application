# 2. User Interface Layout

A shared base template gives every page the same navigation bar, flash-message area and content block. The menu is different for each kind of user so each person only sees the paths they can use.

## Navigation menus

| User | Menu (left to right) | Right-hand side |
|------|----------------------|-----------------|
| Visitor | Products, Vendors, Stores, Reddit | Login, Register |
| Buyer | Products, Vendors, Stores, Reddit, Cart (n), My orders | username, Logout |
| Vendor | **My stores**, **Shop**, **Reviews**, Reddit | username, Logout |

* **Vendor "My stores"** – the vendor's own stores, with edit/delete and their products.
* **Vendor "Shop"** – all products on the site (same page buyers call "Products").
* **Vendor "Reviews"** – every review for every product the vendor sells, in one table with the store and product name on each row, and Store / Product filters. A vendor with 1000 products does not have to open them one by one.

## Buyer browsing paths (three ways in)

```
Products  -> product page -> add to cart
Vendors   -> a vendor's stores -> a store's products -> product page
Stores    -> a store's products -> product page            (all stores, any vendor)
```
Every product page links back to its store and vendor, so a buyer who knows only a vendor or a store name can still find the product.

## Pages

```
Products                 search box + grid of product cards (name, store link, price, stock)
Product detail           description, price, store/vendor links, [Add to cart] (buyers),
                         reviews with date and Verified/Unverified badge,
                         "Leave a review" form (buyers) - can be used many times
Vendors                  table of vendors with store counts
Vendor's stores          table of that vendor's stores
Stores                   table of all stores with their vendor
Store products           grid of the store's products
Cart                     product, qty, line total, [Remove]; total; [Checkout]
My orders / Invoice      list of past orders; invoice page with line items and total
Login / Register         simple forms; register has a vendor/buyer selector
Forgot password          email form -> emailed link -> new-password form
My stores (vendor)       stores with [View] [Edit] [Delete], [New store]
Store detail (vendor)    store info, product table with [Edit] [Remove], [Add product]
Reviews (vendor)         filterable table: store, product, rating, comment, buyer, date
Reddit                   latest posts of r/django (title link, author, score)
Create/edit forms        single-column forms with inline error messages
Confirm delete           explicit confirmation page for stores and products
```

## UX principles
* Success / error feedback via flash messages after every action.
* Destructive actions always need a confirmation page.
* A 403 page for role violations and a 404 page for missing or not-owned objects.
