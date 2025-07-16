from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from sickgenes.forms import prepare_identifiers
from sickgenes.models import HgncGene, GeneFinding, Study, StudyCohort, HmdbMetabolite, MetaboliteFinding
from sickgenes.forms import StudyForm, StudyCohortForm, GeneFilterForm
from django.db import transaction
from django.db.models import Prefetch, Count
from django.contrib.admin.views.decorators import staff_member_required
from sickgenes.tables import GeneTable
from collections import defaultdict

def study(request, study_id):
    study = get_object_or_404(
        Study.objects.prefetch_related(
            'study_cohorts',
            'study_cohorts__disease_tags',
            'study_cohorts__metabolite_findings',
            'study_cohorts__gene_findings',
        ),
        pk=study_id
    )

    return render(request, 'sickgenes/study.html', context={'study': study})

def gene_list(request):
    """
    Displays a paginated and filterable table of genes.
    """
    base_queryset = HgncGene.objects.all()
    
    form = GeneFilterForm(request.GET)
    
    if form.is_valid() and form.cleaned_data.get('disease'):
        disease = form.cleaned_data['disease']
        
        base_queryset = base_queryset.filter(
            genefinding__study_cohort__disease_tags=disease
        ).distinct() 

    genes = base_queryset.annotate(
        study_count=Count('genefinding__study_cohort__study', distinct=True)
    )

    genes_table = GeneTable(genes)

    context = {
        'form': form,
        'genes_table': genes_table,
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
    gene = get_object_or_404(gene_queryset, symbol=hgnc_symbol)

    gene_findings = GeneFinding.objects.filter(hgnc_gene=gene).select_related(
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

    # Your existing logic for processing the input list
    # (Assuming prepare_gene_identifiers is renamed to prepare_identifiers)
    context = prepare_identifiers(request, config['source_model'])
    context['view_type'] = 'search'
    context['title'] = f'Search for {model_type}s'

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