from django.db import transaction
from django.core.management.base import CommandError
from sickgenes.models import StringProtein, StringInteraction, HgncGene
from django.conf import settings
import os
import gzip

BASE_DIR = settings.BASE_DIR

SAMPLE_STRING_ALIAS_PATH = os.path.join(BASE_DIR, 'sample_data/sample_9606.protein.aliases.v12.0.txt.gz')
STRING_ALIAS_PATH = os.path.join(BASE_DIR, 'approved_data/9606.protein.aliases.v12.0.txt.gz')

SAMPLE_STRING_INTERACTION_PATH = os.path.join(BASE_DIR, 'sample_data/sample_9606.protein.links.v12.0.txt.gz')
STRING_INTERACTION_PATH = os.path.join(BASE_DIR, 'approved_data/9606.protein.links.v12.0.txt.gz')

def process_string_aliases(file_path, stdout):
    """
    Process STRING alias file and create StringProtein records in batches.
    """
    if not os.path.exists(file_path):
        raise CommandError(f'STRING alias file not found at: {file_path}')
    
    created_count = 0
    error_count = 0
    processed_count = 0
    batch_size = 1000
    batch_data = []
    
    StringProtein.objects.all().delete()
    
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('\t')
                
                if len(parts) >= 3:
                    string_protein_id = parts[0]
                    alias = parts[1]
                    source = parts[2]
                    
                    if source == 'Ensembl_HGNC_hgnc_id':
                        if string_protein_id.startswith('9606.'):
                            protein_id = string_protein_id[5:]
                        else:
                            protein_id = string_protein_id
                        
                        hgnc_id = alias
                        
                        try:
                            hgnc_gene = HgncGene.objects.get(hgnc_id=hgnc_id)
                            
                            batch_data.append(StringProtein(
                                protein_id=protein_id,
                                hgnc_id=hgnc_id,
                                hgnc_gene=hgnc_gene
                            ))
                            
                            if len(batch_data) >= batch_size:
                                StringProtein.objects.bulk_create(batch_data, ignore_conflicts=True)
                                created_count += len(batch_data)
                                batch_data = []
                                
                        except HgncGene.DoesNotExist:
                            if stdout:
                                stdout.write(f"Warning: HgncGene with ID {hgnc_id} not found for protein {protein_id}")
                            error_count += 1
                            continue
                        except Exception as e:
                            if stdout:
                                stdout.write(f"Error processing alias line {line_num}: {e}")
                            error_count += 1
                            continue
                
                processed_count += 1
                
                if processed_count % 1000 == 0 and stdout:
                    stdout.write(f"Processed {processed_count} alias lines...")
        
        if batch_data:
            StringProtein.objects.bulk_create(batch_data, ignore_conflicts=True)
            created_count += len(batch_data)
    
    except Exception as e:
        raise CommandError(f'Failed to process STRING alias file: {e}')
    
    stdout.write(f"\nString alias import completed:")
    stdout.write(f"  Total lines processed: {processed_count}")
    stdout.write(f"  Records created: {created_count}")
    stdout.write(f"  Errors: {error_count}")
    stdout.write("")
    
    return True

def process_string_interactions(file_path, stdout=None):
    """
    Process STRING interaction file and save to database
    """
    if not os.path.exists(file_path):
        raise CommandError(f'STRING interaction file not found at: {file_path}')

    stdout.write("Step 1: Reading all protein IDs from the file...")
    protein_ids_to_fetch = set()
    with gzip.open(file_path, 'rt', encoding='utf-8') as file:
        for line in file:
            if line.startswith('protein1') or line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                protein1_id = parts[0][5:] if parts[0].startswith('9606.') else parts[0]
                protein2_id = parts[1][5:] if parts[1].startswith('9606.') else parts[1]
                protein_ids_to_fetch.add(protein1_id)
                protein_ids_to_fetch.add(protein2_id)

    stdout.write(f"Step 2: Fetching {len(protein_ids_to_fetch)} unique proteins from the database...")
    protein_cache = StringProtein.objects.in_bulk(list(protein_ids_to_fetch), field_name='protein_id')
    
    stdout.write(f"Found {len(protein_cache)} proteins in the database.")

    stdout.write("Step 3: Processing interactions and batch inserting...")
    
    batch_size = 5000
    batch_data = []
    created_count = 0
    processed_count = 0
    error_count = 0
    missing_proteins = set()
    
    StringInteraction.objects.all().delete()
    
    try:
        with transaction.atomic():
            with gzip.open(file_path, 'rt', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    if line.startswith('protein1') or line.startswith('#') or not line.strip():
                        continue

                    parts = line.split()
                    
                    try:
                        protein1_id = parts[0][5:] if parts[0].startswith('9606.') else parts[0]
                        protein2_id = parts[1][5:] if parts[1].startswith('9606.') else parts[1]
                        combined_score = int(parts[2])

                        try:
                            protein1 = protein_cache[protein1_id]
                        except KeyError:
                            error_count += 1
                            if protein1_id not in missing_proteins:
                                stdout.write(f"Warning: No protein found for {protein1_id}")
                                missing_proteins.add(protein1_id)
                            continue

                        try:
                            protein2 = protein_cache[protein2_id]
                        except KeyError:
                            error_count += 1
                            if protein2_id not in missing_proteins:
                                stdout.write(f"Warning: No protein found for {protein2_id}")
                                missing_proteins.add(protein2_id)
                            continue

                        p1, p2 = (protein1, protein2) if protein1.id <= protein2.id else (protein2, protein1)

                        batch_data.append(StringInteraction(
                            protein1=p1,
                            protein2=p2,
                            combined_score=combined_score
                        ))

                        if len(batch_data) >= batch_size:
                            StringInteraction.objects.bulk_create(batch_data, ignore_conflicts=True)
                            created_count += len(batch_data)
                            batch_data = []
                            stdout.write(f"Processed {processed_count} lines, inserted {created_count} records...")

                    except (ValueError, IndexError) as e:
                        stdout.write(f"Warning: Skipping malformed line {line_num}: {line.strip()} | Error: {e}")
                        error_count += 1
                        continue
                    
                    processed_count += 1

                if batch_data:
                    StringInteraction.objects.bulk_create(batch_data, ignore_conflicts=True)
                    created_count += len(batch_data)

    except Exception as e:
        raise CommandError(f'Failed to process STRING interaction file: {e}')

    stdout.write(f"Processing complete. Total interactions created: {created_count}. Errors/Skipped lines: {error_count}.")
    stdout.write(f"\nString interaction import completed:")
    stdout.write(f"  Total lines processed: {processed_count}")
    stdout.write(f"  Records created: {created_count}")
    stdout.write(f"  Errors: {error_count}")
    stdout.write(f"  Missing proteins encountered: {len(missing_proteins)}")
    stdout.write("")

    return True

@transaction.atomic
def update_string_data(stdout, use_test_data):
    """
    Updates StringProtein and StringInteraction records from STRING data files.
    
    Args:
        stdout: Output stream for progress messages
        use_test_data: If True, use sample data files; if False, use full data files
    """
    results = {}
    
    # Choose the appropriate file paths
    alias_file_path = SAMPLE_STRING_ALIAS_PATH if use_test_data else STRING_ALIAS_PATH
    interaction_file_path = SAMPLE_STRING_INTERACTION_PATH if use_test_data else STRING_INTERACTION_PATH
    
    stdout.write("Starting STRING alias import...")
    alias_results = process_string_aliases(alias_file_path, stdout)

    stdout.write("Starting STRING interaction import...")
    interaction_results = process_string_interactions(interaction_file_path, stdout)
    
    return True