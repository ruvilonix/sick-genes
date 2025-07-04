from django.urls import path
from . import views

app_name = 'sickgenes'
urlpatterns = [
    path('manage/add_genes/', views.add_genes, name="add_genes"),
    path('manage/add_study/', views.add_study, name="add_study"),
    path('study/<int:pk>/', views.study, name="study")
]