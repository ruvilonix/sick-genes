from sickgenes.models import Molecule
from django.db.models import Q

def find_matching_molecules(search_strings):
    """
    takes list of search strings and returns list of dicts for each string: 
    [{'search_string': 'ABC', 'molecules': [obj1, obj2]}, ...]
    """
    search_results = []
    for search_string in search_strings:
        query = (
            Q(hgnc_id=search_string) |
            Q(moleculealias__alias=search_string)
        )
        molecules = Molecule.objects.filter(query).distinct()

        search_results.append({'search_string': search_string, 'molecules': molecules})
    
    return search_results