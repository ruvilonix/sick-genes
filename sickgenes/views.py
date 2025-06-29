from django.shortcuts import render
from sickgenes.forms import MoleculeMatchForm

def add_molecules(request):
    if request.method == 'GET':
        form = MoleculeMatchForm()
    else:
        form = MoleculeMatchForm(request.POST)
        if form.is_valid():
            pass
                                 
    return render(request, 'sickgenes/molecule_match.html', {'form': form})