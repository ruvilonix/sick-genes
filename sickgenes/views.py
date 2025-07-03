from django.shortcuts import render
from sickgenes.forms import SearchInitialForm, SearchNoMatchesFormSet, SearchMultipleMatchesFormSet, SearchOneMatchFormSet
from sickgenes.models import HgncGene

def add_genes(request):
    context = {}

    if request.method == 'GET':
        search_initial_form = SearchInitialForm()
        search_no_matches_formset = SearchNoMatchesFormSet(prefix="no_matches")
        search_multiple_matches_formset = SearchMultipleMatchesFormSet(prefix="multiple_matches")
        search_one_match_formset = SearchOneMatchFormSet(prefix="one_match")
    else:
        search_initial_form = SearchInitialForm(request.POST)
        search_no_matches_formset = SearchNoMatchesFormSet(request.POST, prefix="no_matches")
        search_multiple_matches_formset = SearchMultipleMatchesFormSet(request.POST, prefix="multiple_matches")
        search_one_match_formset = SearchOneMatchFormSet(request.POST, prefix="one_match")

        for form in search_multiple_matches_formset.forms:
            search_term_key = f"{form.prefix}-search_term"
            search_term = request.POST.get(search_term_key)

            if search_term:
                search_results = HgncGene.objects.find_matching_items({search_term})
                if search_results['multiple_matches'] and search_results['multiple_matches'][0]['search_string'] == search_term:
                    result_items = search_results['multiple_matches'][0]['items']
                    item_choices = [(item.id, str(item)) for item in result_items]
                    form.fields['item_id'].choices = form.fields['item_id'].choices + item_choices

        if all([
            search_initial_form.is_valid(),
            search_no_matches_formset.is_valid(),
            search_multiple_matches_formset.is_valid(),
            search_one_match_formset.is_valid(),
        ]):
            # Get newly submitted search terms
            search_terms = search_initial_form.cleaned_data['search_terms']
            for form in search_no_matches_formset:
                if form.cleaned_data.get('search_term'):
                    search_terms.add(form.cleaned_data['search_term'])

            # Process selections and find unresolved multiple-match terms
            selections_from_multiple_matches_formset = []
            for form in search_multiple_matches_formset:
                search_term = form.cleaned_data.get('search_term')
                if not search_term:
                    continue

                if form.cleaned_data.get('item_id'):
                    # User made a selection, process it
                    selected_id = int(form.cleaned_data['item_id'])
                    choices_dict = dict(form.fields['item_id'].choices)
                    item_string = choices_dict.get(selected_id)
                    selections_from_multiple_matches_formset.append(
                        (search_term, selected_id, item_string)
                    )
                else:
                    # No selection was made, add this term to be re-shown
                    search_terms.add(search_term)

            # Find matches for the new terms
            search_results = HgncGene.objects.find_matching_items(search_terms)

            # Regenerate forms for the next page view
            search_initial_form = SearchInitialForm() # Clear the initial form

            no_matches_initial = [{"search_term": term} for term in search_results['no_matches']]
            search_no_matches_formset = SearchNoMatchesFormSet(initial=no_matches_initial, prefix="no_matches")

            # Multiple matches formset (from combined and de-duplicated data)
            multiple_matches_data = search_results['multiple_matches'] 
            multiple_matches_initial = [{"search_term": result['search_string']} for result in multiple_matches_data]
            search_multiple_matches_formset = SearchMultipleMatchesFormSet(initial=multiple_matches_initial, prefix="multiple_matches")

            # Populate choices for the new multiple matches formset
            for i, form in enumerate(search_multiple_matches_formset):
                result_items = multiple_matches_data[i]['items']
                item_choices = [(item.id, str(item)) for item in result_items]
                # Add the null choice for the new forms
                form.fields['item_id'].choices = form.fields['item_id'].choices + item_choices


            # Populate new one_match formset
            final_one_match_data = {}
            # 1. Add items from the already submitted one_match_formset
            for form in search_one_match_formset:
                if form.cleaned_data.get('search_term'):
                    # We use the cleaned_data directly as it's already a dictionary
                    # in the correct format.
                    item_id = form.cleaned_data['item_id']
                    final_one_match_data[item_id] = form.cleaned_data

            # 2. Add newly found single matches from the latest search
            for result in search_results.get('one_match', []):
                item_data = {
                    'search_term': result['search_string'],
                    'item_id': result['item'].id,
                    'item_string': str(result['item']),
                }
                final_one_match_data[item_data['item_id']] = item_data

            # 3. Add items that were just selected from the multiple matches formset
            for search_term, item_id, item_string in selections_from_multiple_matches_formset:
                item_data = {
                    'search_term': search_term,
                    'item_id': item_id,
                    'item_string': item_string,
                }
                final_one_match_data[item_data['item_id']] = item_data

            one_match_initial = list(final_one_match_data.values())

            # Now, create the new formset with the combined and de-duplicated initial data
            search_one_match_formset = SearchOneMatchFormSet(
                initial=one_match_initial,
                prefix="one_match"
            )

            print(len(no_matches_initial), len(multiple_matches_initial), len(one_match_initial))

    # Add forms to context and render
    context['search_initial_form'] = search_initial_form
    context['search_no_matches_formset'] = search_no_matches_formset
    context['search_multiple_matches_formset'] = search_multiple_matches_formset
    context['search_one_match_formset'] = search_one_match_formset

    return render(request, 'sickgenes/molecule_match.html', context)