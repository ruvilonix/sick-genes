from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from sickgenes.forms import prepare_identifiers
from sickgenes.models import HgncGene, GeneFinding, Study, StudyCohort, GeneFindingType, HmdbMetabolite, MetaboliteFinding
from sickgenes.forms import StudyForm, StudyCohortForm
from django.db import transaction
from django.db.models import Prefetch
from django.contrib.admin.views.decorators import staff_member_required

def study(request, study_id):
    study = get_object_or_404(
        Study.objects.prefetch_related(
            'study_cohorts',
            'study_cohorts__disease_tags',
            'study_cohorts__control_tags',
            'study_cohorts__metabolite_findings',
            Prefetch(
                'study_cohorts__gene_findings',
                queryset=GeneFinding.objects.filter(type=GeneFindingType.ABUNDANCE),
                to_attr='abundance_gene_findings'
            ),
            Prefetch(
                'study_cohorts__gene_findings',
                queryset=GeneFinding.objects.filter(type=GeneFindingType.VARIATION),
                to_attr='variation_gene_findings'
            ),
        ),
        pk=study_id
    )

    return render(request, 'sickgenes/study.html', context={'study': study, 'gene_finding_type': GeneFindingType})

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

    if ('confirm_insert' in request.POST and context.get('items_only_exist_in_one_match')):
        search_one_match_formset = context['search_one_match_formset']
        findings_to_insert = []
        for form in search_one_match_formset:
            instance_data = {
                'study_cohort_id': study_cohort_id,
                fk_name: form['item_id'].value(),
            }

            if model_type == 'gene':
                gene_finding_type = request.GET.get('type')
                if gene_finding_type:
                    instance_data['type'] = gene_finding_type

            findings_to_insert.append(finding_model(**instance_data))

        finding_model.objects.bulk_create(findings_to_insert, ignore_conflicts=True)
        study = Study.objects.get(study_cohorts__id=study_cohort_id)
        return redirect(study)

    return render(request, 'sickgenes/molecule_match.html', context)