from django.shortcuts import render
from django.http import HttpResponse
from sickgenes.forms import SearchInitialForm, SearchNoMatchesFormSet, SearchMultipleMatchesFormSet, SearchOneMatchFormSet, prepare_gene_identifiers
from sickgenes.models import HgncGene, Finding
from sickgenes.forms import StudyForm

def add_study(request):
    if request.method == 'POST':
        form = StudyForm(request.POST)
        if form.is_valid():
            study = form.save()
            return HttpResponse(f'You created {study}')
    else:
        form = StudyForm()

    return render(request, 'sickgenes/add_study.html', context={'form': form})



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

