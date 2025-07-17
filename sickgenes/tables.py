import django_tables2 as tables
from .models import HgncGene, Study

class GeneTable(tables.Table):
    study_count = tables.Column(verbose_name="# of Studies")
    symbol = tables.Column(linkify=True)

    class Meta:
        model = HgncGene
        fields = ("symbol", "name", "study_count")
        order_by = ("-study_count", "symbol")

class StudyTable(tables.Table):
    gene_count = tables.Column(verbose_name="# of Genes")
    title = tables.Column(linkify=True)

    class Meta:
        model = Study
        fields = ("title", "authors", "gene_count", "created_at")
        order_by = ("-study_count", "symbol")
