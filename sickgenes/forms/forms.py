from django import forms
from sickgenes.models import Study, StudyCohort
import datetime

class StudyForm(forms.ModelForm):
    class Meta:
        model = Study
        fields = ['doi', 'title', 'authors', 'publication_year', 'publication_month', 'publication_day', 'publisher_url', 's4me_url', 'preprint']

    def clean_publication_year(self):
        year = self.cleaned_data.get('publication_year')
        return None if year == 0 else year

    def clean_publication_month(self):
        month = self.cleaned_data.get('publication_month')
        return None if month == 0 else month

    def clean_publication_day(self):
        day = self.cleaned_data.get('publication_day')
        return None if day == 0 else day
    
    def clean(self):
        cleaned_data = super().clean()

        year = cleaned_data.get('publication_year')
        month = cleaned_data.get('publication_month')
        day = cleaned_data.get('publication_day')

        if month and not year:
            self.add_error('publication_month', 'A year must be entered to specify a month.')

        if day and not month:
            self.add_error('publication_day', 'A month must be entered to specify a day.')

        if year and month and day:
            try:
                datetime.date(year, month, day)
            except ValueError:
                self.add_error('publication_day', f'The day ({day}) is not valid for the selected month and year.')
        
        return cleaned_data

class StudyCohortForm(forms.ModelForm):
    class Meta:
        model = StudyCohort
        fields = ['disease_tags', 'note']