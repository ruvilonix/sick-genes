from django.urls import path
from sickgenes.views import add_molecules

app_name = 'sickgenes'
urlpatterns = [
    path('manage/add_molecules/', add_molecules, name='add_molecules'),
]