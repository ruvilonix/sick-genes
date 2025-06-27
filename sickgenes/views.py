from django.shortcuts import render
from django.views import View
from sickgenes.forms import MoleculeMatchForm

class MoleculeMatchView(View):
    template_name = 'sickgenes/molecule_match.html'

    def get(self, request):
        form = MoleculeMatchForm()
        return render(request, self.template_name, {'form': form})