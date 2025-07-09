from django import forms
from sickgenes.models import Study, StudyCohort

class StudyForm(forms.ModelForm):
    class Meta:
        model = Study
        fields = ['title', 'doi', 'authors', 'publication_year', 'publication_month', 'publication_day', 'publisher_url', 's4me_url', 'preprint']



class StudyCohortForm(forms.ModelForm):
    class Meta:
        model = StudyCohort
        fields = ['disease_tags', 'control_tags', 'note']