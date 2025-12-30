from django.urls import path
from . import views

app_name = 'sickgenes'
urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('about/criteria/', views.criteria, name='criteria'),
    
    path('studies/', views.study_list, name='study_list'),
    path('study/<int:study_id>/', views.study, name="study"),
    path('study/<slug:slug>.<int:study_id>/', views.study, name="study"),

    path('genes/', views.gene_list, name='gene_list'),
    path('gene/<str:hgnc_symbol>/', views.gene_detail, name='gene_detail'),
    path('search/identify/<str:model_type>/', views.identify_molecules, name='identify_molecules'),

    path('manage/add_study/', views.add_study, name="add_study"),
    path('fetch_paper_info/', views.fetch_paper_info, name='fetch_paper_info'),

    path('manage/add_study_cohort/<int:study_id>/', views.add_study_cohort, name="add_study_cohort"),

    path('manage/<int:study_cohort_id>/<str:model_type>/insert/', views.insert_findings, name='insert_findings'),

    path('graph/retrieve-network/', views.gene_network_data, name="gene_network_data"),
    path('graph/display/', views.graph_display, name='graph_display'),

    path('api/v1/dump/', views.database_dump_json, name="database_dump_json"),
]