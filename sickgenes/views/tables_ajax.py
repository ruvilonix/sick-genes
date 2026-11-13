from sickgenes.tables import StudyTable
from sickgenes.models import Study
from django_tables2.config import RequestConfig
from django.http import HttpResponse
from django.db.models import Q, Count


def study_search_filter(search):
    """Match studies whose title or authors contain every word of the search."""
    search_filter = Q()
    for word in search.split():
        search_filter &= Q(title__icontains=word) | Q(authors__icontains=word)
    return search_filter


def table_study(request, phenotype_id=None):
    """
    AJAX handler for study table data. The phenotype filter is part of the
    URL path, since the AJAX table script only passes search, sort and page.
    """
    queryset = Study.objects.published()

    if phenotype_id:
        # The gene count below reuses this filter's join on cohorts, so with a
        # phenotype it only counts genes from cohorts tagged with it. This
        # depends on filtering before annotating.
        queryset = queryset.filter(study_cohorts__disease_tags=phenotype_id).distinct()

    queryset = queryset.annotate(
        gene_count=Count('study_cohorts__gene_findings__hgnc_gene', distinct=True)
    ).filter(gene_count__gt=0)

    search = request.GET.get("search")
    if search:
        queryset = queryset.filter(study_search_filter(search))

    table = StudyTable(queryset)
    RequestConfig(request).configure(table)
    return HttpResponse(table.as_html(request))
