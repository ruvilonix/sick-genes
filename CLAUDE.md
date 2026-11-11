# sickgenes

Django site ([sickgenes.xyz](https://sickgenes.xyz)) that collects gene findings from ME/CFS studies. You can look up a gene and see which papers have flagged it as potentially interesting. The main data is: `Study` → `StudyCohort` (tagged with diseases) → `GeneFinding` → `HgncGene`. Studies with `not_finished=True`, or that have a `newest_version`, are hidden from the public.

## Local development

- Python virtualenv: `.venv`. Dependencies come from `requirements.txt`, except that `psycopg2-binary` is used locally in place of `psycopg2`.
- Postgres runs in a Podman container called `sickgenes-pg`, with data kept in the volume `sickgenes-pgdata`. Run `podman start sickgenes-pg` after a reboot.
- Settings are read from `.env` (gitignored).
- Run the site: `.venv/bin/python manage.py runserver`
- Run the tests: `.venv/bin/python manage.py test sickgenes`
- The app needs Postgres (it uses `ArrayField`); SQLite won't work.

## Workflow

- Never commit straight to `main`. Make a branch, push it, and open a PR with `gh pr create`. The user reviews and merges.
- End commit messages with a `Co-Authored-By: Claude` line whenever Claude contributed.
- The user prefers simple, minimal changes.

## Planned work

See [IMPROVEMENTS.md](IMPROVEMENTS.md) for the list of planned improvements. Update it when an item is done.
