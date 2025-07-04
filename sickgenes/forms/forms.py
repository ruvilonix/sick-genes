from django import forms
from sickgenes.models import Study

class StudyForm(forms.ModelForm):
    class Meta:
        model = Study
        fields = ['title', 'doi', 'publisher_url', 's4me_url', 'preprint']