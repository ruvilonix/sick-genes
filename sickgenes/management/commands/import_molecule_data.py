import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sickgenes.importers import update_hgnc_data, update_hmdb_data

BASE_DIR = settings.BASE_DIR

HGNC_DATA_PATH = 'https://storage.googleapis.com/public-download-files/hgnc/json/json/non_alt_loci_set.json'

HMDB_DATA_PATH = os.path.join(BASE_DIR, 'approved_data/hmdb_metabolites.zip')
HMDB_XML_NAME = 'hmdb_metabolites.xml'

    
class Command(BaseCommand):
    help = 'Imports molecular data from specified database'

    def add_arguments(self, parser):
        parser.add_argument(
            'database', 
            type=str, 
            choices=['hgnc', 'hmdb'],
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
        

        if database_type == 'hgnc':
            if use_test_data:
                data_path = os.path.join(
                    BASE_DIR,
                    'sample_data/sample_hgnc.json',
                )
                if not os.path.exists(data_path):
                    raise CommandError(f"Test data file not found: {data_path}")
            else:
                data_path = HGNC_DATA_PATH

            try:
                processed_count = update_hgnc_data(data_path, self.stdout)

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
            
        elif database_type == 'hmdb':
            if use_test_data:
                data_path = os.path.join(
                    BASE_DIR,
                    'sample_data/sample_hmdb.zip',
                )
                if not os.path.exists(data_path):
                    raise CommandError(f"Test data file not found: {data_path}")
            else:
                data_path = HMDB_DATA_PATH

            try:
                processed_count = update_hmdb_data(data_path, HMDB_XML_NAME, self.stdout)

                self.stdout.write(
                    self.style.SUCCESS(
                        f'HMDB data successfully imported. '
                        f'Processed {processed_count} records.'
                    )
                )
            except CommandError:
                raise
            except Exception as e:
                raise CommandError(f'Unexpected error during HMDB import: {e}')
            

