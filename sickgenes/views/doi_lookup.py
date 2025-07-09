import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from datetime import datetime
from sickgenes.models import Study
import re

def normalize_doi(doi_string):
        if not doi_string:
            return ""
        normalized_doi = re.sub(r'^((?:https?:\/\/)?(?:dx\.)?doi\.org\/)?', '', doi_string.strip(), flags=re.IGNORECASE)
        if not normalized_doi.startswith('10.'):
            return None
        return normalized_doi

@require_GET
def fetch_paper_info(request):
    doi = request.GET.get('doi')
    if not doi:
        return JsonResponse({'success': False, 'error': 'DOI is missing.'})

    normalized_doi = Study.normalize_doi(doi)
    if not normalized_doi:
        return JsonResponse({'success': False, 'error': 'Invalid DOI format.'})

    crossref_api_url = f"https://api.crossref.org/works/{normalized_doi}"

    try:
        response = requests.get(crossref_api_url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data and data.get('status') == 'ok' and data.get('message'):
            message = data['message']
            title = message.get('title', [])[0] if message.get('title') else ''
            
            authors_list = []
            if message.get('author'):
                for author in message['author']:
                    given = author.get('given', '')
                    family = author.get('family', '')
                    if given and family:
                        authors_list.append(f"{given} {family}")
                    elif family:
                        authors_list.append(family)
                    elif given:
                        authors_list.append(given)
            authors = ", ".join(authors_list)

            publication_date = None
            if message.get('published-print') and message['published-print'].get('date-parts'):
                date_parts = message['published-print']['date-parts'][0]
                try:
                    if len(date_parts) == 3:
                        publication_date = datetime(date_parts[0], date_parts[1], date_parts[2]).strftime('%Y-%m-%d')
                    elif len(date_parts) == 2:
                        publication_date = datetime(date_parts[0], date_parts[1], 1).strftime('%Y-%m-%d')
                    elif len(date_parts) == 1:
                        publication_date = datetime(date_parts[0], 1, 1).strftime('%Y-%m-%d')
                except ValueError:
                    publication_date = None
            elif message.get('issued') and message['issued'].get('date-parts'):
                 date_parts = message['issued']['date-parts'][0]
                 try:
                    if len(date_parts) == 3:
                        publication_date = datetime(date_parts[0], date_parts[1], date_parts[2]).strftime('%Y-%m-%d')
                    elif len(date_parts) == 2:
                        publication_date = datetime(date_parts[0], date_parts[1], 1).strftime('%Y-%m-%d')
                    elif len(date_parts) == 1:
                        publication_date = datetime(date_parts[0], 1, 1).strftime('%Y-%m-%d')
                 except ValueError:
                    publication_date = None

            publisher_url = None
            if message.get('resource') and message['resource'].get('primary') and message['resource']['primary'].get('URL'):
                publisher_url = message['resource']['primary']['URL']


            return JsonResponse({
                'success': True,
                'title': title,
                'authors': authors,
                'publication_date': publication_date,
                'publisher_url': publisher_url,
            })
        else:
            return JsonResponse({'success': False, 'error': 'No data found for this DOI.'})

    except requests.exceptions.RequestException as e:
        return JsonResponse({'success': False, 'error': f'Failed to connect to API: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An unexpected error occurred: {str(e)}'})