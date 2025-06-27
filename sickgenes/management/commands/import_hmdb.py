from django.core.management.base import BaseCommand
from sickgenes.models import Molecule, MoleculeAlias
import pandas as pd
from django.utils import timezone
from django.db import transaction
import xml.etree.ElementTree as ET
from django.conf import settings
import json
import os
import zipfile

BASE_DIR = settings.BASE_DIR

HMDB_DATA_PATH = os.path.join(BASE_DIR, 'sickgenes/approved_data/hmdb_metabolites.zip')
HMDB_XML_NAME = 'hmdb_metabolites.xml'

# Small file for testing:
#HMDB_DATA_PATH = os.path.join(BASE_DIR, 'sickgenes/approved_data/urine_metabolites.zip')
#HMDB_XML_NAME = 'urine_metabolites.xml'

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
    help = 'Updates Gene and GeneAlias tables with HGNC data. Saves downloaded file to server to allow restoring old versions.'

    def handle(self, *args, **kwargs):
        
        update_hmdb_data(HMDB_DATA_PATH)
