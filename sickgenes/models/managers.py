from django.db.models import Q
from django.db import models

from django.db import models
from django.db.models import Q

class BaseMoleculeManager(models.Manager):
    """
    Generic manager to find items by searching across a variety of fields.
    
    Subclasses must define lists of field names to be searched, e.g.:
    - str_fields
    - int_fields
    """
    str_fields = []
    int_fields = []

    def _build_search_query(self, search_string):
        """
        Builds a Q object by searching the search_string against the
        fields defined in the manager's class attributes.
        """
        query = Q()

        for field in self.str_fields:
            query |= Q(**{f"{field}__iexact": search_string})

        try:
            search_int = int(search_string)
            for field in self.int_fields:
                query |= Q(**{f"{field}": search_int})
        except ValueError:
            pass

        return query

    def find_matching_items(self, search_strings):
        """
        Takes a list of strings and returns a dictionary with search results.
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
    str_fields = [
        'hgnc_id', 'symbol', 'name', 'entrez_id', 'ensembl_gene_id', 'vega_id', 'ucsc_id',
        'ena__value', 'uniprotid__value', 'aliassymbol__value', 'aliasname__value',
        'prevsymbol__value', 'prevname__value'
    ]
    int_fields = ['omimid__value']


class HmdbMetaboliteManager(BaseMoleculeManager):
    """ Manager for HmdbMetabolite, defines searchable fields. """
    str_fields = [
        'accession', 'name', 'cas_registry_number', 'drugbank_id', 'foodb_id',
        'knapsack_id', 'biocyc_id', 'wikipedia_id', 'iupac_name', 'traditional_iupac',
        'secondary_accessions__value', 'synonyms__value'
    ]
    int_fields = [
        'bigg_id', 'pubchem_compound_id', 'chemspider_id', 'chebi_id'
    ]