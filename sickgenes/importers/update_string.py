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
    Process STRING interaction file and save to database, preventing duplicate pairs
    before they are sent to the database.
    """
    if not os.path.exists(file_path):
        raise CommandError(f'STRING interaction file not found at: {file_path}')

    # Step 1: Pre-scan the file to find all unique protein IDs needed.
    stdout.write("Step 1: Reading all protein IDs from the file...")
    protein_ids_to_fetch = set()
    with gzip.open(file_path, 'rt', encoding='utf-8') as file:
        for line in file:
            if line.startswith('protein1') or line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                # Strip the species ID (e.g., '9606.') from the protein identifier
                protein1_id = parts[0].split('.', 1)[-1]
                protein2_id = parts[1].split('.', 1)[-1]
                protein_ids_to_fetch.add(protein1_id)
                protein_ids_to_fetch.add(protein2_id)
    
    # Step 2: Fetch all required proteins from the DB in a single query.
    stdout.write(f"Step 2: Fetching {len(protein_ids_to_fetch)} unique proteins from the database...")
    protein_cache = {p.protein_id: p for p in StringProtein.objects.filter(protein_id__in=list(protein_ids_to_fetch))}
    stdout.write(f"Found {len(protein_cache)} proteins in the database.")

    # Step 3: Process interactions and perform batch inserts.
    stdout.write("Step 3: Processing interactions and batch inserting...")
    
    batch_size = 5000
    batch_data = []
    created_count = 0
    processed_count = 0
    skipped_count = 0
    missing_proteins = set()
    
    processed_pairs = set()

    StringInteraction.objects.all().delete()
    
    try:

        with gzip.open(file_path, 'rt', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                if line.startswith('protein1') or line.startswith('#') or not line.strip():
                    continue
                
                processed_count += 1
                parts = line.split()

                try:
                    protein1_id = parts[0].split('.', 1)[-1]
                    protein2_id = parts[1].split('.', 1)[-1]
                    combined_score = int(parts[2])

                    protein1 = protein_cache.get(protein1_id)
                    protein2 = protein_cache.get(protein2_id)

                    if not protein1 or not protein2:
                        skipped_count += 1
                        if not protein1 and protein1_id not in missing_proteins:
                            stdout.write(f"Warning: Protein not found in cache for ID {protein1_id}")
                            missing_proteins.add(protein1_id)
                        if not protein2 and protein2_id not in missing_proteins:
                            stdout.write(f"Warning: Protein not found in cache for ID {protein2_id}")
                            missing_proteins.add(protein2_id)
                        continue

                    p1, p2 = (protein1, protein2) if protein1.id <= protein2.id else (protein2, protein1)
                    
                    pair_key = (p1.id, p2.id)

                    if pair_key in processed_pairs:
                        skipped_count += 1
                        continue
                    
                    processed_pairs.add(pair_key)

                    batch_data.append(StringInteraction(
                        protein1=p1,
                        protein2=p2,
                        combined_score=combined_score
                    ))

                    if len(batch_data) >= batch_size:
                        StringInteraction.objects.bulk_create(batch_data, ignore_conflicts=True)
                        created_count += len(batch_data)
                        batch_data = []
                        stdout.write(f"Processed {processed_count} lines, inserted {created_count} unique interactions...")

                except (ValueError, IndexError) as e:
                    stdout.write(f"Warning: Skipping malformed line {line_num}: {line.strip()} | Error: {e}")
                    skipped_count += 1
                    continue

            # Insert any remaining records in the final batch.
            if batch_data:
                StringInteraction.objects.bulk_create(batch_data, ignore_conflicts=True)
                created_count += len(batch_data)

    except Exception as e:
        raise CommandError(f'Failed to process STRING interaction file: {e}')

    stdout.write("\n✅ Processing complete.")
    stdout.write(f"  - Total lines processed: {processed_count}")
    stdout.write(f"  - Unique interactions created: {created_count}")
    stdout.write(f"  - Skipped (duplicate, malformed, missing protein): {skipped_count}")
    stdout.write(f"  - Unique missing protein IDs encountered: {len(missing_proteins)}")
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