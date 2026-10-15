# eCommerce Django Web App

Vendors create stores and products; buyers browse (by product, vendor or store), fill a session-based cart, check out (invoice emailed) and leave reviews. Vendors have a Reviews page listing the reviews of all their products. There is also a REST API and a Reddit feed. Planning documents are in the `Planning/` folder.

---

## Setup, step by step

You need these installed first:

* **Python 3.10 or newer** – https://www.python.org/downloads/ (on Windows tick "Add Python to PATH").
* **Git** – https://git-scm.com/downloads
* **MariaDB** – https://mariadb.org/download/ (remember the root password you choose during install).

Commands below are typed into a **terminal**: on Windows open **Command Prompt** (press the Windows key, type `cmd`, Enter); on macOS open **Terminal**. Type each command and press Enter.

### 1. Clone the repository onto your computer

Go to the folder where you keep projects (for example `cd Documents`), then run:

```
git clone https://github.com/DFowell/eCommerce_application.git
```

### 2. Enter the project folder

```
cd eCommerce_application
```
This is the folder that contains `manage.py`. **Stay in this folder for every command below.**

### 3. Create and activate a virtual environment

The virtual environment (`venv`) keeps this project's packages separate from the rest of your computer. It is created *inside* the project folder:

```
python -m venv venv
```
Activate it:

| System | Command |
|---|---|
| Windows (Command Prompt) | `venv\Scripts\activate` |
| Windows (PowerShell) | `venv\Scripts\Activate.ps1` |
| macOS / Linux | `source venv/bin/activate` |

You should now see `(venv)` at the start of your prompt. (On macOS/Linux use `python3` if `python` is not found.)

### 4. Install the required packages

Now that you are inside the project folder, `requirements.txt` can be found:

```
pip install -r requirements.txt
```

### 5. Create the database in MariaDB

`migrate` (step 7) fills a database but does not create it, so create it first.

**5a. Open the MariaDB command line.**
* Windows: if `mysql -u root -p` says "not recognized", use the full path instead (change the version number to match your folder in `C:\Program Files\MariaDB ...`):
  ```
  "C:\Program Files\MariaDB 11.4\bin\mysql.exe" -u root -p
  ```
  Otherwise open **Start menu > MariaDB > Command Prompt**.
* macOS / Linux: `mysql -u root -p` (on Linux you may need `sudo mysql`).

Enter the MariaDB root password when asked. The prompt changes to `MariaDB [(none)]>`.

**5b. Copy and paste this SQL** (change `choose-a-password` to a password of your own, keeping the quotes; remember it for step 6). Paste it all at once:

```sql
CREATE DATABASE shop CHARACTER SET utf8mb4;
CREATE USER 'shop_user'@'localhost' IDENTIFIED BY 'choose-a-password';
GRANT ALL PRIVILEGES ON shop.* TO 'shop_user'@'localhost';
GRANT ALL PRIVILEGES ON test_shop.* TO 'shop_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```
(`test_shop` is the temporary database Django creates when running the tests.)

### 6. Set the environment variables

The project reads the database details from *environment variables* so no passwords are stored in the code. Set them **in the same terminal window, with the virtual environment active, that you will use to run the server** (step 8). They only last for that window; if you open a new terminal, set them again.

| System | Commands (replace `choose-a-password` with the one from step 5) |
|---|---|
| Windows Command Prompt | `set DB_NAME=shop`<br>`set DB_USER=shop_user`<br>`set DB_PASSWORD=choose-a-password`<br>`set DB_HOST=127.0.0.1`<br>`set DB_PORT=3306` |
| Windows PowerShell | `$env:DB_NAME="shop"`<br>`$env:DB_USER="shop_user"`<br>`$env:DB_PASSWORD="choose-a-password"`<br>`$env:DB_HOST="127.0.0.1"`<br>`$env:DB_PORT="3306"` |
| macOS / Linux | `export DB_NAME=shop`<br>`export DB_USER=shop_user`<br>`export DB_PASSWORD=choose-a-password`<br>`export DB_HOST=127.0.0.1`<br>`export DB_PORT=3306` |

