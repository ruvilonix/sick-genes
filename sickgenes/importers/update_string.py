from django.db import transaction
from django.core.management.base import CommandError
from sickgenes.models import StringProtein, HgncGene
from django.conf import settings
import os
import gzip

BASE_DIR = settings.BASE_DIR
SAMPLE_STRING_ALIAS_PATH = os.path.join(BASE_DIR, 'sample_data/sample_9606.protein.aliases.v12.0.txt.gz')
STRING_ALIAS_PATH = os.path.join(BASE_DIR, 'approved_data/9606.protein.aliases.v12.0.txt.gz')

@transaction.atomic
def update_string_data(stdout, use_test_data):
    """
    Updates StringProtein records from the STRING alias file.
    """
    # Choose the appropriate file path
    file_path = SAMPLE_STRING_ALIAS_PATH if use_test_data else STRING_ALIAS_PATH
    
    if not os.path.exists(file_path):
        raise CommandError(f'STRING alias file not found at: {file_path}')
    
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as file:
            processed_count = 0
            created_count = 0
            updated_count = 0
            error_count = 0
            
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
                            protein_id = string_protein_id[5:]  # Remove '9606.' prefix
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
                                stdout.write(f"Error processing line {line_num}: {e}")
                            error_count += 1
                            continue
                
                processed_count += 1
                
                # Output progress every 1000 lines
                if processed_count % 1000 == 0 and stdout:
                    stdout.write(f"Processed {processed_count} lines...")
    
    except Exception as e:
        raise CommandError(f'Failed to process STRING alias file: {e}')
    
    # Summary output
    if stdout:
        stdout.write(f"\nString protein import completed:")
        stdout.write(f"  Total lines processed: {processed_count}")
        stdout.write(f"  Records created: {created_count}")
        stdout.write(f"  Records updated: {updated_count}")
        stdout.write(f"  Errors: {error_count}")
    
    return True