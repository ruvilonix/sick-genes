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
    Process STRING alias file and create/update StringProtein records.
    """
    if not os.path.exists(file_path):
        raise CommandError(f'STRING alias file not found at: {file_path}')
    
    created_count = 0
    updated_count = 0
    error_count = 0
    processed_count = 0
    
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
                            
                            string_protein, created = StringProtein.objects.update_or_create(
                                protein_id=protein_id,
                                defaults={
                                    'hgnc_id': hgnc_id,
                                    'hgnc_gene': hgnc_gene
                                }
                            )
                            
                            if created:
                                created_count += 1
                            else:
                                updated_count += 1
                                
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
    
    except Exception as e:
        raise CommandError(f'Failed to process STRING alias file: {e}')
    
    stdout.write(f"\nString alias import completed:")
    stdout.write(f"  Total lines processed: {processed_count}")
    stdout.write(f"  Records created: {created_count}")
    stdout.write(f"  Records updated: {updated_count}")
    stdout.write(f"  Errors: {error_count}")
    stdout.write("")
    
    return True

def process_string_interactions(file_path, stdout=None):
    """
    Process STRING interaction file and create/update StringInteraction records.
    """
    if not os.path.exists(file_path):
        raise CommandError(f'STRING interaction file not found at: {file_path}')
    
    created_count = 0
    updated_count = 0
    error_count = 0
    processed_count = 0
    
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                
                if not line or line.startswith('#') or line.startswith('protein1'):
                    continue
                
                parts = line.split()
                
                if len(parts) >= 3:
                    protein1_id = parts[0]
                    protein2_id = parts[1]
                    combined_score = parts[2]
                    
                    if protein1_id.startswith('9606.'):
                        protein1_id = protein1_id[5:]
                    if protein2_id.startswith('9606.'):
                        protein2_id = protein2_id[5:]
                    
                    try:
                        combined_score = int(combined_score)
                        
                        protein1 = StringProtein.objects.get(protein_id=protein1_id)
                        protein2 = StringProtein.objects.get(protein_id=protein2_id)
                        
                        # To avoid duplicate interactions, ensure consistent ordering
                        if protein1.id <= protein2.id:
                            p1, p2 = protein1, protein2
                        else:
                            p1, p2 = protein2, protein1
                        
                        interaction, created = StringInteraction.objects.update_or_create(
                            protein1=p1,
                            protein2=p2,
                            defaults={
                                'combined_score': combined_score
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                            
                    except StringProtein.DoesNotExist as e:
                        if stdout:
                            stdout.write(f"Warning: StringProtein not found for interaction {protein1_id} - {protein2_id}")
                        error_count += 1
                        continue
                    except ValueError as e:
                        if stdout:
                            stdout.write(f"Error parsing combined_score on line {line_num}: {e}")
                        error_count += 1
                        continue
                    except Exception as e:
                        if stdout:
                            stdout.write(f"Error processing interaction line {line_num}: {e}")
                        error_count += 1
                        continue
                
                processed_count += 1
                
                # Output progress every 1000 lines
                if processed_count % 1000 == 0 and stdout:
                    stdout.write(f"Processed {processed_count} interaction lines...")
    
    except Exception as e:
        raise CommandError(f'Failed to process STRING interaction file: {e}')
    
    stdout.write(f"\nString interaction import completed:")
    stdout.write(f"  Total lines processed: {processed_count}")
    stdout.write(f"  Records created: {created_count}")
    stdout.write(f"  Records updated: {updated_count}")
    stdout.write(f"  Errors: {error_count}")
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