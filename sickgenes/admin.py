from django.contrib import admin

from .models import Study, GeneFinding, StudyCohort, Disease, HgncGene

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

