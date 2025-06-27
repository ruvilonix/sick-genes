from django.contrib import admin

from .models import Study, Finding, Molecule, MoleculeAlias, StudyCohort, Disease

class MoleculeAdmin(admin.ModelAdmin):
    search_fields = ['hgnc_symbol', 'hgnc_id', 'hmdb_accession', 'hmdb_name']

class MoleculeAliasAdmin(admin.ModelAdmin):
    readonly_fields = ['molecule']
    search_fields = ['alias']

class FindingAdmin(admin.ModelAdmin):
    readonly_fields = ['study_cohort', 'molecule']

admin.site.register(Study)
admin.site.register(Finding, FindingAdmin)
admin.site.register(Molecule, MoleculeAdmin)
admin.site.register(MoleculeAlias, MoleculeAliasAdmin)
admin.site.register(StudyCohort)
admin.site.register(Disease)