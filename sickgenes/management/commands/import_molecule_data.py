import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sickgenes.importers import update_hgnc_data

BASE_DIR = settings.BASE_DIR

HGNC_DATA_PATHS = [
    'https://storage.googleapis.com/public-download-files/hgnc/json/json/alternative_loci_set.json',
    'https://storage.googleapis.com/public-download-files/hgnc/json/json/non_alt_loci_set.json',
]


class Command(BaseCommand):
    help = 'Imports gene data from HGNC'

    def add_arguments(self, parser):
        parser.add_argument(
            'database', 
            type=str, 
            # Only HGNC is left; the argument stays so existing commands keep working
            choices=['hgnc'],
            help="Which database to import from"
        )
        
        parser.add_argument(
            '-t', '--test', 
            action='store_true', 
            help="Import data from small test files. Used for testing."
           )

    def handle(self, *args, **kwargs):
        if kwargs['test']:
            data_path = os.path.join(BASE_DIR, 'sample_data/sample_hgnc.json')
            if not os.path.exists(data_path):
                raise CommandError(f"Test data file not found: {data_path}")
            data_paths = [data_path]
        else:
            data_paths = HGNC_DATA_PATHS

        # Download and file errors already come back as CommandError; anything
        # else is a bug, so let it show its full traceback
        result = update_hgnc_data(data_paths, self.stdout)
        self.stdout.write(
            self.style.SUCCESS(
                f'HGNC data successfully imported. '
                f'Processed {result.processed_count} records.'
            )
        )
        for line in result.report_lines():
            self.stdout.write(line)
