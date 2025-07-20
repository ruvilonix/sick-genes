Overview
--------

The purpose of this database is to identify genes of interest in disease phenotypes compared to healthy populations, enabling cross-study comparison and replication analysis.

## Genes to Include

#### Primary Inclusion Criteria

*   **Gene product levels:** Level of a gene product is significantly associated with having the phenotype in question (the phenotype(s) assigned to the Study Cohort being edited)
    
*   **Coding mutations:** Gene where a mutation within the coding region is significantly associated with the phenotype
    
*   **Regulatory mutations:** Gene where a mutation near the coding region is significantly associated with the phenotype, and the paper suggests or mentions the nearby gene as potentially interesting for this reason
    
*   **Cell type markers:** A gene that identifies a cell type, where the cell type is significantly increased or decreased (e.g., CD8+ T cells), even if the gene itself wasn't directly measured
    
*   **Machine learning identified:** A gene predicted to be of interest based on machine learning algorithms, including genes that were not individually significant but were part of a gene panel that significantly discriminated between groups in ML analysis
        
*   **Severity associations:** Any of the above but associated with the severity/amount of the phenotype instead of with another group
    
*   **Longitudinal studies:** If a gene is significant at any timepoint in a longitudinal study, include it
    

#### Protein Complexes and Heterodimers

*   **Simple complexes (≤3 components):** Include all constituent genes when the complex is significantly associated with the phenotype (e.g., TSH → include TSHB and CGA)
    
*   **Ambiguous cases:** When authors cannot discriminate between similar genes (e.g., IGHV3-23/30), include all mentioned genes
    
*   **Complex assemblies (5+ components):** Do not include constituent genes due to unclear biological relevance of individual components
    
---

## Genes to NOT Include

*   **External database predictions:** Genes predicted to be of interest based on predictions made using external protein-protein or gene-gene interaction databases (e.g., GSEA or STRING network analysis)
    
*   **Rare mutations without controls:** Rare mutations related to a gene, but without a comparison group to determine significance
    
*   **Disease vs. disease only:** Do not store genes from studies that only compare diseased groups without healthy controls
    
*   **Complex protein assemblies:** Constituent genes of protein complexes with 5 or more components
    

---

## Statistical Significance Criteria

#### P-value Thresholds

*   Genes are primarily limited to those that pass a p-value threshold defined in the paper, or 0.05 if none is specified
    
*   **Exception:** If authors mention a finding because it approaches significance (e.g., p=0.053) and believe it may be important, it can be added
    
*   **Multiple testing correction:** If authors performed multiple test correction, use the adjusted p-value. If not, use the nominal p-value
    

--- 

## Special Cases and Notes

#### Multiple Phenotype Comparisons

*   **Disease A vs. Disease B only:** Do not store genes from studies that only compare diseased groups without healthy controls
    
*   **Multiple diseases with healthy controls:** If multiple phenotypes and healthy controls are compared for a gene, only store the gene for phenotypes that are significantly different from healthy controls