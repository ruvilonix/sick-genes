from django.db.models import Q
from django.db import models

from django.db import models
from django.db.models import Q

class BaseMoleculeManager(models.Manager):
    """
    Generic manager to find items by searching across a variety of fields.
    
    Subclasses must define lists of field names to be searched, e.g.:
    - plain_str_fields
    - array_str_fields
    - plain_int_fields
    - array_int_fields
    """
    plain_str_fields = []
    array_str_fields = []
    plain_int_fields = []
    array_int_fields = []

    def _build_search_query(self, search_string):
        """
        Builds a Q object by searching the search_string against the
        fields defined in the manager's class attributes.
        """
        query = Q()

        # Plain string fields use case-insensitive exact match
        for field in self.plain_str_fields:
            query |= Q(**{f"{field}__iexact": search_string})

        # Array of string fields use case-insensitive contains match
        for field in self.array_str_fields:
            query |= Q(**{f"{field}__icontains": search_string})

        # For integer fields, we first try to convert the search string
        try:
            search_int = int(search_string)
            for field in self.plain_int_fields:
                query |= Q(**{f"{field}": search_int})
            for field in self.array_int_fields:
                query |= Q(**{f"{field}__contains": [search_int]})
        except ValueError:
            # If search_string is not a valid integer, just skip the integer fields
            pass

        return query

    def find_matching_items(self, search_strings):
        """
        Takes a list of strings and returns a dictionary with search results.
        (This method remains unchanged)
        """
        search_results = {
            'no_matches': [],
            'one_match': [],
            'multiple_matches': [],
        }

        for search_string in search_strings:
            query = self._build_search_query(search_string)
            items = self.filter(query).distinct()

            count = items.count()
            if count == 0:
                search_results['no_matches'].append(search_string)
            elif count == 1:
                search_results['one_match'].append({'search_string': search_string, 'item': items.first()})
            else:
                search_results['multiple_matches'].append({'search_string': search_string, 'items': list(items)})

        return search_results

class HgncGeneManager(BaseMoleculeManager):
    """ Manager for HgncGene, defines searchable fields. """
    plain_str_fields = [
        'hgnc_id', 'symbol', 'name', 'entrez_id', 'ensembl_gene_id', 'vega_id', 'ucsc_id'
    ]
    array_str_fields = [
        'ena', 'uniprot_ids', 'alias_symbol', 'alias_name', 'prev_symbol', 'prev_name'
    ]
    array_int_fields = ['omim_id']


class HmdbMetaboliteManager(BaseMoleculeManager):
    """ Manager for HmdbMetabolite, defines searchable fields. """
    plain_str_fields = [
        'accession', 'name', 'cas_registry_number', 'drugbank_id', 'foodb_id',
        'knapsack_id', 'biocyc_id', 'wikipedia_id', 'iupac_name', 'traditional_iupac'
    ]
    array_str_fields = ['secondary_accessions', 'synonyms']
    plain_int_fields = [
        'bigg_id', 'pubchem_compound_id', 'chemspider_id', 'chebi_id'
    ]