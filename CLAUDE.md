# MediAid

A Bangla-first health platform for Bangladesh: medicine information first, emergency services second. The owner isn't an experienced developer, so explain important decisions simply.

- **Stack:** Django 5.2, PostgreSQL on Neon, deployed on Vercel (region `sin1`). The deployment setup follows `~/Projects/KhorochAi`.
- **Repo:** `RakibulNayeem/MediAid-Web`. New work is on `v2`. Tag `v1-old` is the old 2023 project, kept for history only: never reuse its code.

## Working rules from the owner
- Ask before every push. Merge into `main` only after approval.
- Small, clear commits. After each step, say how to test it locally.
- Don't scrape or copy from medex.com.bd: its terms ban automated extraction without written consent. Data comes from DGDA lists and official leaflets, loaded through the CSV import.

## Layout
- `config/`: settings and URLs. All secrets come from the environment.
- `core/`: home page, `BanglaFirstLocaleMiddleware`, template filters (`num`, `taka`, `localized`, `lines`), `compile_po`.
- `medicines/`: models, `search.py`, `importer.py`, `text.py`, views, admin, and the `import_csv` and `seed_sample` commands.
- `emergency/`: phase 2 placeholders only, with no models yet.
- `static/img/brand/`: logos and icons copied from `MediAid-Logo-Kit/` (kept out of git). Header: Bangla or English on-dark logo by language. Footer: bilingual on-dark. Follow the rules in the kit README.
- `templates/`, `static/css/style.css` (the only CSS file; colours are variables at the top), `locale/bn/`.

## Key decisions
- **Search** (`medicines/search.py`) tries these in order:
  1. Each typed word must start a word in `Medicine.search_text`. That field is lower-case with a leading space. Use `contains`, never `icontains`, because `UPPER()` stops PostgreSQL using the trigram index.
  2. A Bangla query with no match is romanised (`bangla_to_latin`), because official lists only have English names.
  3. Same sound (`sound_key`, stored in `sound_text`), so other spellings find the right medicine.
  4. Closest spelling with `TrigramWordSimilarity`, on PostgreSQL only. These can be different medicines, so the page labels them.
- **Local SQLite is allowed** when `DATABASE_URL` is empty. The trigram index migrations and fuzzy search skip themselves there. Run tests on PostgreSQL as well when changing search.
- **Alternatives** are the same `generic` + `strength_key` + `dosage_form`. `strength_key` makes "500 mg" equal "500mg".
- **Savings** only show when both brands have the same non-empty `price_unit`, so differently sized packs are never compared.
- **Language:** Bangla unless the cookie says otherwise, ignoring the browser's language. Generic info text is in Bangla only; the English toggle translates the interface and says so on the page.
- **Names:** on the Bangla site, brand, generic and company show as Bangla with the English beside them (the `dual` filter), so people can still match the box. Most Bangla names are automatic (`transliterate.py`, `fill_bangla_names`, marked `*_bn_auto`) and need review.
- **Numbers:** prices, counts and strengths get Bangla digits on the server (`num`, `taka`).
- **Import:** all or nothing. Blank cells keep stored values. Only rows that really changed are written.
- **`is_sample`** marks test data. Pages show a warning on these rows. Sample prices are invented and the text is unverified, so sample data must not go live as if real. `seed_sample` needs `--force` when `DEBUG` is off.

## Accounts and leaderboard
- **Accounts:** django-allauth at `/accounts/`, email plus Google (button appears only when `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set; Google logs in to the account with the same verified email), verified by 6-digit code. Off on the live site until `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are set (`ACCOUNTS_ENABLED`).
- **Leaderboard:** `Medicine.search_count` and `view_count`, totals only, grouped by brand. Bots are not counted, and nothing records who searched.
- **Prescriptions (not built):** never send real prescriptions to the free Gemini tier. Google says not to submit personal data there and reviewers may read it. Real uploads need a billed project; test with made-up prescriptions. The photo is deleted after the final check.
- **Git:** old `main` commits still track `db.sqlite3`, so switching to them overwrites the ignored local database.

## Commands
- `python manage.py test`
- `python manage.py seed_sample [--clear]`
- `python manage.py import_csv medicines|generics FILE [--dry-run]`
- `python manage.py convert_dgda DGDA_EXPORT.csv OUTPUT.csv` prepares DGDA's export for the import. The export has no prices or Bangla names.
- `python manage.py makemessages -l bn --ignore=.venv --no-location --no-wrap`, then edit the `.po`, then `python manage.py compile_po`. Commit the `.mo` too.
- Run migrations on Neon with the direct connection string before the code that needs them goes live.
