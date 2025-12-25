from django.contrib import admin

from .models import (
    Study, GeneFinding, StudyCohort, Disease, HgncGene, 
    HmdbMetabolite, Ena, UniprotId, OmimId, AliasSymbol, 
    AliasName, PrevSymbol, PrevName, MetaboliteSynonym, SecondaryAccession,
    MetaboliteFinding, StringProtein, StringInteraction, SiteConfiguration
)

from solo.admin import SingletonModelAdmin

admin.site.register(SiteConfiguration, SingletonModelAdmin)

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
    
class StudyCohortInline(admin.TabularInline):
    model = StudyCohort
    extra = 0
    show_change_link = True

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ['title', 'not_finished']
    inlines = [
        StudyCohortInline,
    ]

@admin.register(StudyCohort)
class StudyCohortAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('study').prefetch_related('disease_tags')
        return qs

admin.site.register(Disease)

admin.site.register(MetaboliteFinding)

## HGNC

class EnaInline(admin.TabularInline):
    model = Ena
class UniprotIdInline(admin.TabularInline):
    model = UniprotId
class OmimIdInline(admin.TabularInline):
    model = OmimId
class AliasSymbolInline(admin.TabularInline):
    model = AliasSymbol
class AliasNameInline(admin.TabularInline):
    model = AliasName
class PrevSymbolInline(admin.TabularInline):
    model = PrevSymbol
class PrevNameInline(admin.TabularInline):
    model = PrevName

@admin.register(HgncGene)
class HgncGeneAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['hgnc_id', 'symbol', 'name']
    readonly_fields = ['created_at', 'updated_at']

    inlines = [
        EnaInline,
        UniprotIdInline,
        OmimIdInline,
        AliasSymbolInline,
        AliasNameInline,
        PrevSymbolInline,
        PrevNameInline,
    ]

## HMDB

class MetaboliteSynonymInline(admin.TabularInline):
    model = MetaboliteSynonym
class SecondaryAccessionInline(admin.TabularInline):
    model = SecondaryAccession

@admin.register(HmdbMetabolite)
class HmdbMetaboliteAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['accession', 'name']
    readonly_fields = ['created_at', 'updated_at']

    inlines = [MetaboliteSynonymInline, SecondaryAccessionInline]


## STRING

@admin.register(StringProtein)
class StringProteinAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['protein_id']
    pass

@admin.register(StringInteraction)
class StringInteractionAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    search_fields = ['protein1', 'protein2']
    list_select_related = ['protein1', 'protein2']
    pass