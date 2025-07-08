from django.test import TestCase, SimpleTestCase
from django.core.management import call_command
from sickgenes.models import HgncGene, Study, Disease, StudyCohort, HmdbMetabolite
from io import StringIO
from django.utils import timezone
from django.urls import reverse

class ImportHgncTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.out = StringIO()
        cls.start_time = timezone.now()
        call_command('import_molecule_data', 'hgnc', test=True, stdout=cls.out)
        cls.end_time = timezone.now()

    def test_import_hgnc_success_message(self):
        self.assertIn('HGNC data successfully imported', self.out.getvalue())

    def test_hgnc_importer_imports_all_items_from_sample_data(self):
        genes = HgncGene.objects.all()
        self.assertEqual(genes.count(), 3)

    def test_all_hgnc_fields_are_saved(self):
        gene = HgncGene.objects.get(hgnc_id='HGNC:5')

        self.assertEqual(gene.symbol, 'A1BG')
        self.assertEqual(gene.name, 'alpha-1-B glycoprotein')
        self.assertEqual(gene.entrez_id, "1")
        self.assertEqual(gene.ensembl_gene_id, "ENSG00000121410")
        self.assertEqual(gene.vega_id, "OTTHUMG00000183507")
        self.assertEqual(gene.ucsc_id, "uc002qsd.5")
        self.assertCountEqual([ena.value for ena in gene.ena_set.all()], ['fake_ena'])
        self.assertCountEqual([uniprot_id.value for uniprot_id in gene.uniprotid_set.all()], ["P04217"])
        self.assertCountEqual([omim_id.value for omim_id in gene.omimid_set.all()], [138670])
        self.assertCountEqual([alias_symbol.value for alias_symbol in gene.aliassymbol_set.all()], ['fake_alias_symbol'])
        self.assertCountEqual([alias_name.value for alias_name in gene.aliasname_set.all()], ['fake1', 'fake2'])
        self.assertCountEqual([prev_name.value for prev_name in gene.prevname_set.all()], ['fake_prev_name'])
        self.assertCountEqual([prev_symbol.value for prev_symbol in gene.prevsymbol_set.all()], ['fake_prev_symbol', 'string, including comma'])

    def test_datetime_field_is_recent(self):
        gene = HgncGene.objects.get(hgnc_id='HGNC:5')

        self.assertGreaterEqual(gene.created_at, self.start_time)
        self.assertLessEqual(gene.created_at, self.end_time)

    def test_update_or_create_behavior(self):
        initial_count = HgncGene.objects.count()

        out = StringIO()
        call_command('import_molecule_data', 'hgnc', test=True, stdout=out)

        self.assertEqual(HgncGene.objects.count(), initial_count)

class ImportHmdbTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.out = StringIO()
        cls.start_time = timezone.now()
        call_command('import_molecule_data', 'hmdb', test=True, stdout=cls.out)
        cls.end_time = timezone.now()

    def test_import_hmdb_success_message(self):
        self.assertIn('HMDB data successfully imported', self.out.getvalue())

    def test_hmdb_importer_imports_all_items_from_sample_data(self):
        molecules = HmdbMetabolite.objects.all()
        # You'll need to adjust this count based on your actual sample HMDB test data
        self.assertEqual(molecules.count(), 3) 

    def test_long_iupac_name_does_not_save(self):
        molecule = HmdbMetabolite.objects.get(accession='HMDB0000002')
        self.assertEqual(molecule.iupac_name, None)

    def test_all_hmdb_fields_are_saved(self):
        molecule = HmdbMetabolite.objects.get(accession='HMDB0000005')

        self.assertEqual(molecule.name, '2-Ketobutyric acid')
        self.assertEqual(molecule.cas_registry_number, '600-18-0')
        self.assertEqual(molecule.drugbank_id, 'DB04553')
        self.assertEqual(molecule.foodb_id, 'FDB030356')
        self.assertEqual(molecule.knapsack_id, 'C00019675')
        self.assertEqual(molecule.biocyc_id, '2-OXOBUTANOATE')
        self.assertEqual(molecule.wikipedia_id, 'Alpha-Ketobutyric_acid')
        self.assertEqual(molecule.bigg_id, 33889)
        self.assertEqual(molecule.pubchem_compound_id, 58)
        self.assertEqual(molecule.chemspider_id, 57)
        self.assertEqual(molecule.chebi_id, 30831)
        self.assertCountEqual([secondary_accession.value for secondary_accession in molecule.secondary_accessions.all()], ['HMDB00005', 'HMDB0006544', 'HMDB06544'])
        self.assertCountEqual([synonym.value for synonym in molecule.synonyms.all()], [
            '2-Ketobutanoic acid', '2-Oxobutyric acid', '3-Methyl pyruvic acid',
            'alpha-Ketobutyrate', 'alpha-Ketobutyric acid', 'alpha-oxo-N-Butyric acid',
            '2-Oxobutyrate', '2-Oxobutanoic acid', '2-Ketobutanoate', '3-Methyl pyruvate',
            'a-Ketobutyrate', 'a-Ketobutyric acid', 'Α-ketobutyrate', 'Α-ketobutyric acid',
            'a-oxo-N-Butyrate', 'a-oxo-N-Butyric acid', 'alpha-oxo-N-Butyrate',
            'Α-oxo-N-butyrate', 'Α-oxo-N-butyric acid', '2-Oxobutanoate',
            '2-Ketobutyrate', '2-oxo-Butanoate', '2-oxo-Butanoic acid',
            '2-oxo-Butyrate', '2-oxo-Butyric acid', '2-oxo-N-Butyrate',
            '2-oxo-N-Butyric acid', '3-Methylpyruvate', '3-Methylpyruvic acid',
            'a-Keto-N-butyrate', 'a-Keto-N-butyric acid', 'a-Oxobutyrate',
            'a-Oxobutyric acid', 'alpha-Keto-N-butyrate', 'alpha-Keto-N-butyric acid',
            'alpha-Ketobutric acid', 'alpha-Oxobutyrate', 'alpha-Oxobutyric acid',
            'Methyl-pyruvate', 'Methyl-pyruvic acid', 'Propionyl-formate',
            'Propionyl-formic acid', 'alpha-Ketobutyric acid, sodium salt',
            '2-Ketobutyric acid'
        ])
        self.assertEqual(molecule.iupac_name, '2-oxobutanoic acid')
        self.assertEqual(molecule.traditional_iupac, '2-oxobutanoic acid')

    def test_datetime_field_is_recent(self):
        molecule = HmdbMetabolite.objects.get(accession='HMDB0000005')

        self.assertGreaterEqual(molecule.created_at, self.start_time)
        self.assertLessEqual(molecule.created_at, self.end_time)

    def test_update_or_create_behavior(self):
        initial_count = HmdbMetabolite.objects.count()

        out = StringIO()
        call_command('import_molecule_data', 'hmdb', test=True, stdout=out)

        self.assertEqual(HmdbMetabolite.objects.count(), initial_count)


class FindMatchingHgncGenesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gene1 = HgncGene.objects.create(
            hgnc_id='HGNC:1',
            symbol="G1",
            name="gene one",
            entrez_id="101",
            omim_id=[123, 456],
            uniprot_ids=['P123', 'P456'],
            alias_symbol=['G1-ALIAS']
        )
        cls.gene2 = HgncGene.objects.create(
            hgnc_id='HGNC:2',
            symbol="G2",
            name="gene two",
            entrez_id="102",
            omim_id=[123, 789],
            uniprot_ids=['item, comma'],
        )

    def search_genes(self, search_strings):
        return HgncGene.objects.find_matching_items(search_strings)

    def test_search_no_matches(self):
        results = self.search_genes(['NOTHING'])
        self.assertIn('NOTHING', results['no_matches'])

    def test_search_one_match_by_id(self):
        results = self.search_genes(['HGNC:1'])
        self.assertEqual(len(results['one_match']), 1)
        self.assertEqual(results['one_match'][0]['item'], self.gene1)

    def test_search_one_match_case_insensitive(self):
        results = self.search_genes(['hgnc:1'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)

    def test_search_one_match_by_array_field(self):
        results = self.search_genes(['P123'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)

    def test_search_one_match_by_array_field_case_insensitive(self):
        results = self.search_genes(['p123'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)

    def test_search_multiple_matches_by_omim(self):
        results = self.search_genes(['123'])
        self.assertEqual(len(results['multiple_matches']), 1)
        matched_items = results['multiple_matches'][0]['items']
        self.assertIn(self.gene1, matched_items)
        self.assertIn(self.gene2, matched_items)

    def test_search_item_with_comma(self):
        results = self.search_genes(['item, comma'])
        self.assertEqual(results['one_match'][0]['item'], self.gene2)

    def test_complex_search(self):
        results = self.search_genes(['G1', '123', 'nonexistent'])
        self.assertIn('nonexistent', results['no_matches'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        self.assertEqual(len(results['multiple_matches'][0]['items']), 2)


class FindMatchingHmdbMetabolitesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.metabolite1 = HmdbMetabolite.objects.create(
            accession="HMDB0000001",
            name="1-Methylhistidine",
            chebi_id=50212,
            synonyms=["(2S)-2-amino-3-(1-methyl-1H-imidazol-4-yl)propanoic acid", "Pi-methylhistidine"]
        )
        cls.metabolite2 = HmdbMetabolite.objects.create(
            accession="HMDB0000002",
            name="2-Methylhistidine",
            chebi_id=50212, # Shared Chebi ID
            synonyms=["(2S)-2-amino-3-(2-methyl-1H-imidazol-4-yl)propanoic acid", "Tau-methylhistidine"]
        )

    def search_metabolites(self, search_strings):
        return HmdbMetabolite.objects.find_matching_items(search_strings)

    def test_search_no_matches(self):
        results = self.search_metabolites(['NOT_FOUND'])
        self.assertIn('NOT_FOUND', results['no_matches'])

    def test_search_one_match_by_accession(self):
        results = self.search_metabolites(['HMDB0000001'])
        self.assertEqual(len(results['one_match']), 1)
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)

    def test_search_one_match_by_name_case_insensitive(self):
        results = self.search_metabolites(['1-methylhistidine'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)

    def test_search_one_match_by_synonym(self):
        results = self.search_metabolites(['Pi-methylhistidine'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)

    def test_search_multiple_matches_by_chebi_id(self):
        results = self.search_metabolites(['50212'])
        self.assertEqual(len(results['multiple_matches']), 1)
        matched_items = results['multiple_matches'][0]['items']
        self.assertIn(self.metabolite1, matched_items)
        self.assertIn(self.metabolite2, matched_items)

    def test_combined_search_scenarios(self):
        results = self.search_metabolites(['HMDB0000002', '50212', 'invalid'])
        self.assertIn('invalid', results['no_matches'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite2)
        self.assertEqual(len(results['multiple_matches'][0]['items']), 2)

class AddGenesView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.study = Study.objects.create(title="Example study", doi="https://doi.org/fdfdsa")
        disease = Disease.objects.create(name="ME/CFS")
        control = Disease.objects.create(name="Healthy")
        cls.study_cohort = StudyCohort.objects.create(study=cls.study)
        cls.study_cohort.disease_tags.add(disease)
        cls.study_cohort.control_tags.add(control)

    def test_url_valid_response(self):
        response = self.client.get(f'/manage/add_gene_findings/{self.study.id}/GA/')

        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_data(self):
        response = self.client.get(reverse('sickgenes:add_gene_findings', args=(self.study.id,"GA")))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/molecule_match.html')
        self.assertContains(response, "Search terms:")

class AddStudyView(TestCase):
    def test_url_valid_response(self):
        response = self.client.get('/manage/add_study/')

        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_data(self):
        response = self.client.get(reverse('sickgenes:add_study'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/add_study.html')
        self.assertContains(response, "Title:")

    def test_post_data_to_add_study(self):
        response = self.client.post(reverse('sickgenes:add_study'), data={'title': "Study one", 'doi': 'https://doi.org/234243'})
        studies = Study.objects.filter(title='Study one')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(studies), 1)

class StudyView(TestCase):
    @classmethod
    def setUpTestData(cls):
        study = Study.objects.create(title="Example study", doi="https://doi.org/fdfdsa")
        disease = Disease.objects.create(name="ME/CFS")
        control = Disease.objects.create(name="Healthy")
        study_cohort = StudyCohort.objects.create(study=study)
        study_cohort.disease_tags.add(disease)
        study_cohort.control_tags.add(control)
        cls.study_id = study.id

    def test_url_valid_response(self):
        response = self.client.get(f'/study/{self.study_id}/')

        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_data(self):
        response = self.client.get(reverse('sickgenes:study', args=(self.study_id,)))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/study.html')
        self.assertContains(response, "Example study")
        self.assertContains(response, "ME/CFS")
        self.assertContains(response, "Healthy")

class AddStudyCohortView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.study = Study.objects.create(title="Example study", doi="https://doi.org/fdfdsa")
        cls.disease_mecfs = Disease.objects.create(name="ME/CFS")
        cls.disease_healthy = Disease.objects.create(name="Healthy")
        cls.disease_diabetes = Disease.objects.create(name="Diabetes")

    def test_url_valid_response(self):
        response = self.client.get(f'/manage/add_study_cohort/{self.study.id}/')

        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_data(self):
        response = self.client.get(reverse('sickgenes:add_study_cohort', args=(self.study.id,)))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/add_study_cohort.html')
        self.assertContains(response, "Disease tags:")

    def test_post_data_to_add_study_cohort(self):
        post_data = {
            'disease_tags': [self.disease_mecfs.id, self.disease_diabetes.id],
            'control_tags': [self.disease_healthy.id],
        }
        response = self.client.post(reverse('sickgenes:add_study_cohort', args=(self.study.id,)), data=post_data)
        study_cohorts_for_study = StudyCohort.objects.filter(study=self.study)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(study_cohorts_for_study.count(), 1)

        new_study_cohort = study_cohorts_for_study.first()
        saved_disease_tag_ids = [tag.id for tag in new_study_cohort.disease_tags.all()]
        saved_control_tag_ids = [tag.id for tag in new_study_cohort.control_tags.all()]

        self.assertSetEqual(set(saved_disease_tag_ids), set(post_data['disease_tags']))
        self.assertSetEqual(set(saved_control_tag_ids), set(post_data['control_tags']))