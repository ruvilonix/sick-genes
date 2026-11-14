import requests
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from sickgenes.models import Study

CROSSREF_WORK_URL = 'https://api.crossref.org/works/{doi}'


@staff_member_required
@require_GET
def fetch_paper_info(request):
    """
    Looks up a DOI on Crossref for the Add study form. Returns JSON: the
    form's fields with "success": true, or "success": false and an "error".
    """
    entered_doi = request.GET.get('doi')
    if not entered_doi:
        return lookup_error('DOI is missing.')
    doi = Study.normalize_doi(entered_doi)
    if not doi:
        return lookup_error('Invalid DOI format.')

    try:
        response = requests.get(CROSSREF_WORK_URL.format(doi=doi), timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as error:
        # Also covers a reply that isn't valid JSON
        return lookup_error(f'Failed to connect to API: {error}')

    if not isinstance(data, dict) or data.get('status') != 'ok' or not data.get('message'):
        return lookup_error('No data found for this DOI.')

    return JsonResponse({'success': True, **parse_crossref_work(data['message'])})


def lookup_error(message):
    return JsonResponse({'success': False, 'error': message})


def parse_crossref_work(work):
    """The Add study form's fields from a Crossref work record (its "message")."""
    date_parts = (work.get('issued', {}).get('date-parts') or [[]])[0]
    year, month, day = (list(date_parts) + [None, None, None])[:3]

    return {
        'title': (work.get('title') or [''])[0],
        'authors': '; '.join(filter(None, map(author_name, work.get('author', [])))),
        'publication_year': year,
        'publication_month': month,
        'publication_day': day,
        'journal_titles': '; '.join(work.get('container-title', [])),
        'publisher_url': work.get('resource', {}).get('primary', {}).get('URL', ''),
    }


def author_name(author):
    """"Family, Given", or whichever of the two Crossref has ('' if neither)."""
    return ', '.join(part for part in (author.get('family'), author.get('given')) if part)
