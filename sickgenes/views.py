from django.shortcuts import render
from sickgenes.forms import MoleculeMatchForm

def add_molecules(request):
    form = MoleculeMatchForm()
    return render(request, 'sickgenes/molecule_match.html', {'form': form})