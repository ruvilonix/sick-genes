from django.core.management.base import BaseCommand
from sickgenes.models import Molecule, MoleculeAlias, HgncGene
import pandas as pd
from django.utils import timezone
from django.db import transaction
import os
import xml.etree.ElementTree as ET
from django.conf import settings
import pandas as pd
import zipfile
import requests
import json
from .helper_functions import get_json_from_source

BASE_DIR = settings.BASE_DIR

HGNC_DATA_PATH = 'https://storage.googleapis.com/public-download-files/hgnc/json/json/non_alt_loci_set.json'

HMDB_DATA_PATH = os.path.join(BASE_DIR, 'sickgenes/approved_data/hmdb_metabolites.zip')
HMDB_XML_NAME = 'hmdb_metabolites.xml'

# Small file for testing:
#HGNC_DATA_PATH = 'https://storage.googleapis.com/public-download-files/hgnc/json/json/locus_types/T_cell_receptor_gene.json'

# Small file for testing:
#HMDB_DATA_PATH = os.path.join(BASE_DIR, 'sickgenes/approved_data/urine_metabolites.zip')
#HMDB_XML_NAME = 'urine_metabolites.xml'

@transaction.atomic
def update_hgnc_data(hgnc_data_path):
    fields = [
        'symbol',
        'name'
        'entrez_id',
        'ensembl_gene_id',
        'vega_id',
        'ucsc_id',
        'ena',
        'uniprot_ids',
        'pubmed_id',
        'omim_id',
        'alias_symbol',
        'alias_name',
        'prev_symbol',
        'prev_name',
    ]

    datetime_updated = timezone.now()

    hgnc_json_genes = get_json_from_source(hgnc_data_path)['response']['docs']
    
    for item in hgnc_json_genes:
        field_values = {field: item[field] for field in fields if field in item}
        updated_values = field_values | {'datetime_updated': datetime_updated}

        obj, _ = HgncGene.objects.update_or_create(
            hgnc_id=item['hgnc_id'],
            defaults=updated_values,    
        )
    

class Command(BaseCommand):
    help = 'Updates Molecule and MoleculeAlias tables with HGNC data. Saves downloaded file to server to allow restoring old versions.'

    def add_arguments(self, parser):
        parser.add_argument('database', type=str, help="Which database to import: 'hgnc' or 'hmdb'")
        parser.add_argument('-t', '--test', action='store_true', help="Import data from small test files. Used for testing.")

    def handle(self, *args, **kwargs):

        if kwargs['test']:
            hgnc_data_path = os.path.join(BASE_DIR, 'sickgenes/approved_data/sample_data/sample_hgnc.json')
        else:
            hgnc_data_path = HGNC_DATA_PATH
        
        if kwargs['database'] == 'hgnc':
            update_hgnc_data(hgnc_data_path)
            self.stdout.write(self.style.SUCCESS('HGNC data successfully imported from JSON'))