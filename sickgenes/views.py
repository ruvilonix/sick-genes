from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from sickgenes.forms import prepare_gene_identifiers
from sickgenes.models import HgncGene, GeneFinding, Study, StudyCohort, GeneFindingType
from sickgenes.forms import StudyForm, StudyCohortForm
from django.db import transaction
from django.db.models import Prefetch

def study(request, study_id):
    study = get_object_or_404(
        Study.objects.prefetch_related(
            'study_cohorts',
            'study_cohorts__disease_tags',
            'study_cohorts__control_tags',
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

    return render(request, 'sickgenes/study.html', context={'study': study})

def add_study(request):
    if request.method == 'POST':
        form = StudyForm(request.POST)
        if form.is_valid():
            study = form.save()
            return redirect(study)
    else:
        form = StudyForm()

    return render(request, 'sickgenes/add_study.html', context={'form': form})

def add_study_cohort(request, study_id):
    study = get_object_or_404(Study, pk=study_id)

    if request.method == 'POST':
        form = StudyCohortForm(request.POST)
        if form.is_valid():
            study_cohort = form.save(commit=False)
            study_cohort.study = study
            study_cohort.save()
            form.save_m2m

            return redirect(study)
    else:
        form = StudyCohortForm()

    return render(request, 'sickgenes/add_study_cohort.html', context={'form': form})


def add_genes(request, study_cohort_id, gene_finding_type):
    
    context = prepare_gene_identifiers(request, HgncGene)
    context |= {'view_type': 'insert'}

    if ('confirm_insert' in request.POST and context['items_only_exist_in_one_match']):
        search_one_match_formset = context['search_one_match_formset']
        findings_to_insert = []
        for form in search_one_match_formset:
            findings_to_insert.append(
                GeneFinding(
                    study_cohort_id=study_cohort_id,
                    hgnc_gene_id=form['item_id'].value(),
                    type=gene_finding_type,
                )
            )


        GeneFinding.objects.bulk_create(findings_to_insert, ignore_conflicts=True)

    return render(request, 'sickgenes/molecule_match.html', context)

def search_genes(request):
    pass

