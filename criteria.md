The purpose of this database is to identify genes of interest in disease phenotypes compared to healthy populations, enabling cross-study comparison and replication analysis.

## Genes to Include

#### Primary Inclusion Criteria

*   **Gene product levels:** Level of a gene product is significantly associated with having the phenotype in question (the phenotype(s) assigned to the Study Cohort being edited)
    
*   **Coding mutations:** Gene where a mutation within the coding region is significantly associated with the phenotype
    
*   **Regulatory mutations:** Gene where a mutation near the coding region is significantly associated with the phenotype, and the paper suggests or mentions the nearby gene as potentially interesting for this reason
    
*   **Cell type markers:** A gene that identifies a cell type, where the cell type is significantly increased or decreased (e.g., CD8+ T cells), even if the gene itself wasn't directly measured

*   **Genes altered after in vitro stimulation:** A gene that has a significantly different change after in vitro stimulation than in healthy controls. 

Example where IFNG and TNF would be saved for both ME/CFS and long COVID cohorts (1):
> "We designed a classic ICS assay to provide a direct measure of the functional capabilities of magnet-enriched fresh CD8 T-cells in a format that would be easy to adapt to clinical testing. These functional ICS assays showed that CD8 T-cells of ME/CFS and Long COVID patients had a significantly diminished capacity to produce both cytokines, **IFNγ** or **TNFα**, after PMA stimulation when compared to HC as seen in representative FACS plots (Fig. S1) and following statistical analysis of multiple individuals from each group (Fig. 1)."

*   **Gene product shape or activity different:** Example [2]:
> Recordings of TRPM3 ion channel currents were obtained from freshly isolated NK cells from HC, post-COVID-19 condition patients, and ME/CFS patients using the whole-cell patch-clamp electrophysiological technique. Endogenous TRPM3 function was rapidly and reversibly activated by application of 100 μM PregS. We found a significant difference among three groups of ionic current amplitude after PregS stimulation (p < 0.0001).
        
*   **Severity associations:** Any of the above but associated with the severity/amount of the phenotype instead of with another group
    
*   **Longitudinal studies:** If a gene is significant at any timepoint in a longitudinal study, include it
    

#### Protein Complexes and Heterodimers

*   **Simple complexes (≤3 components):** Include all constituent genes when the complex is significantly associated with the phenotype (e.g., TSH → include TSHB and CGA)
    
*   **Ambiguous cases:** When authors cannot discriminate between similar genes (e.g., IGHV3-23/30), include all mentioned genes
        
---

## Genes to NOT Include

*   **External database predictions:** Genes predicted to be of interest based on predictions made using external protein-protein or gene-gene interaction databases (e.g., GSEA or STRING network analysis)
    
*   **Rare mutations without controls:** Rare mutations related to a gene, but without a comparison group to determine significance
    
*   **Disease vs. disease only:** Do not store genes from studies that only compare groups that have health conditions without healthy controls
    
*   **Complex protein assemblies:** Constituent genes of protein complexes with 4 or more components

*   **Machine learning identified:** A gene predicted to be of interest based on machine learning algorithms, including genes that were not individually significant but were part of a gene panel that significantly discriminated between groups in ML analysis
    

---

## Statistical Significance Criteria

#### P-value Thresholds

*   Genes are primarily limited to those that pass a p-value threshold defined in the paper, or 0.05 if none is specified.
    
*   **Exception:** If authors mention a finding because it approaches significance (e.g., p=0.053) and believe it may be important, it can be added.
    
*   **Multiple testing correction:** If authors performed multiple test correction, use the adjusted p-value. If not, use the nominal p-value.
    
---

### References

[1] Gil, Anna, et al. “Identification of CD8 T-Cell Dysfunction Associated with Symptoms in Myalgic Encephalomyelitis/Chronic Fatigue Syndrome (ME/CFS) and Long COVID and Treatment with a Nebulized Antioxidant/Anti-Pathogen Agent in a Retrospective Case Series.” Brain, Behavior, & Immunity. Health, 1 Dec. 2023, pp. 100720–100720, https://doi.org/10.1016/j.bbih.2023.100720.

[2] Sasso, E. M., Muraki, K., Eaton-Fitch, N., Smith, P., Jeremijenko, A., Griffin, P., & Marshall-Gradisnik, S. (2024). Investigation into the restoration of TRPM3 ion channel activity in post-COVID-19 condition: a potential pharmacotherapeutic target. Frontiers in Immunology, 15. https://doi.org/10.3389/fimmu.2024.1264702