import django_tables2 as tables
from .models import HgncGene, Study

# Bootstrap classes for columns: keep short values on one line, and hide less
# important columns on narrow screens
NO_WRAP = {"th": {"class": "text-nowrap"}, "td": {"class": "text-nowrap"}}
NUMBER = {"th": {"class": "text-end text-nowrap"}, "td": {"class": "text-end"}}
HIDE_BELOW_MD = {"th": {"class": "d-none d-md-table-cell"}, "td": {"class": "d-none d-md-table-cell"}}
HIDE_BELOW_LG = {
    "th": {"class": "d-none d-lg-table-cell text-nowrap"},
    "td": {"class": "d-none d-lg-table-cell text-nowrap"},
}


class GeneTable(tables.Table):
    study_count = tables.Column(verbose_name="Studies", attrs=NUMBER)
    symbol = tables.Column(linkify=True, attrs=NO_WRAP)

    class Meta:
        model = HgncGene
        fields = ("symbol", "name", "study_count")
        order_by = ("-study_count", "symbol")

class StudyTable(tables.Table):
    gene_count = tables.Column(verbose_name="Genes", attrs=NUMBER)
    title = tables.Column(linkify=True)
    short_authors = tables.Column(
        verbose_name='Authors',
        order_by='authors',
        attrs=HIDE_BELOW_MD,
    )

    publication_date = tables.Column(
        verbose_name="Published",
        order_by=("publication_year", "publication_month", "publication_day"),
        attrs=NO_WRAP,
    )

    created_at = tables.DateColumn(format="d M Y", verbose_name="Added", attrs=HIDE_BELOW_LG)

    class Meta:
        model = Study
        fields = ("title", "publication_date", "short_authors", "gene_count", "created_at")
        order_by = ("-created_at")
