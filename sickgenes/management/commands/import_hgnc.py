from django.core.management.base import BaseCommand
from sickgenes.models import Molecule, MoleculeAlias
import pandas as pd
from django.utils import timezone
from django.db import transaction
import os
import xml.etree.ElementTree as ET
from django.conf import settings
import pandas as pd
import zipfile


BASE_DIR = settings.BASE_DIR

HGNC_DATA_PATH = 'https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/non_alt_loci_set.txt'
HMDB_DATA_PATH = os.path.join(BASE_DIR, 'sickgenes/approved_data/hmdb_metabolites.zip')
HMDB_XML_NAME = 'hmdb_metabolites.xml'

# Small file for testing:
#HGNC_DATA_URL = 'https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/locus_types/T_cell_receptor_pseudogene.txt'

# Small file for testing:
#HMDB_DATA_PATH = os.path.join(BASE_DIR, 'sickgenes/approved_data/urine_metabolites.zip')
#HMDB_XML_NAME = 'urine_metabolites.xml'

@transaction.atomic
def update_hgnc_data(hgnc_data_path):
    update_datetime = timezone.now()

    hgnc_df = pd.read_csv(
        hgnc_data_path, 
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
                alias=alias_symbol,
            ))

    MoleculeAlias.objects.bulk_create(gene_aliases_to_create)

        

@transaction.atomic
def update_hmdb_data(hmdb_data_path):
    update_datetime = timezone.now()

    genes_to_insert = []

    MoleculeAlias.objects.filter(molecule__type=Molecule.MoleculeType.METABOLITE).delete()

    x = 0
    namespace = {'ns0': 'http://www.hmdb.ca'}

    def create_list_from_xml_element(element, child_name, namespace):
        child = element.find(f'ns0:{child_name}', namespace)

        children = []
        for inner_child in child:
            children.append(inner_child.text)

        return children

    # Open the zip file and get the XML file from inside it
    with zipfile.ZipFile(hmdb_data_path, 'r') as zip_file:
        with zip_file.open(HMDB_XML_NAME) as xml_file:
            for event, elem in ET.iterparse(xml_file, events=("start", "end")):
                if event == 'end' and elem.tag.endswith('metabolite'):
                    updated_values = {
                        'hmdb_name': elem.find('ns0:name', namespace).text,
                        'type': Molecule.MoleculeType.METABOLITE,
                        'datetime_updated': update_datetime,
                    }

                    obj, _ = Molecule.objects.update_or_create(
                        hmdb_accession=elem.find('ns0:accession', namespace).text,
                        defaults=updated_values,   
                    )

                    alias_symbols = create_list_from_xml_element(elem, 'secondary_accessions', namespace)
                    alias_symbols += create_list_from_xml_element(elem, 'synonyms', namespace)
                    alias_symbols = set(alias_symbols)
                    
                    metabolite_aliases_to_create = []
                    for alias_symbol in alias_symbols:
                        metabolite_aliases_to_create.append(MoleculeAlias(
                            molecule=obj,
                            alias=alias_symbol,
                        ))

                    MoleculeAlias.objects.bulk_create(metabolite_aliases_to_create)

                    # Clear the processed element and its children
                    elem.clear()
    

class Command(BaseCommand):
    help = 'Updates Molecule and MoleculeAlias tables with HGNC data. Saves downloaded file to server to allow restoring old versions.'

    def add_arguments(self, parser):
        parser.add_argument('database', type=str, help="Which database to import: 'hgnc' or 'hmdb'")
        parser.add_argument('-t', '--test', action='store_true', help="Import data from small test files. Used for testing.")

    def handle(self, *args, **kwargs):

        if kwargs['test']:
            hgnc_data_path = os.path.join(BASE_DIR, 'sickgenes/approved_data/sample_data/sample_hgnc.txt')
            hmdb_data_path = os.path.join(BASE_DIR, 'sickgenes/approved_data/sample_data/sample_hmdb.zip')
        else:
            hgnc_data_path = HGNC_DATA_PATH
            hmdb_data_path = HMDB_DATA_PATH
        
        if kwargs['database'] == 'hgnc':
            update_hgnc_data(hgnc_data_path)
            self.stdout.write(self.style.SUCCESS('HGNC data successfully imported'))

        elif kwargs['database'] == 'hmdb':
            update_hmdb_data(hmdb_data_path)
            self.stdout.write(self.style.SUCCESS('HMDB data successfully imported'))
