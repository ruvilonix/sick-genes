This is the source code repository for the website [sickgenes.xyz](https://sickgenes.xyz).

To install and run, place these variables in a `.env.` file in the project root (fill in secret key and database URL):

```
SECRET_KEY="<CREATE SECRET KEY> "
DEBUG="True"
ALLOWED_HOSTS="localhost 127.0.0.1 [::1]"
DATABASE_URL="postgres://<username>:<password>@localhost:5432/<database>"

CONTACT_EMAIL_ADDRESS="<email address>"
```

Import HGNC data by running `python manage.py import_molecule_data hgnc`.