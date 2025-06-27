from django import forms

class MoleculeMatchForm(forms.Form):
    molecule_list = forms.CharField(
        widget=forms.Textarea(),
        required=False,
    )

    matching_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )