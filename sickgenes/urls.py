from django.urls import path
from django.views.generic import RedirectView
from . import views
from django.views.generic import TemplateView

app_name = 'sickgenes'
urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    # The criteria page was merged into the about page
    path('about/criteria/', RedirectView.as_view(pattern_name='sickgenes:about', permanent=True)),
    
    path('studies/', views.study_list, name='study_list'),
    path('table-study/', views.table_study, name="TableStudy"),
    path('table-study/phenotype/<int:phenotype_id>/', views.table_study, name="TableStudy"),

    path('study/<int:study_id>/', views.study, name="study"),
    path('study/<slug:slug>.<int:study_id>/', views.study, name="study"),

    path('study/<int:study_id>/set-newest-version/', views.set_newest_study_version, name='set_newest_study_version'),

    path('genes/', views.gene_list, name='gene_list'),
    path('gene/<str:hgnc_symbol>/', views.gene_detail, name='gene_detail'),
    path('search/identify/<str:model_type>/', views.identify_molecules, name='identify_molecules'),

    path('manage/add_study/', views.add_study, name="add_study"),
    path('fetch_paper_info/', views.fetch_paper_info, name='fetch_paper_info'),

    path('manage/add_study_cohort/<int:study_id>/', views.add_study_cohort, name="add_study_cohort"),

    path('manage/<int:study_cohort_id>/<str:model_type>/insert/', views.insert_findings, name='insert_findings'),
    path('manage/<int:study_cohort_id>/gene/remove/', views.remove_findings, name='remove_findings'),


    path('api/v1/dump/', views.database_dump_json_v1, name="database_dump_json_v1"),
    path('api/v2/sickgenes_database.json.gz', views.database_dump_json_v2, name="database_dump_json_v2"),

    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),

]