from django.urls import path
from sickgenes.views import MoleculeMatchView

app_name = 'sickgenes'
urlpatterns = [
    path('manage/add_molecules/', MoleculeMatchView.as_view(), name='add_molecules'),
]