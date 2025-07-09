import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from sickgenes.models import Study

@require_GET
def fetch_paper_info(request):
    doi = request.GET.get('doi')
    if not doi:
        return JsonResponse({'success': False, 'error': 'DOI is missing.'})

    normalized_doi = Study.normalize_doi(doi) # Use the local normalize_doi function
    if not normalized_doi:
        return JsonResponse({'success': False, 'error': 'Invalid DOI format.'})

    crossref_api_url = f"https://api.crossref.org/works/{normalized_doi}"

    try:
        response = requests.get(crossref_api_url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data and data.get('status') == 'ok' and data.get('message'):
            message = data['message']
            title = message.get('title', [''])[0]

            authors_list = []
            if message.get('author'):
                for author in message['author']:
                    given = author.get('given', '')
                    family = author.get('family', '')
                    if given and family:
                        authors_list.append(f"{family}, {given}")
                    elif family:
                        authors_list.append(family)
                    elif given:
                        authors_list.append(given)
            authors = "; ".join(authors_list)
            
            # Extract date parts
            publication_year, publication_month, publication_day = None, None, None
            date_info = message.get('issued')
            if date_info and date_info.get('date-parts'):
                date_parts = date_info['date-parts'][0]
                if len(date_parts) >= 1:
                    publication_year = date_parts[0]
                if len(date_parts) >= 2:
                    publication_month = date_parts[1]
                if len(date_parts) >= 3:
                    publication_day = date_parts[2]

            publisher_url = message.get("resource", {}).get("primary", {}).get("URL", '')


            return JsonResponse({
                'success': True,
                'title': title,
                'authors': authors,
                'publication_year': publication_year,
                'publication_month': publication_month,
                'publication_day': publication_day,
                'publisher_url': publisher_url,
            })
        else:
            return JsonResponse({'success': False, 'error': 'No data found for this DOI.'})

    except requests.exceptions.RequestException as e:
        return JsonResponse({'success': False, 'error': f'Failed to connect to API: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An unexpected error occurred: {str(e)}'})