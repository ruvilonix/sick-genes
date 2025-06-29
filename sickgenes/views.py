from django.shortcuts import render
from sickgenes.forms import MoleculeMatchForm
from sickgenes.models import Molecule

def add_molecules(request):
    if request.method == 'GET':
        form = MoleculeMatchForm()
    else:
        form = MoleculeMatchForm(request.POST)
        if form.is_valid():
            search_terms = search_results = form.cleaned_data['search_terms']
            search_results = Molecule.objects.find_matching_molecules(search_terms, [Molecule.MoleculeType.GENE, Molecule.MoleculeType.METABOLITE])

    return render(request, 'sickgenes/molecule_match.html', {'form': form})