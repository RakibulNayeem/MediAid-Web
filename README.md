# MediAid

A Bangla-first health platform for Bangladesh, built with Django.

- **Phase 1 (built):** medicine search in Bangla and English, medicine and generic pages, cheaper alternatives, browsing, and a CSV import.
- **Phase 2 (not built yet):** blood donors, ambulances, hospitals and doctors. These pages currently show "coming soon" with the 999 and 16263 helplines.

## Run it on your computer

You need Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env`, set `DEBUG=True` and put a random value in `DJANGO_SECRET_KEY`. Leave `DATABASE_URL` empty to use a local SQLite file.

```bash
python manage.py migrate
python manage.py seed_sample        # adds test medicines, marked as sample data
python manage.py createsuperuser    # your admin login
python manage.py runserver
```

Then open:

- http://127.0.0.1:8000/ for the site
- http://127.0.0.1:8000/admin/ for the admin

Spelling-mistake search ("paracitamol") only works on PostgreSQL, so it does nothing on local SQLite. Everything else works the same.

### Run the tests

```bash
python manage.py test
```

## Load real data

Use official sources only: DGDA's registered drug lists and official product leaflets. Do not copy data from medex.com.bd or other medicine sites.

**Small files (under about 4 MB):** in the admin, open Medicines, then **Import CSV**. Leave "Check only" ticked first. If the check passes, untick it and upload again.

**Big files:** run this on your computer, with `DATABASE_URL` in `.env` pointing at the database you want to fill:

```bash
python manage.py import_csv medicines my_file.csv --dry-run   # check only
python manage.py import_csv medicines my_file.csv             # save
python manage.py import_csv generics my_info.csv
```

Example files are in `sample_data/`. How the import behaves:

- The file must be UTF-8. In Excel: Save As, then "CSV UTF-8".
- If any row has a problem, nothing is saved, and you get a list of the lines to fix.
- Importing again updates existing rows. A row is matched by `dgda_registration_no`, or otherwise by brand + strength + form + manufacturer.
- Blank cells never erase stored data.
- Fill in `price_unit` (for example `1 tablet`). Savings only show between brands with the same unit, so a 60 ml bottle is never compared with a 100 ml one.

To remove the sample data once real data is in:

```bash
python manage.py seed_sample --clear
```

## Deploy on Vercel + Neon

1. **Neon:** create a project (Singapore region). Copy two connection strings: the **pooled** one (host contains `-pooler`) and the **direct** one.
2. **Vercel:** import the GitHub repo. Under Settings → Environment Variables, add:

   | Name | Value |
   |---|---|
   | `DJANGO_SECRET_KEY` | a long random string |
   | `DEBUG` | `False` |
   | `DATABASE_URL` | the Neon **pooled** connection string |
   | `ALLOWED_HOSTS` | `.vercel.app` (add your own domain if you have one) |
   | `CSRF_TRUSTED_ORIGINS` | `https://*.vercel.app` (add `https://yourdomain.com` if you have one) |

3. **Create the tables** from your computer, using the **direct** connection string:

   ```bash
   DATABASE_URL="<neon direct string>" python manage.py migrate
   DATABASE_URL="<neon direct string>" python manage.py createsuperuser
   ```

4. **Deploy.** Vercel runs `collectstatic` by itself during the build, because `STATIC_ROOT` is set. Every push to the production branch deploys.

Whenever a change includes a new migration, run `migrate` on Neon *before* the code goes live.

Vercel has no permanent file storage, so the app stores no uploaded files. CSV imports are read into the database straight away. Vercel also refuses uploads above about 4.5 MB, which is why big files use the command above.

## Change the look or the text

- **Colours and styles:** `static/css/style.css`. The colour variables are at the top.
- **Translations:** edit `locale/bn/LC_MESSAGES/django.po`, then run `python manage.py compile_po` and commit both the `.po` and `.mo` files.
