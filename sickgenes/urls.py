from django.urls import path
from . import views

app_name = 'sickgenes'
urlpatterns = [
    path('manage/add_study/', views.add_study, name="add_study"),
    path('study/<int:study_id>/', views.study, name="study"),
    path('manage/add_study_cohort/<int:study_id>/', views.add_study_cohort, name="add_study_cohort"),
    path('fetch_paper_info/', views.fetch_paper_info, name='fetch_paper_info'),

    path('search/identify/<str:model_type>/', views.identify_molecules, name='identify_molecules'),
    path('manage/<int:study_cohort_id>/<str:model_type>/insert/', views.insert_findings, name='insert_findings'),

    path('graph/retrieve-network/', views.gene_network_data, name="gene_network_data"),
    path('graph/display/', views.graph_display, name='graph_display'),
]