(On Command Prompt do not add quotes around the values. If `DB_NAME` is not set the project uses a SQLite file instead, which is handy for a quick try-out but is not MariaDB.)

### 7. Create the tables (migrations)

```
python manage.py migrate
```
You should see a list of lines ending in `OK`. (The migration files are already included in the repository. If you change a model yourself, run `python manage.py makemigrations store` first.)

Optional – create an admin login for http://127.0.0.1:8000/admin/ :
```
python manage.py createsuperuser
```

### 8. Start the server and open the application

```
python manage.py runserver
```
Now open your web browser and go to:

* **The website:** http://127.0.0.1:8000/
* The REST API: http://127.0.0.1:8000/api/ (see below)
* Admin site: http://127.0.0.1:8000/admin/

Leave the terminal running while you use the site; press **Ctrl+C** in it to stop the server. Invoice and password-reset emails are *printed in this terminal window* (they are not sent to a real mailbox unless you set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in the same way as step 6).

---

## Using the application

1. Click **Register**, choose **Vendor**, and create an account. Use **My stores** to create a store and add products.
2. Log out, register a second account as a **Buyer**.
3. As a buyer, find products via **Products**, **Vendors** (vendor -> its stores -> a store's products) or **Stores** (any store -> its products). Add items to the **Cart** and **Checkout**; the invoice appears in **My orders** and is printed in the server terminal.
4. On a product page leave a review. You can review the same product again later; every review is kept. It is marked *Verified* if you have bought the product.
5. Log in as the vendor again and open **Reviews** to see all reviews of all your products, with the store and product for each. Use the Store and Product filters to narrow the list.
6. Forgot password? Use the link on the login page; the reset link (valid for 1 hour, single use) is printed in the server terminal.
7. **Reddit** shows the latest posts of r/django.

Vendor menu: **My stores, Shop, Reviews, Reddit**. Buyer menu: **Products, Vendors, Stores, Reddit, Cart, My orders**.

## Running the tests

```
python manage.py test
```
(Needs the same environment variables and the `test_shop` permission from step 5.) You should see `OK` at the end. To check that every module, class and function has a docstring run `python check_docstrings.py`.

## REST API

Get a token, then send it with every request in an `Authorization: Token <key>` header.

Windows Command Prompt:
```
curl -X POST http://127.0.0.1:8000/api/auth/token/ -d "username=vendor1&password=YOURPASSWORD"
curl http://127.0.0.1:8000/api/stores/ -H "Authorization: Token PASTE_TOKEN_HERE"
```
`python api_demo.py <vendor_username> <password>` shows the same flow using the `requests` module. The endpoints, JSON formats and sequence diagrams are in `Planning/5_api_plan.md`. While logged in on the website you can also browse the API in your browser, e.g. http://127.0.0.1:8000/api/reviews/

## Troubleshooting

| Message | Fix |
|---|---|
| `'mysql' is not recognized` | Use the full path or the Start-menu MariaDB Command Prompt (step 5a). |
| `Access denied for user 'shop_user'` | The password in `DB_PASSWORD` differs from step 5b, or the variables are not set in this terminal window (step 6). |
| `Unknown database 'shop'` | Step 5 was skipped. |
| `Can't connect to MySQL server` | MariaDB is not running. |
| `No module named ...` | The virtual environment is not active (step 3) or step 4 was skipped. |
| Tests: `Access denied ... test_shop` | The `test_shop` GRANT line in step 5b was skipped. |
| Reddit page shows an error | Reddit sometimes blocks automated requests; wait a minute and refresh. |

## Project layout

```
manage.py               Django command-line entry point
ecommerce_project/      settings, root URLs
store/                  the app: models, views, forms, templates, REST API, tests
functions/reddit.py     helper that fetches posts from Reddit
Planning/               planning documents and sequence diagrams
api_demo.py             example script that uses the REST API
check_docstrings.py     reports missing docstrings
requirements.txt        Python packages
```
