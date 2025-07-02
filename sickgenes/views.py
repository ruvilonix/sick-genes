from django.shortcuts import render
from sickgenes.forms import MoleculeMatchForm
from sickgenes.models import HgncGene

def add_genes(request):
    context = {}

    if request.method == 'GET':
        form = MoleculeMatchForm()
    else:
        form = MoleculeMatchForm(request.POST)
        if form.is_valid():
            search_terms = search_results = form.cleaned_data['search_terms']
            search_results = HgncGene.objects.find_matching_items(search_terms)

            form = MoleculeMatchForm(initial={'matching_data': search_results})

            context['search_results'] = search_results

    context['form'] = form

    return render(request, 'sickgenes/molecule_match.html', context)
