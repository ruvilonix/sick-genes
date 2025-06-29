from django.db.models import Q
from django.db import models

class MoleculeManager(models.Manager):
    def _build_search_query(self, search_string, molecule_types):
        search_fields = [
            'hgnc_id',
            'hgnc_symbol',
            'hgnc_name',
            'hmdb_accession',
            'hmdb_name',
            'moleculealias__alias',
        ]

        query = Q()
        for search_field in search_fields:
            query |= Q(**{f"{search_field}__iexact": search_string})

        return query & Q(type__in=molecule_types)
    
    def _categorize_search_results(self, search_results):
        categorized_results = {
            'no_matches': [],
            'one_match': [],
            'multiple_matches': [],
        }

        for result in search_results:
            n_results = len(result['molecules'])
            if n_results == 0:
                categorized_results['no_matches'].append(result)
            elif n_results == 1:
                categorized_results['one_match'].append(result)
            elif n_results > 1:
                categorized_results['multiple_matches'].append(result)

        return categorized_results
    
    def find_matching_molecules(self, search_strings, molecule_types):
        """Takes list of strings to search on and list of molecule types (e.g. Molecule.MoleculeType.GENE) to search"""
        search_results = []

        for search_string in search_strings:
            query = self._build_search_query(search_string, molecule_types)

            molecules = self.filter(query).distinct()
            search_results.append({'search_string': search_string, 'molecules': molecules})

        categorized_results = self._categorize_search_results(search_results)

        return categorized_results