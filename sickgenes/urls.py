from django.urls import path
from . import views

app_name = 'sickgenes'
urlpatterns = [
    path('manage/add_gene_findings/<int:study_cohort_id>/<str:gene_finding_type>/', views.add_gene_findings, name="add_gene_findings"),
    path('manage/add_study/', views.add_study, name="add_study"),
    path('study/<int:study_id>/', views.study, name="study"),
    path('manage/add_study_cohort/<int:study_id>/', views.add_study_cohort, name="add_study_cohort"),
]