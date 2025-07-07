from django.contrib import admin

from .models import Study, GeneFinding, StudyCohort, Disease, HgncGene, HmdbMetabolite

class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(GeneFinding)
class GeneFindingAdmin(admin.ModelAdmin):
    readonly_fields = ['study_cohort', 'hgnc_gene']

admin.site.register(Study)
admin.site.register(StudyCohort)
admin.site.register(Disease)

@admin.register(HgncGene)
class HgncGeneAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['hgnc_id', 'symbol', 'name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(HmdbMetabolite)
class HmdbMetaboliteAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['accession', 'name']
    readonly_fields = ['created_at', 'updated_at']