from django.core.management.base import BaseCommand
from sickgenes.models import Molecule, MoleculeAlias
import pandas as pd
from django.utils import timezone
from django.db import transaction

import pandas as pd
pd.set_option('display.max_columns', None)

HGNC_DATA_URL = 'https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/non_alt_loci_set.txt'

# Small file for testing:
#HGNC_DATA_URL = 'https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/locus_types/T_cell_receptor_pseudogene.txt'

@transaction.atomic
def update_hgnc_data(hgnc_data_url):
    update_datetime = timezone.now()

    hgnc_df = pd.read_csv(
        hgnc_data_url, 
        usecols=['hgnc_id', 'symbol', 'name', 'alias_symbol', 'prev_symbol'], 
        dtype={'hgnc_id': str, 'symbol': str, 'name': str, 'alias_symbol': str, 'prev_symbol': str},
        sep='\t',
    )    
    hgnc_df = hgnc_df[['hgnc_id', 'symbol', 'name', 'alias_symbol', 'prev_symbol']].fillna(value='')

    genes_to_insert = []

    MoleculeAlias.objects.filter(molecule__type=Molecule.MoleculeType.GENE).delete()
    gene_aliases_to_create = []
    
    for i, row in hgnc_df.iterrows():
        updated_values = {
            'hgnc_symbol': row['symbol'],
            'hgnc_name': row['name'],
            'type': Molecule.MoleculeType.GENE,
            'datetime_updated': update_datetime,
        }

        obj, _ = Molecule.objects.update_or_create(
            hgnc_id=row['hgnc_id'],
            defaults=updated_values,    
        )

        alias_symbols = row['alias_symbol'].split('|') if row['alias_symbol'] != '' else []
        alias_symbols += row['prev_symbol'].split('|') if row['prev_symbol'] != '' else []
        alias_symbols = set(alias_symbols)
        
        for alias_symbol in alias_symbols:
            gene_aliases_to_create.append(MoleculeAlias(
                molecule=obj,
                symbol=alias_symbol,
            ))

    MoleculeAlias.objects.bulk_create(gene_aliases_to_create)
        
    

class Command(BaseCommand):
    help = 'Updates Molecule and MoleculeAlias tables with HGNC data. Saves downloaded file to server to allow restoring old versions.'

    def handle(self, *args, **kwargs):
        
        update_hgnc_data(HGNC_DATA_URL)
