from django import forms
from sickgenes.models import Study, StudyCohort, Disease
import datetime
from django.db.models import Count, Q

class StudyForm(forms.ModelForm):
    class Meta:
        model = Study
        fields = ['doi', 'title', 'authors', 'publication_year', 'publication_month', 'publication_day', 'journal_titles', 'publisher_url', 's4me_url', 'preprint']

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        last_20_cohort_pks = StudyCohort.objects.order_by('-created_at').values_list('pk', flat=True)[:20]

        disease_queryset = Disease.objects.annotate(
            recent_cohort_count=Count('study_cohorts', filter=Q(study_cohorts__pk__in=list(last_20_cohort_pks))),
            total_cohort_count=Count('study_cohorts')
        ).order_by('-recent_cohort_count', '-total_cohort_count', 'name')

        self.fields['disease_tags'].queryset = disease_queryset

    class Meta:
        model = StudyCohort
        fields = ['disease_tags', 'note']

    
class GeneFilterForm(forms.Form):
    disease = forms.ModelChoiceField(
        queryset=Disease.objects.all().order_by('name'),
        required=False,
        empty_label="All Diseases",
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
    )