from django import forms
from django.forms import formset_factory

class SearchInitialForm(forms.Form):
    search_terms = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
        required=False,
    )

    def clean_search_terms(self):
        search_terms_string = self.cleaned_data['search_terms']

        search_terms = set()
        for search_string in search_terms_string.splitlines():
            search_string = search_string.strip()
            if search_string:
                search_terms.add(search_string)

        return search_terms
    
class SearchNoMatchesForm(forms.Form):
    search_term = forms.CharField(
        max_length=300, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    delete = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

SearchNoMatchesFormSet = formset_factory(SearchNoMatchesForm, extra=0)

class SearchMultipleMatchesForm(forms.Form):
    search_term = forms.CharField(
        max_length=300, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True})
    )
    item_id = forms.ChoiceField(
        choices=[('', 'Please select one')], required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    delete = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


SearchMultipleMatchesFormSet = formset_factory(SearchMultipleMatchesForm, extra=0)


class SearchOneMatchForm(forms.Form):
    search_term = forms.CharField(
        max_length=300, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True})
    )
    item_id = forms.IntegerField(widget=forms.HiddenInput())
    item_string = forms.CharField(
        max_length=300, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True})
    )
    delete = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

SearchOneMatchFormSet = formset_factory(SearchOneMatchForm, extra=0)

def prepare_identifiers(request, model):
    """Prepare forms/formsets for retrieving IDs for items (genes) from a list of search terms
    
    Args: 
        request, model
        
    Returns:
        form_data = {
            'search_initial_form': <>,
            'search_no_matches_formset': <>,
            'search_multiple_matches_formset': <>,
            'search_one_match_formset': <>,
            'items_only_exist_in_one_match': <>,
        }
    """

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
        form_data = process_search_forms(form_data, model)

    return form_data

def process_search_forms(
            form_data,
            model,
        ):
    
    search_initial_form = form_data['search_initial_form']
    search_no_matches_formset = form_data['search_no_matches_formset']
    search_multiple_matches_formset = form_data['search_multiple_matches_formset']
    search_one_match_formset = form_data['search_one_match_formset']

    # Retrieve matches for search term in each form to generate choices
    for form in search_multiple_matches_formset.forms:
        search_term = form['search_term'].value()

        if search_term:
            search_results = model.objects.find_matching_items({search_term})
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
            if form.cleaned_data.get('search_term') and not form.cleaned_data.get('delete'):
                search_terms.add(form.cleaned_data['search_term'])

        # Process selections from multiple_matches forms
        selections_from_multiple_matches_formset = []
        for form in search_multiple_matches_formset:
            search_term = form.cleaned_data.get('search_term')
            if not search_term or form.cleaned_data.get('delete'):
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
        search_results = model.objects.find_matching_items(search_terms)

        # Regenerate forms for the next page view
        # Blank initial form
        search_initial_form = SearchInitialForm() # Clear the initial form

        # No matches formset from no_matches in search_results
        no_matches_initial = [{"search_term": term} for term in search_results['no_matches']]
        search_no_matches_formset = SearchNoMatchesFormSet(initial=no_matches_initial, prefix="no_matches")

        # Multiple matches formset from multiple_matches in search_results
        multiple_matches_data = search_results['multiple_matches']
        multiple_matches_initial = []
        for result in multiple_matches_data:
            initial_data = {'search_term': result['search_string']}
            # Check for an exact case-insensitive match to set as a default
            for item in result['items']:
                if str(item).lower() == result['search_string'].lower():
                    initial_data['item_id'] = item.id
                    break
            multiple_matches_initial.append(initial_data)
        
        search_multiple_matches_formset = SearchMultipleMatchesFormSet(
            initial=multiple_matches_initial, prefix="multiple_matches"
        )

        # Populate choices for the new multiple matches formset
        for i, form in enumerate(search_multiple_matches_formset):
            result_items = multiple_matches_data[i]['items']
            item_choices = [(item.id, str(item)) for item in result_items]
            form.fields['item_id'].choices += item_choices



        # Populate new one_match formset
        final_one_match_data = {}
        # 1. Add items from the already submitted one_match_formset
        for form in search_one_match_formset:
            if form.cleaned_data.get('search_term') and not form.cleaned_data.get('delete'):
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

        items_only_exist_in_one_match = all([
            (len(no_matches_initial) == 0),
            (len(multiple_matches_initial) == 0),
            (len(one_match_initial) > 0)
        ])

        new_form_data = {
            "search_initial_form": search_initial_form,
            "search_no_matches_formset": search_no_matches_formset,
            "search_multiple_matches_formset": search_multiple_matches_formset,
            "search_one_match_formset": search_one_match_formset,
            "items_only_exist_in_one_match": items_only_exist_in_one_match,
        }

        return new_form_data