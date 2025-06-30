from django import forms

class MoleculeMatchForm(forms.Form):
    search_terms = forms.CharField(
        widget=forms.Textarea(),
        required=False,
    )

    matching_data = forms.CharField(
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