# 4. Planning for Failure

| Failure / unexpected behaviour | Response |
|---|---|
| Invalid form input | Re-display the form with field errors; nothing is saved |
| Buyer tries vendor page (or vice versa) | 403 Forbidden |
| Accessing another vendor's store/product or another buyer's order | 404 Not Found |
| Product deleted while in a cart | Cart view drops missing items silently and warns the buyer |
| Requested quantity exceeds stock at checkout | Checkout aborted, nothing changed, buyer told which item is short |
| Two buyers buy the last item at once | Checkout runs in `transaction.atomic()` with `select_for_update()` on products; the loser gets the stock error |
| Error halfway through checkout | Transaction rolls back: no partial order, stock unchanged, cart kept |
| Invoice email fails (SMTP down) | Order is still saved; buyer sees a warning and can open the invoice on the site; the error is logged |
| Password-reset token expired, used or invalid | "Link invalid or expired" page with a link to request a new one |
| Database unavailable | Django's 500 page; configuration via env vars makes switching to a standby easy |
| Schema changes | Applied only through migrations (`makemigrations` / `migrate`) |
| Regressions | Automated tests (`python manage.py test`) cover permissions, checkout, reviews and reset tokens |
