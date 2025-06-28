from django.db.models import Manager, Q
from django.db import models

class MoleculeManager(models.Manager):
    def find_matching_molecules(self, search_strings):
        search_results = []

        for search_string in search_strings:
            query = (
                Q(hgnc_id__iexact=search_string) |
                Q(moleculealias__alias__iexact=search_string)
            )
            molecules = self.filter(query).distinct()
            search_results.append({'search_string': search_string, 'molecules': molecules})

        return search_results