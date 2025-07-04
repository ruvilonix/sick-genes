from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from sickgenes.forms import SearchInitialForm, SearchNoMatchesFormSet, SearchMultipleMatchesFormSet, SearchOneMatchFormSet, prepare_gene_identifiers
from sickgenes.models import HgncGene, Finding, Study, StudyCohort
from sickgenes.forms import StudyForm, StudyCohortForm

def study(request, study_id):
    study = get_object_or_404(Study, pk=study_id)

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


def add_genes(request):
    
    context = prepare_gene_identifiers(request, HgncGene)
    context |= {'view_type': 'insert'}

    if ('confirm_insert' in request.POST and context['items_only_exist_in_one_match']):
        search_one_match_formset = context['search_one_match_formset']
        findings_to_insert = []
        for form in search_one_match_formset:
            findings_to_insert.append(Finding(study_cohort_id=1, hgnc_gene_id=form['item_id'].value()))

        Finding.objects.bulk_create(findings_to_insert)

    return render(request, 'sickgenes/molecule_match.html', context)

def search_genes(request):
    pass

