from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import JsonResponse, Http404
from sickgenes.forms import prepare_identifiers
from sickgenes.models import HgncGene, GeneFinding, Study, StudyCohort, HmdbMetabolite, MetaboliteFinding, SiteConfiguration
from sickgenes.forms import StudyForm, StudyCohortForm, GeneFilterForm, SetNewestStudyVersionForm
from django.db import transaction
from django.db.models import Prefetch, Count, Q
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from sickgenes.tables import GeneTable, StudyTable
from collections import defaultdict
from django_tables2.config import RequestConfig
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.html import escape
import markdown
import os
from urllib.parse import urlencode

def home(request):
    study_count = Study.objects.filter(not_finished=False, newest_version__isnull=True).count()

    context = {
        'home_page_description': markdown.markdown(SiteConfiguration.get_solo().home_page_description),
        'study_count': study_count,
    }
    return render(request, 'sickgenes/home.html', context)

def about(request):
    context = {
        'contact_email_address': settings.CONTACT_EMAIL_ADDRESS,
        'about_text': markdown.markdown(SiteConfiguration.get_solo().about)
    }
    return render(request, 'sickgenes/about.html', context)

def criteria(request): # TODO criteria page not needed anymore
    criteria_file = os.path.join(settings.BASE_DIR, 'criteria.md')

    try:
        with open(criteria_file, 'r') as f:
            content = f.read()

        criteria_html = markdown.markdown(content)

    except FileNotFoundError:
        criteria_html = "<p>Criteria file not found</p>"
    
    return render(request, 'sickgenes/criteria.html', {'criteria_html': criteria_html})

def study(request, study_id, slug=None):
    study = get_object_or_404(
        Study.objects.prefetch_related(
            'study_cohorts',
            'study_cohorts__disease_tags',
            'study_cohorts__metabolite_findings',
            'study_cohorts__gene_findings',
            'study_cohorts__gene_findings__hgnc_gene'
        ),
        pk=study_id
    )

    if study.not_finished and not request.user.is_staff:
        raise Http404

    if study.newest_version and not request.GET.get('no_redirect'):
        messages.info(
            request,
            mark_safe(f'You were redirected from an older version: <a href="{study.get_absolute_url()}?no_redirect=1">{escape(study.title)}</a>')
        )
        return redirect(study.newest_version)
    

    set_newest_version_form = SetNewestStudyVersionForm(study=study)

    study_note = markdown.markdown(study.note)

    context = {
        'opts': Study._meta,
        'study': study,
        'study_note': study_note,
        'set_newest_version_form': set_newest_version_form,
    }

    return render(request, 'sickgenes/study.html', context)

@staff_member_required
def set_newest_study_version(request, study_id):
    
    study = get_object_or_404(Study, pk=study_id)
    
    if request.method == 'POST':
        form = SetNewestStudyVersionForm(request.POST, study=study)
        if form.is_valid():
            newest_study = form.cleaned_data['newest_version']
            study.set_newest_version(newest_study)
    
    return redirect(study)

def study_list(request):
    form = GeneFilterForm(request.GET)
    phenotype = form.cleaned_data.get('phenotype') if form.is_valid() else None

    context = {
        'form': form,
        'phenotype': phenotype,
    }
    
    return render(request, 'sickgenes/study_list.html', context)

def gene_list(request):
    """
    Displays a paginated and filterable table of genes.
    """
    base_queryset = HgncGene.objects.all()

    # Symbols come as one comma-separated parameter (?symbol=A,B,C). Repeated
    # parameters (?symbol=A&symbol=B) are still accepted for old links.
    gene_symbols_to_filter = [
        symbol.strip()
        for value in request.GET.getlist('symbol')
        for symbol in value.split(',')
        if symbol.strip()
    ]
    if gene_symbols_to_filter:
        base_queryset = base_queryset.filter(symbol__in=gene_symbols_to_filter)

    # ?cohort=<id> shows the genes found in that study cohort
    cohort_id = request.GET.get('cohort', '')
    if cohort_id.isdigit():
        cohort_findings = GeneFinding.objects.filter(study_cohort_id=cohort_id)
        if not request.user.is_staff:
            cohort_findings = cohort_findings.filter(study_cohort__study__not_finished=False)
        base_queryset = base_queryset.filter(id__in=cohort_findings.values('hgnc_gene_id'))
    else:
        cohort_id = ''
    
    form = GeneFilterForm(request.GET)
    
    if form.is_valid() and form.cleaned_data.get('phenotype'):
        disease = form.cleaned_data['phenotype']
        
        genes = base_queryset.annotate(
            study_count=Count(
                'genefinding__study_cohort__study',
                filter=Q(
                    genefinding__study_cohort__study__not_finished=False,
                    genefinding__study_cohort__study__newest_version__isnull=True,
                    genefinding__study_cohort__disease_tags=disease
                ),
                distinct=True,
            )
        ).distinct()

    else:
        genes = base_queryset.annotate(
            study_count=Count(
                'genefinding__study_cohort__study',
                filter=Q(
                    genefinding__study_cohort__study__not_finished=False,
                    genefinding__study_cohort__study__newest_version__isnull=True,
                    ),
                distinct=True,
            )
        )

    genes_table = GeneTable(genes)
    RequestConfig(request, paginate={"per_page": 25}).configure(genes_table)

    context = {
        'form': form,
        'genes_table': genes_table,
        'filtered_genes': ','.join(gene_symbols_to_filter),
        'cohort_id': cohort_id,
        'title': 'Gene List',
    }
    
    return render(request, 'sickgenes/gene_list.html', context)

