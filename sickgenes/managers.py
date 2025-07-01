from django.db.models import Q
from django.db import models

class HgncGeneManager(models.Manager):
    def _build_search_query(self, search_string):
        """
        Build query for searching all fields of HgncGene

        Args: 
            search_string: The string to search with

        Returns:
            Q object representing the search
        """

        plain_str_fields = ['hgnc_id', 'symbol', 'name', 'entrez_id', 
                         'ensembl_gene_id', 'vega_id', 'ucsc_id']
        array_str_fields = ['ena', 'uniprot_ids', 'alias_symbol', 
                            'alias_name', 'prev_symbol', 'prev_name']
        array_int_fields = ['pubmed_id', 'omim_id']

        query = Q()
        for plain_field in plain_str_fields:
            query |= Q(**{f"{plain_field}__iexact": search_string})

        for array_field in array_str_fields:
            query |= Q(**{f"{array_field}__contains": [search_string]})

        try:
            search_string = int(search_string)
            for array_field in array_int_fields:
                query |= Q(**{f"{array_field}__contains": [int(search_string)]})
        except ValueError:
            pass

        return query
    
    def find_matching_items(self, search_strings):
        """
        Takes list of strings to search on and returns dictionary with search results.
        
        Args:
            search_strings: List of strings to search on

        Returns:
            Dictionary in the format
                {
                    "no_matches": [<search string one>], 
                    "one_match": {
                        "search_string": <search string two, 
                        "item": obj1
                    },
                    "multiple_matches": {
                        "search_string": <search string three, 
                        "items": [obj1, obj2]
                    }
                }
        """
        search_results = {
            'no_matches': [],
            'one_match': [],
            'multiple_matches': [],
        }

        for search_string in search_strings:
            query = self._build_search_query(search_string)
            items = self.filter(query).distinct()
            
            if (len(items) == 0):
                search_results['no_matches'].append(search_string)
            elif (len(items) == 1):
                search_results['one_match'].append({'search_string': search_string, 'item': items[0]})
            elif (len(items) > 1):
                search_results['multiple_matches'].append({'search_string': search_string, 'items': items})

        return search_results