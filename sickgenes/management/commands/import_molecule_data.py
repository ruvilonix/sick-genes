from django.core.management.base import BaseCommand, CommandError
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
    """
    Updates HgncGene records from JSON data source.
    
    Args:
        hgnc_data_path: Path or URL to HGNC JSON data
        
    Returns:
        int: Number of records processed
    """

    expected_fields = ['symbol',
        'name', 'entrez_id', 'ensembl_gene_id', 'vega_id', 'ucsc_id',
        'ena', 'uniprot_ids', 'pubmed_id', 'omim_id', 'alias_symbol',
        'alias_name', 'prev_symbol', 'prev_name']

    try:
        hgnc_data = get_json_from_source(hgnc_data_path)
        hgnc_genes = hgnc_data['response']['docs']
    except (KeyError, TypeError) as e:
        raise CommandError(f'Invalid JSON structure in HGNC data: {e}')
    except Exception as e:
        raise CommandError(f'Failed to retrieve HGNC data: {e}')
    
    datetime_updated = timezone.now()
    processed_count = 0
    
    for gene_data in hgnc_genes:
        try:
            field_values = {
                field: gene_data[field] 
                for field in expected_fields 
                if field in gene_data
            }

            field_values['datetime_updated'] = datetime_updated

            obj, _ = HgncGene.objects.update_or_create(
                hgnc_id=gene_data['hgnc_id'],
                defaults=field_values,    
            )

            processed_count += 1

        except KeyError as e:
            raise CommandError(f"Missing required field in gene data: {e}")
        except Exception as e:
            raise CommandError(f"Error processing gene {gene_data.get('hgnc_id', 'unknown')}: {e}")
    
    return processed_count

class Command(BaseCommand):
    help = 'Imports molecular data from specified database'

    def add_arguments(self, parser):
        parser.add_argument(
            'database', 
            type=str, 
            choices=['hgnc'],
            help="Which database to import from"
        )
        
        parser.add_argument(
            '-t', '--test', 
            action='store_true', 
            help="Import data from small test files. Used for testing."
           )

    def handle(self, *args, **kwargs):
        database_type = kwargs['database']
        use_test_data = kwargs['test']
        
        if kwargs['database'] == 'hgnc':

            if database_type == 'hgnc':
                if use_test_data:
                    data_path = os.path.join(
                        BASE_DIR,
                        'sickgenes/approved_data/sample_data/sample_hgnc.json',
                    )
                    if not os.path.exists(data_path):
                        raise CommandError(f"Test data file not found: {data_path}")
                else:
                    data_path = HGNC_DATA_PATH

                try:
                    processed_count = update_hgnc_data(data_path)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'HGNC data successfully imported. '
                            f'Processed {processed_count} records.'
                        )
                    )
                except CommandError:
                    raise
                except Exception as e:
                    raise CommandError(f'Unexpected error during HGNC import: {e}')