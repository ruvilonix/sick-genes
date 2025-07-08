import zipfile
import xml.etree.ElementTree as ET
from django.db import transaction
from django.core.management.base import CommandError
from sickgenes.models import HmdbMetabolite, MetaboliteSynonym, SecondaryAccession

RELATED_MODELS = {
    'synonyms': {
        'model': MetaboliteSynonym,
        'child_tag': 'synonym',
        'value_field': 'value',
        'max_length': 255
    },
    'secondary_accessions': {
        'model': SecondaryAccession,
        'child_tag': 'accession',
        'value_field': 'value',
        'max_length': None
    },
}

def _get_field_value(element, tag, namespace, cast_type=str, max_len=None):
    """Helper to find text in an element, cast it, and check its length."""
    node = element.find(tag, namespace)
    if node is not None and node.text:
        value = node.text.strip()
        if max_len and len(value) > max_len:
            return None
        try:
            return cast_type(value)
        except (ValueError, TypeError):
            return None
    return None

@transaction.atomic
def update_hmdb_data(hmdb_data_path, hmdb_xml_name):
    """
    Updates HmdbMetabolite records and their related tables from a zipped XML source.
    """
    processed_count = 0
    namespace = {'hmdb': 'http://www.hmdb.ca'}
    metabolite_tag = f"{{{namespace['hmdb']}}}metabolite"

    try:
        with zipfile.ZipFile(hmdb_data_path, 'r') as zip_file:
            with zip_file.open(hmdb_xml_name) as xml_file:
                for event, elem in ET.iterparse(xml_file, events=("end",)):
                    if elem.tag == metabolite_tag:

                        primary_accession_element = elem.find('hmdb:accession', namespace)
                        if primary_accession_element is None or not primary_accession_element.text:
                            elem.clear()
                            continue
                        
                        primary_accession = primary_accession_element.text

                        # Map all single-value fields from the XML to the model
                        main_fields = {
                            'name': _get_field_value(elem, 'hmdb:name', namespace),
                            'cas_registry_number': _get_field_value(elem, 'hmdb:cas_registry_number', namespace),
                            'drugbank_id': _get_field_value(elem, 'hmdb:drugbank_id', namespace),
                            'foodb_id': _get_field_value(elem, 'hmdb:foodb_id', namespace),
                            'knapsack_id': _get_field_value(elem, 'hmdb:knapsack_id', namespace),
                            'biocyc_id': _get_field_value(elem, 'hmdb:biocyc_id', namespace),
                            'wikipedia_id': _get_field_value(elem, 'hmdb:wikipedia_id', namespace),
                            'iupac_name': _get_field_value(elem, 'hmdb:iupac_name', namespace, max_len=255),
                            'traditional_iupac': _get_field_value(elem, 'hmdb:traditional_iupac', namespace, max_len=255),
                            'bigg_id': _get_field_value(elem, 'hmdb:bigg_id', namespace, cast_type=int),
                            'pubchem_compound_id': _get_field_value(elem, 'hmdb:pubchem_compound_id', namespace, cast_type=int),
                            'chemspider_id': _get_field_value(elem, 'hmdb:chemspider_id', namespace, cast_type=int),
                            'chebi_id': _get_field_value(elem, 'hmdb:chebi_id', namespace, cast_type=int),
                        }
                        
                        metabolite_obj, _ = HmdbMetabolite.objects.update_or_create(
                            accession=primary_accession,
                            defaults=main_fields
                        )

                        for parent_tag, config in RELATED_MODELS.items():
                            parent_element = elem.find(f'hmdb:{parent_tag}', namespace)
                            if parent_element is not None:
                                model_class = config['model']
                                model_class.objects.filter(metabolite=metabolite_obj).delete()

                                items_to_create = []
                                for item in parent_element.findall(f"hmdb:{config['child_tag']}", namespace):
                                    if item.text:
                                        value = item.text.strip()
                                        if config['max_length'] and len(value) > config['max_length']:
                                            continue
                                        
                                        items_to_create.append(
                                            model_class(metabolite=metabolite_obj, **{config['value_field']: value})
                                        )
                                
                                if items_to_create:
                                    model_class.objects.bulk_create(items_to_create, ignore_conflicts=True)

                        processed_count += 1
                        elem.clear()

    except (zipfile.BadZipFile, KeyError, ET.ParseError) as e:
        raise CommandError(f'Failed to read or parse HMDB data: {e}')
    except Exception as e:
        raise CommandError(f'An unexpected error occurred while processing HMDB data: {e}')
    
    return processed_count