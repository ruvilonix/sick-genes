from django.http import HttpResponse
from sickgenes.models import Study
import json
import gzip


def without_empty(data):
    """Return a copy of the dict without values that are None, empty or False."""
    return {key: value for key, value in data.items() if value}


def database_dump_json_v2(request):
    """
    A view that returns the Study database as a nested JSON object,
    omitting any fields that are None or empty.
    Genes are deduplicated into a separate list with full metadata.
    """
    studies = Study.objects.published().prefetch_related(
        'study_cohorts__disease_tags',
        'study_cohorts__gene_findings__hgnc_gene',
    )

    studies_list = []
    unique_genes = {}

    for study in studies:
        publication_date = None
        if study.publication_year:
            publication_date = without_empty({
                'year': study.publication_year,
                'month': study.publication_month,
                'day': study.publication_day,
            })

        cohorts_list = []
        for cohort in study.study_cohorts.all():
            gene_findings_list = []
            for finding in cohort.gene_findings.all():
                gene = finding.hgnc_gene
                # Gene metadata keeps empty values, unlike studies and cohorts
                unique_genes.setdefault(gene.hgnc_id, {
                    "hgnc_id": gene.hgnc_id,
                    "hgnc_symbol": gene.symbol,
                    "hgnc_name": gene.name,
                    "entrez_id": gene.entrez_id,
                    "ensembl_gene_id": gene.ensembl_gene_id,
                })
                gene_findings_list.append({"hgnc_id": gene.hgnc_id, "hgnc_symbol": gene.symbol})

            cohort_data = without_empty({
                "note": cohort.note,
                "phenotypes": [
                    {"code": disease.code, "description": disease.name}
                    for disease in cohort.disease_tags.all()
                ],
                "gene_findings": gene_findings_list,
            })
            if cohort_data:
                cohorts_list.append(cohort_data)

        studies_list.append(without_empty({
            "title": study.title,
            "doi": study.doi,
            "sickgenes_url": request.build_absolute_uri(study.get_absolute_url()),
            "pmid": study.pmid,
            "authors": study.authors,
            "journal_titles": study.journal_titles,
            "note": study.note,
            "preprint": study.preprint,
            "publisher_url": study.publisher_url,
            "s4me_url": study.s4me_url,
            "publication_date": publication_date,
            "study_cohorts": cohorts_list,
        }))

    response_data = {
        "genes": list(unique_genes.values()),
        "studies": studies_list
    }

    json_content = json.dumps(response_data, indent=2)
    gzipped_content = gzip.compress(json_content.encode(encoding='utf-8'))
    return HttpResponse(gzipped_content, content_type="application/gzip")
