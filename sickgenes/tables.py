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
    short_authors = tables.Column(verbose_name='Authors')

    publication_date = tables.Column(
        verbose_name="Published", 
        order_by=("publication_year", "publication_month", "publication_day")
    )
    
    created_at = tables.DateColumn(format="d M Y", verbose_name="Date Added")

    class Meta:
        model = Study
        fields = ("title", "publication_date", "short_authors", "gene_count", "created_at")
        order_by = ("-created_at")
