from django.db import models
from django.apps import apps

class BaseMoleculeManager(models.Manager):
    """
    Generic manager to find items by searching across a variety of fields.
    """
    # A mapping of related models to the field we want to search on them.
    str_fields = []
    int_fields = []
    related_models_to_search = {}
    related_fk_name = None

    def find_matching_items(self, search_strings):
        """
        Takes a list of strings and returns a dictionary with search results.
        """
        search_results = {
            'no_matches': [],
            'one_match': [],
            'multiple_matches': [],
        }

        app_label = self.model._meta.app_label

        for search_string in search_strings:
            matching_ids = set()

            for field in self.str_fields:
                qs = self.filter(**{f"{field}__iexact": search_string}).values_list('pk', flat=True)
                if qs.exists():
                    matching_ids.update(qs)

            try:
                search_int = int(search_string)
                for field in self.int_fields:
                    qs = self.filter(**{f"{field}": search_int}).values_list('pk', flat=True)
                    if qs.exists():
                        matching_ids.update(qs)
            except ValueError:
                pass
            
            # String searches on related models
            for related_field, model_name in self.related_models_to_search.get('str_fields', {}).items():
                # Resolve the model class at runtime instead of import time
                model = apps.get_model(app_label=app_label, model_name=model_name)
                related_ids = model.objects.filter(
                    value__iexact=search_string
                ).values_list(self.related_fk_name, flat=True)
                matching_ids.update(related_ids)

            # Integer searches on related models
            try:
                search_int = int(search_string)
                for related_field, model_name in self.related_models_to_search.get('int_fields', {}).items():
                    # Resolve the model class at runtime
                    model = apps.get_model(app_label=app_label, model_name=model_name)
                    related_ids = model.objects.filter(
                        value=search_int
                    ).values_list(self.related_fk_name, flat=True)
                    matching_ids.update(related_ids)
            except ValueError:
                pass

            if not matching_ids:
                search_results['no_matches'].append(search_string)
                continue
            
            items = list(self.filter(pk__in=matching_ids))
            count = len(items)

            if count == 1:
                search_results['one_match'].append({'search_string': search_string, 'item': items[0]})
            else:
                search_results['multiple_matches'].append({'search_string': search_string, 'items': items})

        return search_results


class HgncGeneManager(BaseMoleculeManager):
    """ Manager for HgncGene, defines searchable fields and models. """
    str_fields = [
        'hgnc_id', 'symbol', 'name', 'entrez_id', 'ensembl_gene_id', 'vega_id', 'ucsc_id',
    ]

    related_fk_name = 'gene_id'

    related_models_to_search = {
        'str_fields': {
            'ena__value': 'Ena',
            'uniprotid__value': 'UniprotId',
            'aliassymbol__value': 'AliasSymbol',
            'aliasname__value': 'AliasName',
            'prevsymbol__value': 'PrevSymbol',
            'prevname__value': 'PrevName',
        },
        'int_fields': {
            'omimid__value': 'OmimId',
        }
    }


class HmdbMetaboliteManager(BaseMoleculeManager):
    """ Manager for HmdbMetabolite, defines searchable fields. """
    str_fields = [
        'accession', 'name', 'cas_registry_number', 'drugbank_id', 'foodb_id',
        'knapsack_id', 'biocyc_id', 'wikipedia_id', 'iupac_name', 'traditional_iupac'
    ]
    int_fields = [
        'bigg_id', 'pubchem_compound_id', 'chemspider_id', 'chebi_id'
    ]

    related_fk_name = 'metabolite_id'

    related_models_to_search = {
        'str_fields': {
            'metabolitesynonym__value': 'MetaboliteSynonym',
            'secondaryaccession__value': 'SecondaryAccession',
        }
    }