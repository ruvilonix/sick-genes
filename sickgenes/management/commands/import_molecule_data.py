from django.core.management.base import BaseCommand, CommandError
from sickgenes.models import HgncGene, HmdbMetabolite
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

HMDB_DATA_PATH = os.path.join(BASE_DIR, 'approved_data/hmdb_metabolites.zip')
HMDB_XML_NAME = 'hmdb_metabolites.xml'

# Small file for testing:
#HGNC_DATA_PATH = 'https://storage.googleapis.com/public-download-files/hgnc/json/json/locus_types/T_cell_receptor_gene.json'

# Small file for testing:
#HMDB_DATA_PATH = os.path.join(BASE_DIR, 'approved_data/urine_metabolites.zip')
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
        'ena', 'uniprot_ids', 'omim_id', 'alias_symbol',
        'alias_name', 'prev_symbol', 'prev_name']

    try:
        hgnc_data = get_json_from_source(hgnc_data_path)
        hgnc_genes = hgnc_data['response']['docs']
    except (KeyError, TypeError) as e:
        raise CommandError(f'Invalid JSON structure in HGNC data: {e}')
    except Exception as e:
        raise CommandError(f'Failed to retrieve HGNC data: {e}')
    
    processed_count = 0
    
    for gene_data in hgnc_genes:
        try:
            field_values = {
                field: gene_data[field] 
                for field in expected_fields 
                if field in gene_data
            }

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

@transaction.atomic
def update_hmdb_data(hmdb_data_path, hmdb_xml_name):
    """
    Updates HmdbMetabolite records from a zipped XML source.

    This function is memory-efficient, using iterparse to process the
    XML one element at a time.

    Args:
        hmdb_data_path: Path to the zipped HMDB XML data.
        hmdb_xml_name: Filename of the XML file within the zip archive.

    Returns:
        int: The number of metabolite records processed.
    
    Raises:
        CommandError: If the file cannot be read, parsed, or if the
                      data structure is invalid.
    """
    expected_fields = [
        'accession', 'name', 'cas_registry_number', 'drugbank_id', 'foodb_id', 
        'knapsack_id', 'biocyc_id', 'wikipedia_id', 'bigg_id', 
        'pubchem_compound_id', 'chemspider_id', 'chebi_id', 
        'secondary_accessions', 'synonyms', 'iupac_name', 'traditional_iupac'
    ]
    
    # Maps array fields to the name of their child elements in the XML
    child_names_for_arrays = {
        'secondary_accessions': 'accession', 
        'synonyms': 'synonym'
    }

    processed_count = 0
    namespace = {'hmdb': 'http://www.hmdb.ca'}
    metabolite_tag = f"{{{namespace['hmdb']}}}metabolite"

    try:
        with zipfile.ZipFile(hmdb_data_path, 'r') as zip_file:
            with zip_file.open(hmdb_xml_name) as xml_file:
                # Use iterparse for memory-efficient parsing. We only care about the
                # 'end' event for each 'metabolite' element.
                for event, elem in ET.iterparse(xml_file, events=("end",)):
                    if elem.tag == metabolite_tag:
                        field_values = {}

                        # Extract data for all expected fields from the XML element
                        for field in expected_fields:
                            # Handle array fields (e.g., synonyms)
                            if field in child_names_for_arrays:
                                values = []
                                parent_element = elem.find(f"hmdb:{field}", namespace)
                                if parent_element is not None:
                                    child_tag = child_names_for_arrays[field]
                                    for child in parent_element.findall(f"hmdb:{child_tag}", namespace):
                                        if child.text:
                                            values.append(child.text) if len(child.text) <= 255 else None
                                field_values[field] = values
                            # Handle simple text fields
                            else:
                                child = elem.find(f"hmdb:{field}", namespace)
                                if child is not None and child.text:
                                    field_values[field] = child.text if len(child.text) <= 255 else None

                        # The primary accession number is required to create a record
                        primary_accession = field_values.get('accession')
                        if not primary_accession:
                            continue
                        
                        # Use the extracted accession as the primary key for lookup
                        # and update the record with all other extracted values.
                        obj, _ = HmdbMetabolite.objects.update_or_create(
                            accession=primary_accession,
                            defaults=field_values
                        )
                        processed_count += 1
                        
                        # Clear the processed element from memory to keep usage low
                        elem.clear()

    except FileNotFoundError:
        raise CommandError(f'HMDB data file not found at: {hmdb_data_path}')
    except (zipfile.BadZipFile, KeyError) as e:
        raise CommandError(f"Error reading zip or XML file '{hmdb_xml_name}': {e}")
    except ET.ParseError as e:
        raise CommandError(f'Failed to parse XML file: {e}')
    except Exception as e:
        # Catch any other unexpected errors during processing
        raise CommandError(f'An error occurred while processing HMDB data: {e}')

    return processed_count
    

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
                    'approved_data/sample_data/sample_hgnc.json',
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
            
        elif database_type == 'hmdb':
            if use_test_data:
                data_path = os.path.join(
                    BASE_DIR,
                    'approved_data/sample_data/sample_hmdb.zip',
                )
                if not os.path.exists(data_path):
                    raise CommandError(f"Test data file not found: {data_path}")
            else:
                data_path = HMDB_DATA_PATH

            try:
                processed_count = update_hmdb_data(data_path, HMDB_XML_NAME)

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