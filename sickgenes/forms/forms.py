from django import forms
from sickgenes.models import Study, StudyCohort

class StudyForm(forms.ModelForm):
    class Meta:
        model = Study
        fields = ['title', 'doi', 'authors', 'publication_date', 'publisher_url', 's4me_url', 'preprint']
        widgets = {
            'publication_date': forms.DateInput(attrs={'type': 'date'}),
        }


class StudyCohortForm(forms.ModelForm):
    class Meta:
        model = StudyCohort
        fields = ['disease_tags', 'control_tags', 'note']