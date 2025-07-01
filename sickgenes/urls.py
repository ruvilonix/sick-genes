from django.urls import path
from sickgenes.views import add_genes

app_name = 'sickgenes'
urlpatterns = [
    path('manage/add_genes/', add_genes, name="add_genes"),
]