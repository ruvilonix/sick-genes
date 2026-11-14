# sickgenes

The source code for [sickgenes.xyz](https://sickgenes.xyz), a site that collects gene findings from ME/CFS studies. Visitors can look up a gene and see which studies have reported it.

The code is not tied to ME/CFS. The site name, home page text, about page and literature search terms are all set in the admin, so it can be used for any disease.

It is a Django app that needs PostgreSQL (SQLite will not work).

## Quick start

You need Python 3.13 or newer and a PostgreSQL database.

Clone the repository and install the dependencies:

```
git clone https://github.com/ruvilonix/sick-genes.git
cd sick-genes
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`psycopg2` builds from source and needs the PostgreSQL client headers (`libpq-dev` on Debian/Ubuntu, `libpq-devel` on Fedora). If you would rather not install them, use `pip install psycopg2-binary` instead for local development.

Create a file called `.env` in the project root:

```
SECRET_KEY="change-me"
DEBUG="True"
ALLOWED_HOSTS="localhost 127.0.0.1 [::1]"
DATABASE_URL="postgres://USER:PASSWORD@localhost:5432/DATABASE"
CONTACT_EMAIL_ADDRESS="you@example.com"
```

You can generate a secret key with:

```
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Set up the database, import the gene list from HGNC (this downloads about 35 MB and can take a few minutes), and create an admin account:

```
python manage.py migrate
python manage.py import_molecule_data hgnc
python manage.py createsuperuser
```

Start the site:

```
python manage.py runserver
```

It is now running at http://127.0.0.1:8000.

## Adding data

Log in at http://127.0.0.1:8000/admin with the account you created.

1. Under **Site Configurations**, set the site name, home page and about text, and the literature search terms used on gene pages.
2. Under **Diseases**, add the phenotypes you want to tag study cohorts with.
3. Use **Add Study** in the site's menu to add a study. New studies are hidden from the public until you publish them.
4. On the study page, add a cohort, then paste in its genes.

Hidden studies are listed under **Hidden Studies** in the menu.

## Running the tests

```
python manage.py test sickgenes
```

The tests need a PostgreSQL user that is allowed to create databases.

Pull requests also run the linter [ruff](https://docs.astral.sh/ruff/) (configured in `pyproject.toml`) and check that every model change has a migration:

```
pip install ruff
ruff check .
python manage.py makemigrations --check --dry-run
```

## Deployment

The `Procfile` runs the site with gunicorn and applies migrations and collects static files on each release. It works as-is on Dokku or Heroku-style hosts. In production, set `DEBUG="False"` and set `ALLOWED_HOSTS` to your domain.

## Data sources

Gene names and symbols come from the [HGNC](https://www.genenames.org/) database.
