import django_tables2 as tables
from .models import HgncGene

class GeneTable(tables.Table):
    study_count = tables.Column(verbose_name="# of Studies")
    symbol = tables.Column(linkify=True)

    class Meta:
        model = HgncGene
        template_name = "django_tables2/bootstrap5.html" 
        fields = ("symbol", "name", "study_count")
        order_by = ("-study_count", "symbol")