def gene_detail(request, hgnc_symbol):
    """
    Displays details for a single gene
    """
    gene_queryset = HgncGene.objects.prefetch_related(
        'ena_set',
        'uniprotid_set',
        'omimid_set',
        'aliassymbol_set',
        'aliasname_set',
        'prevsymbol_set',
        'prevname_set'
    )
    gene = gene_queryset.filter(symbol=hgnc_symbol).first()
    if gene is None:
        return redirect_unknown_gene_symbol(request, hgnc_symbol)

    gene_findings = GeneFinding.objects.filter(hgnc_gene=gene).exclude(
        study_cohort__study__not_finished=True
    ).exclude(
        study_cohort__study__newest_version__isnull=False
    ).select_related(
        'study_cohort__study'
    ).prefetch_related(
        'study_cohort__disease_tags'
    )

    studies_data = defaultdict(list)
    for finding in gene_findings:
        study = finding.study_cohort.study
        cohort = finding.study_cohort
        
        if cohort not in studies_data[study]:
            studies_data[study].append(cohort)

    sorted_studies = sorted(
        studies_data.items(), 
        key=lambda item: (item[0].publication_year or 0, item[0].title), 
        reverse=True
    )

    context = {
        'gene': gene,
        'studies_data': sorted_studies
    }
    
    return render(request, 'sickgenes/gene_detail.html', context)


def redirect_unknown_gene_symbol(request, symbol):
    """
    Handles gene URLs whose symbol isn't a current HGNC symbol: a different
    case (/gene/ttn/), or a symbol HGNC has since renamed (/gene/MLLT4/).
    Redirects are temporary, since an old symbol can later be given to a
    different gene.
    """
    gene = HgncGene.objects.filter(symbol__iexact=symbol).first()
    if gene:
        return redirect(gene)

    renamed_to = list(HgncGene.objects.filter(prevsymbol__value__iexact=symbol).distinct())
    if len(renamed_to) == 1:
        return redirect(renamed_to[0])
    if renamed_to:
        context = {'symbol': symbol, 'genes': renamed_to}
        return render(request, 'sickgenes/gene_previous_symbol.html', context)

    raise Http404


@staff_member_required
def add_study(request):
    if request.method == 'POST':
        form = StudyForm(request.POST)
        if form.is_valid():
            study = form.save()
            return redirect(study)
    else:
        form = StudyForm()

    return render(request, 'sickgenes/add_study.html', context={'form': form})

@staff_member_required
def add_study_cohort(request, study_id):
    study = get_object_or_404(Study, pk=study_id)

    if request.method == 'POST':
        form = StudyCohortForm(request.POST)
        if form.is_valid():
            study_cohort = form.save(commit=False)
            study_cohort.study = study
            study_cohort.save()
            form.save_m2m()

            return redirect(study)
    else:
        form = StudyCohortForm()

    return render(request, 'sickgenes/add_study_cohort.html', context={'form': form})

MODEL_CONFIG = {
    'gene': {
        'source_model': HgncGene,
        'finding_model': GeneFinding,
        'fk_name': 'hgnc_gene_id' # The foreign key field name on the finding model
    },
    'metabolite': {
        'source_model': HmdbMetabolite,
        'finding_model': MetaboliteFinding, # Assumed model
        'fk_name': 'hmdb_metabolite_id'
    },
}

def identify_molecules(request, model_type):
    config = MODEL_CONFIG.get(model_type)
    if not config:
        raise Http404(f"Model type '{model_type}' is not supported.")

    context = prepare_identifiers(request, config['source_model'])
    context['view_type'] = 'search'
    context['title'] = f'Search'

    if context.get('items_only_exist_in_one_match'):
        search_one_match_formset = context['search_one_match_formset']

        item_ids_to_search = []
        for form in search_one_match_formset:
            item_ids_to_search.append(form['item_id'].value())

        items_to_search = list(HgncGene.objects.filter(id__in=item_ids_to_search).values_list('symbol', flat=True))

        if items_to_search:
            # One comma-separated parameter keeps the URL short
            query_string = urlencode({'symbol': ','.join(items_to_search)}, safe=',')
            redirect_url = f"{reverse('sickgenes:gene_list')}?{query_string}"
            return redirect(redirect_url)

    return render(request, 'sickgenes/molecule_match.html', context)

@staff_member_required
def insert_findings(request, study_cohort_id, model_type):
    """
    Handles finding matches for a list of identifiers and inserting them
    into a specific study_cohort.
    """

    config = MODEL_CONFIG.get(model_type)
    if not config:
        raise Http404(f"Model type '{model_type}' is not supported.")

    source_model = config['source_model']
    finding_model = config['finding_model']
    fk_name = config['fk_name']

    context = prepare_identifiers(request, source_model)
    context['view_type'] = 'insert'
    context['title'] = f'Add {model_type}s to study'

    if ('confirm_insert' in request.POST and context.get('items_only_exist_in_one_match')):
        search_one_match_formset = context['search_one_match_formset']
        findings_to_insert = []
        for form in search_one_match_formset:
            instance_data = {
                'study_cohort_id': study_cohort_id,
                fk_name: form['item_id'].value(),
            }

            findings_to_insert.append(finding_model(**instance_data))

        finding_model.objects.bulk_create(findings_to_insert, ignore_conflicts=True)
        study = Study.objects.get(study_cohorts__id=study_cohort_id)
        return redirect(study)

    return render(request, 'sickgenes/molecule_match.html', context)

