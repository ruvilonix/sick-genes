from django import forms
from sickgenes.models import Study, StudyCohort

class StudyForm(forms.ModelForm):
    class Meta:
        model = Study
        fields = ['title', 'doi', 'publisher_url', 's4me_url', 'preprint']

class StudyCohortForm(forms.ModelForm):
    class Meta:
        model = StudyCohort
        fields = ['disease', 'control']