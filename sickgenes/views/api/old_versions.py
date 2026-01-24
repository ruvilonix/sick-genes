from django.http import JsonResponse
from sickgenes.models import Study

def database_dump_json_v1(request):
    """
    A view that returns the Study database as a nested JSON object,
    omitting any fields that are None or empty.
    """
    studies_query = Study.objects.prefetch_related(
        'study_cohorts__disease_tags',
        'study_cohorts__gene_findings__hgnc_gene',
        'study_cohorts__metabolite_findings__hmdb_metabolite',
    ).exclude(not_finished=True)

    studies_list = []
    for study in studies_query:
        study_data = {}

        if study.title:
            study_data["title"] = study.title
        if study.doi:
            study_data["doi"] = study.doi
        if study.authors:
            study_data["authors"] = study.authors
        if study.journal_titles:
            study_data["journal_titles"] = study.journal_titles
        if study.note:
            study_data["note"] = study.note
        if study.s4me_url:
            study_data["s4me_url"] = study.s4me_url
        if study.publication_year:
            study_data["publication_date"] = {'year': study.publication_year}
            if study.publication_month:
                study_data["publication_date"]['month'] = study.publication_month
            if study.publication_day:
                study_data["publication_date"]['day'] = study.publication_day

        cohorts_list = []
        for cohort in study.study_cohorts.all():
            cohort_data = {}

            if cohort.note:
                cohort_data["note"] = cohort.note

            phenotypes = [disease.name for disease in cohort.disease_tags.all()]
            gene_findings_list = [
                {"hgnc_id": f"HGNC:{f.hgnc_gene.hgnc_id}", "symbol": f.hgnc_gene.symbol}
                for f in cohort.gene_findings.all() if f.hgnc_gene
            ]

            if phenotypes:
                cohort_data["phenotypes"] = phenotypes
            if gene_findings_list:
                cohort_data["gene_findings"] = gene_findings_list
            
            if cohort_data:
                cohorts_list.append(cohort_data)

        if cohorts_list:
            study_data["study_cohorts"] = cohorts_list
        
        studies_list.append(study_data)

    response_data = {"studies": studies_list}

    response = JsonResponse(response_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = 'attachment; filename=sickgenes-full-database.json'

    return response