from django.db import transaction
from django.core.management.base import CommandError
from sickgenes.models import HgncGene, Ena, UniprotId, OmimId, AliasSymbol, AliasName, PrevSymbol, PrevName
from .helper_functions import get_json_from_source, output_progress

RELATED_MODELS = {
    'ena': Ena,
    'uniprot_ids': UniprotId,
    'omim_id': OmimId,
    'alias_symbol': AliasSymbol,
    'alias_name': AliasName,
    'prev_symbol': PrevSymbol,
    'prev_name': PrevName,
}

@transaction.atomic
def update_hgnc_data(hgnc_data_paths, stdout=None):
    """
    Updates HgncGene records and their related tables from a JSON data source.
    """
    processed_count = 0

    for hgnc_data_path in hgnc_data_paths:
        try:
            hgnc_data = get_json_from_source(hgnc_data_path)
            hgnc_genes = hgnc_data['response']['docs']
        except Exception as e:
            raise CommandError(f'Failed to retrieve or parse HGNC JSON data: {e}')

        for gene_data in hgnc_genes:
            hgnc_id = parse_hgnc_id(gene_data.get('hgnc_id'))
            # Both are required in the database; skip a record that lacks one
            # rather than failing the whole import
            if hgnc_id is None or not gene_data.get('symbol'):
                continue

            main_fields = {
                'symbol': gene_data.get('symbol'),
                'name': gene_data.get('name'),
                'entrez_id': gene_data.get('entrez_id'),
                'ensembl_gene_id': gene_data.get('ensembl_gene_id'),
                'vega_id': gene_data.get('vega_id'),
                'ucsc_id': gene_data.get('ucsc_id'),
            }
            gene_obj, _ = HgncGene.objects.update_or_create(
                hgnc_id=hgnc_id,
                defaults=main_fields
            )

            for field_name, model_class in RELATED_MODELS.items():
                if field_name in gene_data:
                    model_class.objects.filter(gene=gene_obj).delete()

                    # Bulk create new entries for efficiency
                    items_to_create = [
                        model_class(gene=gene_obj, value=item)
                        for item in gene_data[field_name] if item is not None
                    ]
                    if items_to_create:
                        model_class.objects.bulk_create(items_to_create, ignore_conflicts=True)
            
            processed_count += 1

            output_progress(processed_count, stdout)

        if stdout:
            stdout.write()

    return processed_count


def parse_hgnc_id(value):
    """The number in an HGNC ID such as "HGNC:5", or None if there isn't one."""
    _, _, number = (value or '').partition(':')
    return int(number) if number.isdigit() else None
