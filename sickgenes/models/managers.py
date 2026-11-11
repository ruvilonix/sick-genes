from collections import defaultdict
from django.db import connection, models
from django.db.models.functions import Upper
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

    @staticmethod
    def _upper_in_database(strings):
        """
        Upper-cases strings with Postgres rather than Python, so they compare
        exactly like UPPER() on the database side. The two differ for a few
        characters, e.g. the "ﬁ" ligature.
        """
        if not strings:
            return []
        with connection.cursor() as cursor:
            cursor.execute("SELECT s, UPPER(s) FROM unnest(%s::text[]) AS s", [strings])
            return cursor.fetchall()

    def find_matching_items(self, search_strings):
        """
        Takes a list of strings and returns a dictionary with search results.

        Runs one query per searchable field for all strings together, so the
        number of queries doesn't grow with the number of search strings.
        """
        search_strings = list(search_strings)
        app_label = self.model._meta.app_label

        # Search strings keyed the way database values are compared to them:
        # upper-cased for case-insensitive text fields, as numbers for integer fields
        strings_by_upper = defaultdict(list)
        strings_by_int = defaultdict(list)
        for search_string, upper_string in self._upper_in_database(search_strings):
            strings_by_upper[upper_string].append(search_string)
        for search_string in search_strings:
            try:
                strings_by_int[int(search_string)].append(search_string)
            except ValueError:
                pass

        matching_ids = {search_string: set() for search_string in search_strings}

        def upper_matches(queryset, field, pk_field):
            # Case-insensitive match as UPPER(field) IN (...), which uses the
            # UPPER indexes and stays fast for long lists
            return queryset.annotate(upper_value=Upper(field)).filter(
                upper_value__in=strings_by_upper
            ).values_list('upper_value', pk_field)

        def add_text_matches(rows):
            for upper_value, pk in rows:
                for search_string in strings_by_upper.get(upper_value, []):
                    matching_ids[search_string].add(pk)

        def add_int_matches(rows):
            for value, pk in rows:
                for search_string in strings_by_int.get(value, []):
                    matching_ids[search_string].add(pk)

        if search_strings:
            for field in self.str_fields:
                add_text_matches(upper_matches(self, field, 'pk'))

            for related_field, model_name in self.related_models_to_search.get('str_fields', {}).items():
                model = apps.get_model(app_label=app_label, model_name=model_name)
                add_text_matches(upper_matches(model.objects, 'value', self.related_fk_name))

        if strings_by_int:
            for field in self.int_fields:
                add_int_matches(
                    self.filter(**{f"{field}__in": strings_by_int}).values_list(field, 'pk')
                )

            for related_field, model_name in self.related_models_to_search.get('int_fields', {}).items():
                model = apps.get_model(app_label=app_label, model_name=model_name)
                add_int_matches(
                    model.objects.filter(value__in=strings_by_int).values_list('value', self.related_fk_name)
                )

        # Load all matched items in one query
        all_ids = set().union(*matching_ids.values())
        items_by_id = {item.pk: item for item in self.filter(pk__in=all_ids)} if all_ids else {}

        search_results = {
            'no_matches': [],
            'one_match': [],
            'multiple_matches': [],
        }

        # Position of each item in the model's default ordering
        item_order = {pk: position for position, pk in enumerate(items_by_id)}

        for search_string in search_strings:
            # Keep the model's default ordering, as a filter() query would
            pks = sorted(matching_ids[search_string], key=item_order.get)
            items = [items_by_id[pk] for pk in pks]

            if not items:
                search_results['no_matches'].append(search_string)
            elif len(items) == 1:
                search_results['one_match'].append({'search_string': search_string, 'item': items[0]})
            else:
                search_results['multiple_matches'].append({'search_string': search_string, 'items': items})

        return search_results


class HgncGeneManager(BaseMoleculeManager):
    """ Manager for HgncGene, defines searchable fields and models. """
    str_fields = [
        'symbol', 'name', 'ensembl_gene_id', 'vega_id', 'ucsc_id',
    ]
    # Numeric columns are matched as numbers so their indexes can be used
    int_fields = [
        'hgnc_id', 'entrez_id',
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