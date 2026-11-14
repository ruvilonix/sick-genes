from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Count
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


@dataclass
class HgncImportResult:
    """What an HGNC import did, including changes to genes that have findings."""
    processed_count: int = 0
    # (old symbol, new symbol, number of findings)
    renamed: list = field(default_factory=list)
    # (symbol, HGNC ID number, number of findings) for genes not in any file
    missing: list = field(default_factory=list)

    def report_lines(self):
        if not self.renamed and not self.missing:
            return ['No genes with findings were renamed or removed.']
        lines = []
        if self.renamed:
            lines.append('Genes with findings that HGNC renamed:')
            lines += [f'  {old} -> {new} ({findings_text(n)})' for old, new, n in self.renamed]
        if self.missing:
            lines.append(
                "Genes with findings that are no longer in HGNC's files (withdrawn or merged; "
                'look them up on genenames.org):'
            )
            lines += [f'  {symbol}, HGNC:{hgnc_id} ({findings_text(n)})' for symbol, hgnc_id, n in self.missing]
        return lines


def findings_text(number):
    return f'{number} finding' if number == 1 else f'{number} findings'


@transaction.atomic
def update_hgnc_data(hgnc_data_paths, stdout=None):
    """
    Updates HgncGene records and their related tables from HGNC's JSON files.
    Genes missing from the files are kept, since findings may point to them.
    Returns an HgncImportResult.
    """
    result = HgncImportResult()
    # Only genes with findings are reported, so only these are remembered
    genes_with_findings = {
        hgnc_id: (symbol, findings)
        for hgnc_id, symbol, findings in HgncGene.objects
            .annotate(findings=Count('genefinding'))
            .filter(findings__gt=0)
            .values_list('hgnc_id', 'symbol', 'findings')
    }
    seen_ids = set()

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
            seen_ids.add(hgnc_id)
            if hgnc_id in genes_with_findings:
                old_symbol, findings = genes_with_findings[hgnc_id]
                if old_symbol != gene_data['symbol']:
                    result.renamed.append((old_symbol, gene_data['symbol'], findings))

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

            # HGNC leaves a list out of the record when it's empty, so a missing
            # list means its old values were removed and must be cleared too
            for field_name, model_class in RELATED_MODELS.items():
                model_class.objects.filter(gene=gene_obj).delete()
                items_to_create = [
                    model_class(gene=gene_obj, value=item)
                    for item in gene_data.get(field_name, []) if item is not None
                ]
                if items_to_create:
                    # ignore_conflicts skips a value repeated within one list
                    model_class.objects.bulk_create(items_to_create, ignore_conflicts=True)

            result.processed_count += 1
            output_progress(result.processed_count, stdout)

        if stdout:
            stdout.write()

    result.missing = [
        (symbol, hgnc_id, findings)
        for hgnc_id, (symbol, findings) in sorted(genes_with_findings.items())
        if hgnc_id not in seen_ids
    ]
    return result


def parse_hgnc_id(value):
    """The number in an HGNC ID such as "HGNC:5", or None if there isn't one."""
    _, _, number = (value or '').partition(':')
    return int(number) if number.isdigit() else None
