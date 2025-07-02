from django import forms
from django.forms import formset_factory

class SearchInitialForm(forms.Form):
    search_terms = forms.CharField(
        widget=forms.Textarea(),
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
    search_term = forms.CharField(max_length=300, required=False)
    delete = forms.BooleanField(required=False)

SearchNoMatchesFormSet = formset_factory(SearchNoMatchesForm, extra=0)

class SearchMultipleMatchesForm(forms.Form):
    search_term = forms.CharField(max_length=300, required=False)
    item_id = forms.ChoiceField(required=False)

SearchMultipleMatchesFormSet = formset_factory(SearchMultipleMatchesForm, extra=0)
