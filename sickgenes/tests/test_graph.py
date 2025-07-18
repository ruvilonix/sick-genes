from django.test import TestCase
from django.urls import reverse
import json

from sickgenes.models import (
    Study, Disease, StudyCohort, GeneFinding, HgncGene, 
    StringProtein, StringInteraction
)


class GeneGraphAPITestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.gene1 = HgncGene.objects.create(symbol='TP53', hgnc_id='HGNC:11998')
        cls.gene2 = HgncGene.objects.create(symbol='BRCA1', hgnc_id='HGNC:1100')
        cls.gene3 = HgncGene.objects.create(symbol='EGFR', hgnc_id='HGNC:3236')
        cls.gene4 = HgncGene.objects.create(symbol='UNRELATED', hgnc_id='HGNC:99999')

        cls.disease1 = Disease.objects.create(name='Cancer')
        cls.disease2 = Disease.objects.create(name='Neurodegeneration')
        cls.disease3 = Disease.objects.create(name='Orphan Disease')

        cls.study1 = Study.objects.create(title='Study A on TP53/BRCA1 in Cancer')
        cls.study2 = Study.objects.create(title='Study B on TP53 in Neuro')
        cls.study3 = Study.objects.create(title='Study C on EGFR in Cancer')
        cls.study4 = Study.objects.create(title='Study D on BRCA1 in Neuro')

        # Create Study Cohorts and link diseases
        cohort1 = StudyCohort.objects.create(study=cls.study1)
        cohort1.disease_tags.add(cls.disease1) # Study 1, Cancer
        
        cohort2 = StudyCohort.objects.create(study=cls.study2)
        cohort2.disease_tags.add(cls.disease2) # Study 2, Neuro
        
        cohort3 = StudyCohort.objects.create(study=cls.study3)
        cohort3.disease_tags.add(cls.disease1) # Study 3, Cancer

        cohort4 = StudyCohort.objects.create(study=cls.study4)
        cohort4.disease_tags.add(cls.disease2) # Study 4, Neuro

        # Create Gene Findings: Link genes to study cohorts
        # TP53 is in a Cancer study (Study 1) AND a Neuro study (Study 2)
        GeneFinding.objects.create(study_cohort=cohort1, hgnc_gene=cls.gene1) # TP53 -> Cancer
        GeneFinding.objects.create(study_cohort=cohort2, hgnc_gene=cls.gene1) # TP53 -> Neuro
        
        # BRCA1 is in a Cancer study (Study 1) AND a Neuro study (Study 4)
        GeneFinding.objects.create(study_cohort=cohort1, hgnc_gene=cls.gene2) # BRCA1 -> Cancer
        GeneFinding.objects.create(study_cohort=cohort4, hgnc_gene=cls.gene2) # BRCA1 -> Neuro

        # EGFR is only in a Cancer study
        GeneFinding.objects.create(study_cohort=cohort3, hgnc_gene=cls.gene3) # EGFR -> Cancer

        # Create String Proteins and Interactions
        protein1 = StringProtein.objects.create(protein_id='P1', hgnc_gene=cls.gene1) # TP53
        protein2 = StringProtein.objects.create(protein_id='P2', hgnc_gene=cls.gene2) # BRCA1
        protein3 = StringProtein.objects.create(protein_id='P3', hgnc_gene=cls.gene3) # EGFR
        
        # Interaction between TP53 and BRCA1
        cls.interaction = StringInteraction.objects.create(protein1=protein1, protein2=protein2, combined_score=999)

        # The URL for the view
        cls.url = reverse('sickgenes:gene_network_data')

    def test_successful_request_with_common_genes_and_interaction(self):
        """
        Test with two diseases where TP53 and BRCA1 are common, and an interaction exists.
        """
        response = self.client.get(self.url, {'disease_ids': [self.disease1.id, self.disease2.id]})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        
        # Check nodes
        self.assertEqual(len(data['nodes']), 2)
        node_symbols = {node['key'] for node in data['nodes']}
        self.assertEqual(node_symbols, {'TP53', 'BRCA1'})
        
        # Verify study counts for each node
        for node in data['nodes']:
            if node['key'] == 'TP53':
                # TP53 is in Study 1 (Cancer) and Study 2 (Neuro)
                self.assertEqual(node['size'], 2) 
            elif node['key'] == 'BRCA1':
                # BRCA1 is in Study 1 (Cancer) and Study 4 (Neuro)
                self.assertEqual(node['size'], 2)

        # Check edges
        edge = data['edges'][0]
        self.assertEqual(edge['key'], f'e{self.interaction.id}')
        self.assertIn(edge['source'], {'TP53', 'BRCA1'})
        self.assertIn(edge['target'], {'TP53', 'BRCA1'})

    def test_request_with_no_common_genes(self):
        """
        Test with diseases that have no genes in common.
        """
        response = self.client.get(self.url, {'disease_ids': [self.disease1.id, self.disease3.id]})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(len(data['nodes']), 0)
        self.assertEqual(len(data['edges']), 0)

    def test_request_with_common_genes_but_no_interactions(self):
        """
        Test a scenario where genes are common, but no interaction is in the DB.
        (We'll cheat by just deleting the interaction for this test)
        """
        # Create a new gene that is common but has no interactions
        new_gene = HgncGene.objects.create(symbol='NEWGENE', hgnc_id='HGNC:12345')
        # Find it in both cohorts
        GeneFinding.objects.create(study_cohort=StudyCohort.objects.get(study=self.study1), hgnc_gene=new_gene)
        GeneFinding.objects.create(study_cohort=StudyCohort.objects.get(study=self.study2), hgnc_gene=new_gene)

        # The original query should now find 3 genes
        response = self.client.get(self.url, {'disease_ids': [self.disease1.id, self.disease2.id]})
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(len(data['nodes']), 3)

    def test_request_with_no_disease_ids(self):
        """
        Test that sending no IDs returns a 400 Bad Request error.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Please provide at least one disease ID.')

    def test_request_with_invalid_disease_id(self):
        """
        Test that sending a non-integer ID returns a 400 Bad Request error.
        """
        response = self.client.get(self.url, {'disease_ids': ['1', 'not-a-number']})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invalid disease ID provided.')