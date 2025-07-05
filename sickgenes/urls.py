from django.urls import path
from . import views

app_name = 'sickgenes'
urlpatterns = [
    path('manage/add_genes/<int:study_cohort_id>/<str:gene_finding_type>/', views.add_genes, name="add_genes"),
    path('manage/add_study/', views.add_study, name="add_study"),
    path('study/<int:study_id>/', views.study, name="study"),
    path('manage/add_study_cohort/<int:study_id>/', views.add_study_cohort, name="add_study_cohort"),
]