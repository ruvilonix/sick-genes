# Improvement ideas

Planned improvements to the codebase, roughly in priority order. Each one is meant to be its own small PR. Remove an item, or mark it done, once it's merged.

## Worth doing soon

1. **Run tests automatically on every PR.** Add a GitHub Actions workflow that runs the test suite against Postgres on each pull request.

2. **Make Gene Search faster for long lists.** `BaseMoleculeManager.find_matching_items` (`sickgenes/models/managers.py`) runs about 15 queries per search term, one per ID field and alias table. 10 genes took 148 queries, so 500 genes would take about 7,000. Batch the lookups so the number of queries doesn't grow with the number of terms.

3. **Keep the study list's phenotype filter in the URL instead of the session.** `study_list` saves the filter to `request.session['study_disease_filter']` and the AJAX view `table_study` reads it from there. With two tabs open, the second tab's filter applies to the first tab's table. A filtered list also can't be shared as a link.

4. **Production security settings.** `manage.py check --deploy` warns that `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` aren't set. Check how the host handles HTTPS before turning these on. Also, the debug toolbar is loaded whenever tests aren't running, including in production. Load it only when `DEBUG` is on.

## Small cleanup

5. Messages are only rendered in `study.html`. Move the messages block into `base.html` so they show on every page.
6. Remove dead code:
   - the criteria page and `criteria.md` (marked as no longer needed)
   - the duplicate `context_processors.request` entry in `settings.py`
   - Django's default comments in `projectfinding/urls.py`
   - the v1 API (`views/api/old_versions.py`), if nothing uses it any more

## Ideas that serve the site's goal

7. **Gene page:** show the number of studies clearly and link straight to each study's note.
8. **Renamed genes:** when a symbol isn't found, look it up in previous symbols (`PrevSymbol`) and redirect to the current gene, so old links and searches don't 404.
9. **Gene Search results:** show the results directly instead of redirecting to `/genes/?symbol=...`. This removes the last place where a long gene list can hit gunicorn's request line limit of about 4 KB.
