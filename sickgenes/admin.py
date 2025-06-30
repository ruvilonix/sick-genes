from django.contrib import admin

from .models import Study, Finding, Molecule, MoleculeAlias, StudyCohort, Disease, HgncGene, HgncGeneExtra

class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

class MoleculeAliasInline(admin.TabularInline):
    model = MoleculeAlias
    extra = 0
    show_change_link = True

@admin.register(Molecule)
class MoleculeAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['hgnc_symbol', 'hgnc_id', 'hmdb_accession', 'hmdb_name']
    inlines = [MoleculeAliasInline]
    list_filter = ['type']

@admin.register(MoleculeAlias)
class MoleculeAliasAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['alias']

@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    readonly_fields = ['study_cohort', 'molecule']

admin.site.register(Study)
admin.site.register(StudyCohort)
admin.site.register(Disease)

@admin.register(HgncGene)
class HgncGeneAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['hgnc_id', 'symbol', 'name']

@admin.register(HgncGeneExtra)
class HgncGeneExtraAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['value']
    list_filter = ['field_name']