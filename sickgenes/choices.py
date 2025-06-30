from django.db import models

class HgncGeneExtraFieldType(models.TextChoices):
    ENTREZ_ID = "ENT", "Entrez gene ID"
    ENSEMBLE_GENE_ID = "ENS", "Ensembl gene ID"
    VEGA_ID = "VEG", "Vega gene ID"
    UCSC_ID = "UCS", "UCSC gene ID"
    ENA = "ENA", "International Nucleotide Sequence Database Collaboration accession number"
    UNIPROT_ID = "UNI", "UniProt Protein Accession"
    PUBMED_ID = "PUB", "Pubmed PMID"
    OMIM_ID = "OMI", "Online Mendelian Inheritance in Man (OMIM) ID"
    ALIAS_SYMBOL = "ALS", "Alias symbol"
    ALIAS_NAME = "ALN", "Alias name"
    PREV_SYMBOL = "PRA", "Previous symbol"
    PREV_NAME = "PRN", "Previous name"