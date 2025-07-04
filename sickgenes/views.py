from django.shortcuts import render
from sickgenes.forms import SearchInitialForm, SearchNoMatchesFormSet, SearchMultipleMatchesFormSet, SearchOneMatchFormSet, process_search_forms
from sickgenes.models import HgncGene, Finding

def add_genes(request):
    
    context = prepare_gene_identifiers(request)
    context |= {'view_type': 'insert'}

    # TODO If "insert" button is pressed and context['items_only_exist_in_one_match'] is True, insert into database 
    if ('confirm_insert' in request.POST and context['items_only_exist_in_one_match']):
        search_one_match_formset = context['search_one_match_formset']
        findings_to_insert = []
        for form in search_one_match_formset:
            findings_to_insert.append(Finding(study_cohort_id=1, hgnc_gene_id=form['item_id'].value()))

        Finding.objects.bulk_create(findings_to_insert)

    return render(request, 'sickgenes/molecule_match.html', context)

def search_genes(request):
    pass

def prepare_gene_identifiers(request):
    """Prepare forms/formsets for retrieving IDs for items (genes) from a list of search terms"""

    def create_form(form_class, prefix=None):
        args = [request.POST] if request.method == 'POST' else []
        kwargs = {'prefix': prefix} if prefix else {}
        return form_class(*args, **kwargs)
    
    form_data = {
        'search_initial_form': create_form(SearchInitialForm),
        'search_no_matches_formset': create_form(SearchNoMatchesFormSet, 'no_matches'),
        'search_multiple_matches_formset': create_form(SearchMultipleMatchesFormSet, 'multiple_matches'),
        'search_one_match_formset': create_form(SearchOneMatchFormSet, 'one_match'),
        'items_only_exist_in_one_match': False,
    }
    
    if request.method == 'POST':
        form_data = process_search_forms(form_data, HgncGene)

    return form_data

