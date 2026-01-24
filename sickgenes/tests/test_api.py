from django.test import TestCase
from django.urls import reverse
from sickgenes.models import Study, StudyCohort, Disease, GeneFinding, HgncGene

class DatabaseDumpJsonTestV1(TestCase):
    """
    Tests for the database_dump_json view.
    """
    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.gene1 = HgncGene.objects.create(hgnc_id=1, symbol="GENE1")
        cls.gene2 = HgncGene.objects.create(hgnc_id=2, symbol="GENE2")
        cls.disease1 = Disease.objects.create(name="Disease A")
        cls.disease2 = Disease.objects.create(name="Disease B")
        cls.url = reverse('sickgenes:database_dump_json_v1')

    def test_empty_database(self):
        """
        Tests that the view returns an empty list when no studies are in the DB.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"studies": []})

    def test_full_study_and_cohort(self):
        """
        Tests a study with all fields populated and a fully populated cohort.
        """
        # 1. Setup
        study = Study.objects.create(
            title="Full Study Title",
            doi="10.1000/xyz123",
            authors="Doe, J.",
            journal_titles="Journal of Science",
            note="A study note.",
            s4me_url="http://example.com/study",
            publication_year="2025",
            publication_month="7",
            publication_day="25",
        )
        cohort = StudyCohort.objects.create(study=study, note="Cohort note.")
        cohort.disease_tags.add(self.disease1, self.disease2)
        GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=self.gene1)
        GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=self.gene2)

        # 2. Action
        response = self.client.get(self.url)
        data = response.json()

        # 3. Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["studies"]), 1)

        expected_study = {
            "title": "Full Study Title",
            "doi": "10.1000/xyz123",
            "authors": "Doe, J.",
            "journal_titles": "Journal of Science",
            "note": "A study note.",
            "s4me_url": "http://example.com/study",
            "publication_date": {
                "year": 2025,
                "month": 7,
                "day": 25,
            },
            "study_cohorts": [
                {
                    "note": "Cohort note.",
                    "phenotypes": ["Disease A", "Disease B"],
                    "gene_findings": [
                        {"hgnc_id": "HGNC:1", "symbol": "GENE1"},
                        {"hgnc_id": "HGNC:2", "symbol": "GENE2"},
                    ]
                }
            ]
        }
        
        # Sort lists to ensure deterministic comparison
        actual_study = data["studies"][0]
        actual_study["study_cohorts"][0]["phenotypes"].sort()
        actual_study["study_cohorts"][0]["gene_findings"].sort(key=lambda x: x['hgnc_id'])

        self.assertDictEqual(actual_study, expected_study)

    def test_omits_none_and_empty_fields(self):
        """
        Tests that fields with None or empty strings are omitted from the output.
        """
        Study.objects.create(
            title="Minimal Study",
            doi=None,              # Should be omitted
            authors="",            # Should be omitted
            journal_titles=None,   # Should be omitted
            note="",               # Should be omitted
            publication_year="2025",
            publication_month="1",
        )
        
        response = self.client.get(self.url)
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["studies"]), 1)

        expected_study = {
            "title": "Minimal Study",
            "publication_date": {
                "year": 2025,
                "month": 1,
            },
        }
        self.assertDictEqual(data["studies"][0], expected_study)

    def test_omits_na_publication_date(self):
        """
        Tests that a study with publication_date="N/A" omits that specific field.
        """
        Study.objects.create(title="NA Date Study")
        
        response = self.client.get(self.url)
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(data["studies"][0], {"title": "NA Date Study"})
        self.assertNotIn("publication_year", data["studies"][0])

    def test_omits_empty_cohort_from_list(self):
        """
        Tests that a cohort with no data is not included in the 'study_cohorts' list.
        """
        study = Study.objects.create(title="Study with mixed cohorts")
        # Cohort 1: has data and should appear
        StudyCohort.objects.create(study=study, note="Cohort 1 has a note")
        # Cohort 2: has no data and should be omitted
        StudyCohort.objects.create(study=study, note=None)

        response = self.client.get(self.url)
        data = response.json()
        study_data = data["studies"][0]
        
        self.assertIn("study_cohorts", study_data)
        self.assertEqual(len(study_data["study_cohorts"]), 1)
        self.assertEqual(study_data["study_cohorts"][0]["note"], "Cohort 1 has a note")

    def test_omits_empty_cohorts_list_key(self):
        """
        Tests that the 'study_cohorts' key is omitted if all of a study's
        cohorts are empty and thus filtered out.
        """
        study = Study.objects.create(title="Study with only empty cohorts")
        # Create a cohort that has no serializable data
        StudyCohort.objects.create(study=study, note=None)

        response = self.client.get(self.url)
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('study_cohorts', data['studies'][0])
        self.assertDictEqual(data['studies'][0], {'title': 'Study with only empty cohorts'})

    def test_multiple_studies(self):
        """
        Tests the output when multiple studies exist in the database.
        """
        Study.objects.create(title="First Study")
        Study.objects.create(title="Second Study", doi="10.1000/abc")

        response = self.client.get(self.url)
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["studies"]), 2)
        # Check for titles to confirm both studies are present (order isn't guaranteed)
        titles = {s["title"] for s in data["studies"]}
        self.assertEqual(titles, {"First Study", "Second Study"})

    def test_omit_not_finished_study(self):
        study = Study.objects.create(
            title="Full Study Title",
            doi="10.1000/xyz123",
            authors="Doe, J.",
            journal_titles="Journal of Science",
            note="A study note.",
            s4me_url="http://example.com/study",
            publication_year="2025",
            publication_month="7",
            publication_day="25",
            not_finished=True,
        )
        cohort = StudyCohort.objects.create(study=study, note="Cohort note.")
        cohort.disease_tags.add(self.disease1, self.disease2)
        GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=self.gene1)
        GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=self.gene2)

        # 2. Action
        response = self.client.get(self.url)
        data = response.json()

        # 3. Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["studies"]), 0)

class DatabaseDumpJsonTestV2(TestCase):
    """
    Tests for the database_dump_json view.
    """
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.gene1 = HgncGene.objects.create(hgnc_id=1, symbol="GENE1")
        cls.gene2 = HgncGene.objects.create(hgnc_id=2, symbol="GENE2")
        cls.disease1 = Disease.objects.create(name="Disease A", code="A")
        cls.disease2 = Disease.objects.create(name="Disease B")
        cls.url = reverse('sickgenes:database_dump_json_v2')

    def test_empty_database(self):
        """
        Tests that the view returns an empty list when no studies are in the DB.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"studies": []})

    def test_full_study_and_cohort(self):
        """
        Tests a study with all fields populated and a fully populated cohort.
        """
        # 1. Setup
        study = Study.objects.create(
            title="Full Study Title",
            doi="10.1000/xyz123",
            authors="Doe, J.",
            journal_titles="Journal of Science",
            note="A study note.",
            s4me_url="http://example.com/study",
            publication_year="2025",
            publication_month="7",
            publication_day="25",
        )
        cohort = StudyCohort.objects.create(study=study, note="Cohort note.")
        cohort.disease_tags.add(self.disease1, self.disease2)
        GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=self.gene1)
        GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=self.gene2)

        # 2. Action
        response = self.client.get(self.url)
        data = response.json()

        # 3. Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["studies"]), 1)

        expected_study = {
            "title": "Full Study Title",
            "doi": "10.1000/xyz123",
            "authors": "Doe, J.",
            "journal_titles": "Journal of Science",
            "note": "A study note.",
            "s4me_url": "http://example.com/study",
            "publication_date": {
                "year": 2025,
                "month": 7,
                "day": 25,
            },
            "study_cohorts": [
                {
                    "note": "Cohort note.",
                    "phenotypes": [
                        {'code': None, 'description': 'Disease B'},
                        {'code': 'A', 'description': 'Disease A'},
                    ],
                    "gene_findings": [
                        {
                            'ensembl_gene_id': None,
                            'entrez_id': None,
                            'hgnc_id': 1,
                            'hgnc_name': None,
                            'hgnc_symbol': 'GENE1'
                        },
                        {
                            'ensembl_gene_id': None,
                            'entrez_id': None,
                            'hgnc_id': 2,
                            'hgnc_name': None,
                            'hgnc_symbol': 'GENE2'
                        }
                    ]
                }
            ]
        }
        
        # Sort lists to ensure deterministic comparison
        actual_study = data["studies"][0]
        actual_study["study_cohorts"][0]["phenotypes"].sort(key=lambda x: x['code'] or '')
        actual_study["study_cohorts"][0]["gene_findings"].sort(key=lambda x: x['hgnc_id'])

        sickgenes_url = actual_study.pop('sickgenes_url')
        self.assertRegex(sickgenes_url, r'http://testserver/study/full-study-title-2025\.\d+/$')

        self.assertDictEqual(actual_study, expected_study)

    def test_omits_none_and_empty_fields(self):
        """
        Tests that fields with None or empty strings are omitted from the output.
        """
        Study.objects.create(
            title="Minimal Study",
            doi=None,              # Should be omitted
            authors="",            # Should be omitted
            journal_titles=None,   # Should be omitted
            note="",               # Should be omitted
            publication_year="2025",
            publication_month="1",
        )
        
        response = self.client.get(self.url)
        data = response.json()
        actual_study = data["studies"][0]

        actual_study.pop('sickgenes_url')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["studies"]), 1)

        expected_study = {
            "title": "Minimal Study",
            "publication_date": {
                "year": 2025,
                "month": 1,
            },
        }
        self.assertDictEqual(actual_study, expected_study)

    def test_omits_na_publication_date(self):
        """
        Tests that a study with publication_date="N/A" omits that specific field.
        """
        Study.objects.create(title="NA Date Study")
        
        response = self.client.get(self.url)
        data = response.json()
        actual_study = data["studies"][0]

        sickgenes_url = actual_study.pop('sickgenes_url')
        self.assertRegex(sickgenes_url, r'http://testserver/study/na-date-study-none\.\d+/$')
        
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(actual_study, {"title": "NA Date Study"})
        self.assertNotIn("publication_year", data["studies"][0])

    def test_omits_empty_cohort_from_list(self):
        """
        Tests that a cohort with no data is not included in the 'study_cohorts' list.
        """
        study = Study.objects.create(title="Study with mixed cohorts")
        # Cohort 1: has data and should appear
        StudyCohort.objects.create(study=study, note="Cohort 1 has a note")
        # Cohort 2: has no data and should be omitted
        StudyCohort.objects.create(study=study, note=None)

        response = self.client.get(self.url)
        data = response.json()
        study_data = data["studies"][0]
        
        self.assertIn("study_cohorts", study_data)
        self.assertEqual(len(study_data["study_cohorts"]), 1)
        self.assertEqual(study_data["study_cohorts"][0]["note"], "Cohort 1 has a note")

    def test_omits_empty_cohorts_list_key(self):
        """
        Tests that the 'study_cohorts' key is omitted if all of a study's
        cohorts are empty and thus filtered out.
        """
        study = Study.objects.create(title="Study with only empty cohorts")
        # Create a cohort that has no serializable data
        StudyCohort.objects.create(study=study, note=None)

        response = self.client.get(self.url)
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('study_cohorts', data['studies'][0])

    def test_multiple_studies(self):
        """
        Tests the output when multiple studies exist in the database.
        """
        Study.objects.create(title="First Study")
        Study.objects.create(title="Second Study", doi="10.1000/abc")

        response = self.client.get(self.url)
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["studies"]), 2)
        # Check for titles to confirm both studies are present (order isn't guaranteed)
        titles = {s["title"] for s in data["studies"]}
        self.assertEqual(titles, {"First Study", "Second Study"})

    def test_omit_not_finished_study(self):
        study = Study.objects.create(
            title="Full Study Title",
            doi="10.1000/xyz123",
            authors="Doe, J.",
            journal_titles="Journal of Science",
            note="A study note.",
            s4me_url="http://example.com/study",
            publication_year="2025",
            publication_month="7",
            publication_day="25",
            not_finished=True,
        )
        cohort = StudyCohort.objects.create(study=study, note="Cohort note.")
        cohort.disease_tags.add(self.disease1, self.disease2)
        GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=self.gene1)
        GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=self.gene2)

        # 2. Action
        response = self.client.get(self.url)
        data = response.json()

        # 3. Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["studies"]), 0)