from django.shortcuts import render
from sickgenes.forms import SearchInitialForm, SearchNoMatchesFormSet, SearchMultipleMatchesFormSet
from sickgenes.models import HgncGene

def add_genes(request):
    context = {}

    if request.method == 'GET':
        search_initial_form = SearchInitialForm()
        search_no_matches_formset = SearchNoMatchesFormSet(prefix="no_matches")
        search_multiple_matches_formset = SearchMultipleMatchesFormSet(prefix="multiple_matches")
    else:
        search_initial_form = SearchInitialForm(request.POST)
        search_no_matches_formset = SearchNoMatchesFormSet(request.POST, prefix="no_matches")
        search_multiple_matches_formset = SearchMultipleMatchesFormSet(request.POST, prefix="multiple_matches")

        if search_initial_form.is_valid() and search_no_matches_formset.is_valid() and search_multiple_matches_formset.is_valid():

            # Get search terms from initial textarea and no_matches formset
            search_terms = search_initial_form.cleaned_data['search_terms']
            
            for form in search_no_matches_formset:
                if 'search_term' in form.cleaned_data:
                    search_term = form.cleaned_data['search_term']
                    if search_term != '':
                        search_terms.add(search_term)

            search_results = HgncGene.objects.find_matching_items(search_terms)



            # Generate new forms
            search_initial_form = SearchInitialForm()

            no_matches_formset_initial_data = []
            for search_term_with_no_matches in search_results['no_matches']:
                no_matches_formset_initial_data.append({"search_term": search_term_with_no_matches})
            search_no_matches_formset = SearchNoMatchesFormSet(initial=no_matches_formset_initial_data, prefix="no_matches")

            multiple_matches_formset_initial_data = []
            for search_term_with_multiple_matches in search_results['multiple_matches']:
                multiple_matches_formset_initial_data.append({"search_term": search_term_with_multiple_matches['search_string']})
            search_multiple_matches_formset = SearchNoMatchesFormSet(initial=multiple_matches_formset_initial_data, prefix="multiple_matches")
    
    context['search_initial_form'] = search_initial_form
    context['search_no_matches_formset'] = search_no_matches_formset
    context['search_multiple_matches_formset'] = search_multiple_matches_formset
    print(search_no_matches_formset)

    return render(request, 'sickgenes/molecule_match.html', context)
