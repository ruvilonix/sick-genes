from sickgenes.tables import StudyTable
from sickgenes.models import Study
from django_tables2.config import RequestConfig
from django.http import HttpResponse
from django.db.models import Q, Count

def build_filter(search, *args, **kwargs):
    """
    Builds a search filter given the search parameters & search text.
    Use like a regular filter, except set any values you want searched set to True.
    """
    children = [*args, *sorted(kwargs.items())]
    search_keywords = search.split()
    search_filter = Q(_connector="AND")
    for keyword in search_keywords:
        current_filter = Q(_connector="OR")
        for (key, value) in children:
            if value is True:
                current_filter.children.append((key, keyword))
        search_filter.children.append(current_filter)
    return search_filter

def table_study(request):
    """
    AJAX handler for study table data
    """
    search = request.GET.get("search")
    disease = request.session.get('study_disease_filter')    

    
    base_queryset = Study.objects.exclude(not_finished=True)
    
    # Apply disease filter
    count_filter = Q()
    if disease:
        base_queryset = base_queryset.filter(
            study_cohorts__disease_tags=disease
        ).distinct()
        count_filter = Q(study_cohorts__disease_tags=disease)
    
    # Annotate with gene count
    queryset = base_queryset.annotate(
        gene_count=Count(
            'study_cohorts__gene_findings__hgnc_gene',
            filter=count_filter,
            distinct=True
        )
    ).filter(gene_count__gt=0)
    
    # Apply search filter if exists
    if search:
        search_filter = build_filter(
            search,
            title__icontains=True,
            authors__icontains=True,
        )
        queryset = queryset.filter(search_filter)
    
    # Create table
    table = StudyTable(queryset)
    RequestConfig(request).configure(table)
    
    return HttpResponse(table.as_html(request))