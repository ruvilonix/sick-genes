import gzip
import io
import json
import os
import tempfile
from django.test import TestCase
from django.core.management.base import CommandError
from sickgenes.models import (
    AliasSymbol, GeneFinding, HgncGene, OmimId, PrevSymbol, StringInteraction, StringProtein,
    Study, StudyCohort,
)
from django.core.management import call_command
from unittest.mock import patch, ANY

from sickgenes.importers.update_hgnc import HgncImportResult, update_hgnc_data
from sickgenes.importers.update_string import (
    process_string_aliases,
    process_string_interactions,
    update_string_data
)

COMMAND_PATH = 'sickgenes.management.commands.import_molecule_data.update_string_data'

class ImportDataCommandTests(TestCase):
    """
    Tests the import_molecule_data management command.
    """

    @patch(COMMAND_PATH)
    def test_command_calls_string_importer_with_test_flag(self, mock_update_string_data):
        """
        Verify the command calls the correct function with use_test_data=True.
        """
        # Act
        call_command('import_molecule_data', 'string', '--test')

        # Assert
        mock_update_string_data.assert_called_once_with(ANY, True)

    @patch(COMMAND_PATH)
    def test_command_calls_string_importer_without_test_flag(self, mock_update_string_data):
        """
        Verify the command calls the correct function with use_test_data=False.
        """
        # Act
        call_command('import_molecule_data', 'string')

        # Assert
        mock_update_string_data.assert_called_once_with(ANY, False)

    def test_command_fails_with_invalid_database(self):
        """
        Verify the command's argument parser rejects an invalid database choice.
        """
        stderr = io.StringIO()
        with self.assertRaises(CommandError) as e:
            call_command('import_molecule_data', 'invalid_database_name', stderr=stderr)
        
        self.assertIn("invalid choice: 'invalid_database_name'", str(e.exception))


MOCK_ALIAS_CONTENT = """
# string_protein_id	alias	source
9606.ENSP00000269305	HGNC:5	Ensembl_HGNC_hgnc_id
9606.ENSP00000269305	A1BG	Gene_ORF_name
9606.ENSP00000371583	HGNC:13	Ensembl_HGNC_hgnc_id
9606.ENSP_NONEXISTENT	HGNC:99999	Ensembl_HGNC_hgnc_id
ENSP00000216171	HGNC:14	Ensembl_HGNC_hgnc_id
""".strip()

MOCK_INTERACTION_CONTENT = """
protein1 protein2 combined_score
9606.ENSP00000269305 9606.ENSP00000371583 999
9606.ENSP00000269305 9606.ENSP_MISSING 800
9606.ENSP00000216171 9606.ENSP00000269305 950
9606.ENSP_MISSING1 9606.ENSP_MISSING2 700
9606.BAD_LINE_FORMAT
""".strip()


class StringDataImportTests(TestCase):
    """
    Test suite for STRING data import functions.
    """

    def setUp(self):
        """Set up initial data and mocks for all tests."""
        self.hgnc_5 = HgncGene.objects.create(hgnc_id=5, symbol="A1BG")
        self.hgnc_13 = HgncGene.objects.create(hgnc_id=13, symbol="A2M")
        self.hgnc_14 = HgncGene.objects.create(hgnc_id=14, symbol="NAT1")
        
        self.stdout = io.StringIO()

    def _create_mock_gzip_file(self, content):
        """Creates an in-memory gzipped file for mocking."""
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='w') as f:
            f.write(content.encode('utf-8'))
        buf.seek(0)
        return io.TextIOWrapper(gzip.GzipFile(fileobj=buf, mode='r'))

    @patch('sickgenes.importers.update_string.gzip.open')
    @patch('sickgenes.importers.update_string.os.path.exists', return_value=True)
    def test_process_string_aliases_success(self, mock_exists, mock_gzip_open):
        """
        Verify that StringProtein objects are created correctly from a valid alias file.
        """
        mock_file = self._create_mock_gzip_file(MOCK_ALIAS_CONTENT)
        mock_gzip_open.return_value.__enter__.return_value = mock_file

        # Pre-populate to test if data is cleared
        StringProtein.objects.create(protein_id="OLD_PROTEIN", hgnc_id=5, hgnc_gene=self.hgnc_5)
        self.assertEqual(StringProtein.objects.count(), 1)

        result = process_string_aliases('dummy_path.gz', self.stdout)

        self.assertTrue(result)
        self.assertEqual(StringProtein.objects.count(), 3)
        
        # Check that only aliases with 'Ensembl_HGNC_hgnc_id' source were added
        self.assertTrue(StringProtein.objects.filter(protein_id='ENSP00000269305').exists())
        self.assertTrue(StringProtein.objects.filter(protein_id='ENSP00000371583').exists())
        self.assertTrue(StringProtein.objects.filter(protein_id='ENSP00000216171').exists())
        
        # Check link to HgncGene
        protein = StringProtein.objects.get(protein_id='ENSP00000269305')
        self.assertEqual(protein.hgnc_gene, self.hgnc_5)

        # Check output log
        output = self.stdout.getvalue()
        self.assertIn("String alias import completed", output)
        self.assertIn("Records created: 3", output)
        self.assertIn("Warning: HgncGene with ID 99999 not found", output)
        self.assertIn("Errors: 1", output)

    @patch('sickgenes.importers.update_string.os.path.exists', return_value=False)
    def test_process_string_aliases_file_not_found(self, mock_exists):
        """
        Verify that a CommandError is raised if the alias file doesn't exist.
        """
        with self.assertRaises(CommandError) as cm:
            process_string_aliases('non_existent_path.gz', self.stdout)
        self.assertIn("STRING alias file not found", str(cm.exception))

    @patch('sickgenes.importers.update_string.gzip.open')
    @patch('sickgenes.importers.update_string.os.path.exists', return_value=True)
    def test_process_string_interactions_success(self, mock_exists, mock_gzip_open):
        """
        Verify that StringInteraction objects are created correctly from a mock file,
        starting with an empty table.
        """

        mock_gzip_open.side_effect = [
            self._create_mock_gzip_file(MOCK_INTERACTION_CONTENT), # For the first read
            self._create_mock_gzip_file(MOCK_INTERACTION_CONTENT)  # For the second read
        ]

        # Setup: Create the necessary StringProtein objects.
        p1 = StringProtein.objects.create(protein_id="ENSP00000269305", hgnc_id=5, hgnc_gene=self.hgnc_5)
        p2 = StringProtein.objects.create(protein_id="ENSP00000371583", hgnc_id=13, hgnc_gene=self.hgnc_13)
        p3 = StringProtein.objects.create(protein_id="ENSP00000216171", hgnc_id=14, hgnc_gene=self.hgnc_14)
        
        # Ensure the table is empty before running the function
        StringInteraction.objects.all().delete()
        self.assertEqual(StringInteraction.objects.count(), 0)

        # ACT: Run the function
        result = process_string_interactions('dummy_path.gz', self.stdout)

        # ASSERT: Check the final state
        self.assertTrue(result)
        self.assertEqual(StringInteraction.objects.count(), 2)

        # Verify the created interactions
        interaction1 = StringInteraction.objects.get(combined_score=999)
        self.assertEqual(interaction1.protein1, p1)
        self.assertEqual(interaction1.protein2, p2)
        
        interaction2 = StringInteraction.objects.get(combined_score=950)
        # Test the protein ordering logic (p1.id < p3.id)
        self.assertEqual(interaction2.protein1, p1)
        self.assertEqual(interaction2.protein2, p3)
        
        # Check the console output
        output = self.stdout.getvalue()
        self.assertIn("interactions created: 2", output)
        self.assertIn("missing protein IDs encountered: 3", output)

    @patch('sickgenes.importers.update_string.os.path.exists', return_value=False)
    def test_process_string_interactions_file_not_found(self, mock_exists):
        """
        Verify that a CommandError is raised if the interaction file doesn't exist.
        """
        with self.assertRaises(CommandError) as cm:
            process_string_interactions('non_existent_path.gz', self.stdout)
        self.assertIn("STRING interaction file not found", str(cm.exception))

    @patch('sickgenes.importers.update_string.process_string_interactions')
    @patch('sickgenes.importers.update_string.process_string_aliases')
    def test_update_string_data_calls_processors(self, mock_process_aliases, mock_process_interactions):
        """
        Verify that the main update function calls the individual processors.
        """
        mock_process_aliases.return_value = True
        mock_process_interactions.return_value = True

        result = update_string_data(self.stdout, use_test_data=True)

        self.assertTrue(result)
        mock_process_aliases.assert_called_once()
        mock_process_interactions.assert_called_once()
        
        # Check that it uses the sample paths when use_test_data is True
        args, _ = mock_process_aliases.call_args
        self.assertIn('sample_data', args[0])
        
        args, _ = mock_process_interactions.call_args
        self.assertIn('sample_data', args[0])


class UpdateHgncDataTests(TestCase):
    """update_hgnc_data with small JSON files shaped like HGNC's downloads."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def write_file(self, genes):
        """Saves a list of gene records as an HGNC-style JSON file and returns its path."""
        path = os.path.join(self.folder, f'{len(os.listdir(self.folder))}.json')
        with open(path, 'w') as file:
            json.dump({'response': {'docs': genes}}, file)
        return path

    def import_files(self, *gene_lists):
        """Imports each list of gene records as its own file, like the two HGNC downloads."""
        return update_hgnc_data([self.write_file(genes) for genes in gene_lists])

    def values(self, model, gene):
        return sorted(model.objects.filter(gene=gene).values_list('value', flat=True))

    def test_count_includes_every_file(self):
        result = self.import_files(
            [{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}],
            [{'hgnc_id': 'HGNC:13', 'symbol': 'A2M'}, {'hgnc_id': 'HGNC:14', 'symbol': 'NAT1'}],
        )
        self.assertEqual(result.processed_count, 3)
        self.assertEqual(HgncGene.objects.count(), 3)

    def test_records_without_id_or_symbol_are_skipped(self):
        result = self.import_files([
            {'symbol': 'NOID'},
            {'hgnc_id': '', 'symbol': 'BLANKID'},
            {'hgnc_id': 'HGNC:7'},
            {'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'},
        ])
        self.assertEqual(result.processed_count, 1)
        self.assertEqual(list(HgncGene.objects.values_list('hgnc_id', 'symbol')), [(5, 'A1BG')])

    # Re-importing over existing genes, as the production import does.
    # HGNC leaves a key out of a record when it has no value, so a list or
    # field missing from the new record means it was removed.

    def test_update_changes_fields_and_keeps_the_gene_and_its_findings(self):
        self.import_files([{
            'hgnc_id': 'HGNC:5', 'symbol': 'OLD1', 'name': 'old name',
            'entrez_id': '1', 'ensembl_gene_id': 'ENSG01', 'vega_id': 'OTTHUMG01', 'ucsc_id': 'uc001',
        }])
        gene = HgncGene.objects.get(hgnc_id=5)
        cohort = StudyCohort.objects.create(study=Study.objects.create(title='Study'))
        finding = GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=gene)

        self.import_files([{
            'hgnc_id': 'HGNC:5', 'symbol': 'NEW1', 'name': 'new name', 'entrez_id': '2',
        }])

        updated = HgncGene.objects.get()
        self.assertEqual(updated.pk, gene.pk)
        self.assertEqual(
            (updated.symbol, updated.name, updated.entrez_id),
            ('NEW1', 'new name', 2),
        )
        self.assertEqual((updated.ensembl_gene_id, updated.vega_id, updated.ucsc_id), (None, None, None))
        finding.refresh_from_db()
        self.assertEqual(finding.hgnc_gene, updated)

    def test_update_replaces_related_lists(self):
        self.import_files([{
            'hgnc_id': 'HGNC:5', 'symbol': 'A1BG',
            'alias_symbol': ['A', 'B'], 'prev_symbol': ['X'], 'omim_id': ['100'],
        }])
        self.import_files([{
            'hgnc_id': 'HGNC:5', 'symbol': 'A1BG',
            'alias_symbol': ['B', 'C'], 'prev_symbol': ['X'], 'omim_id': ['200'],
        }])

        gene = HgncGene.objects.get()
        self.assertEqual(self.values(AliasSymbol, gene), ['B', 'C'])
        self.assertEqual(self.values(PrevSymbol, gene), ['X'])
        self.assertEqual(self.values(OmimId, gene), [200])

    def test_update_clears_lists_left_out_of_the_new_record(self):
        self.import_files([{
            'hgnc_id': 'HGNC:5', 'symbol': 'A1BG', 'alias_symbol': ['A'], 'omim_id': ['100'],
        }])
        self.import_files([{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}])

        gene = HgncGene.objects.get()
        self.assertEqual(self.values(AliasSymbol, gene), [])
        self.assertEqual(self.values(OmimId, gene), [])

    def test_update_does_not_touch_other_genes_lists(self):
        self.import_files([
            {'hgnc_id': 'HGNC:5', 'symbol': 'A1BG', 'alias_symbol': ['SHARED', 'A']},
            {'hgnc_id': 'HGNC:13', 'symbol': 'A2M', 'alias_symbol': ['SHARED']},
        ])
        self.import_files([{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG', 'alias_symbol': ['A']}])

        self.assertEqual(self.values(AliasSymbol, HgncGene.objects.get(hgnc_id=13)), ['SHARED'])

    def test_gene_left_out_of_the_new_data_is_kept_with_its_findings(self):
        # HGNC drops withdrawn genes from its files; findings must survive that
        self.import_files([
            {'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'},
            {'hgnc_id': 'HGNC:13', 'symbol': 'A2M'},
        ])
        withdrawn = HgncGene.objects.get(hgnc_id=13)
        cohort = StudyCohort.objects.create(study=Study.objects.create(title='Study'))
        GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=withdrawn)

        self.import_files([{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}])

        self.assertTrue(GeneFinding.objects.filter(hgnc_gene__hgnc_id=13, hgnc_gene__symbol='A2M').exists())

    def test_failure_in_a_later_file_undoes_the_whole_import(self):
        self.import_files([{'hgnc_id': 'HGNC:5', 'symbol': 'OLD1', 'alias_symbol': ['A']}])

        first = self.write_file([{'hgnc_id': 'HGNC:5', 'symbol': 'NEW1', 'alias_symbol': ['B']}])
        missing = os.path.join(self.folder, 'missing.json')
        with self.assertRaises(CommandError):
            update_hgnc_data([first, missing])

        gene = HgncGene.objects.get()
        self.assertEqual(gene.symbol, 'OLD1')
        self.assertEqual(self.values(AliasSymbol, gene), ['A'])

    def test_repeated_value_in_a_list_is_stored_once(self):
        self.import_files([{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG', 'alias_symbol': ['A', 'A']}])
        self.assertEqual(self.values(AliasSymbol, HgncGene.objects.get()), ['A'])

    # The report of changes to genes that have findings

    def add_findings(self, hgnc_id, number=1):
        # A gene can be listed once per study, so each finding gets its own study
        for _ in range(number):
            cohort = StudyCohort.objects.create(study=Study.objects.create(title='Study'))
            GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=HgncGene.objects.get(hgnc_id=hgnc_id))

    def test_report_lists_renamed_genes_that_have_findings(self):
        self.import_files([
            {'hgnc_id': 'HGNC:5', 'symbol': 'OLD1'},
            {'hgnc_id': 'HGNC:13', 'symbol': 'OLD2'},
        ])
        self.add_findings(5, number=2)

        result = self.import_files([
            {'hgnc_id': 'HGNC:5', 'symbol': 'NEW1'},
            {'hgnc_id': 'HGNC:13', 'symbol': 'NEW2'},
        ])

        self.assertEqual(result.renamed, [('OLD1', 'NEW1', 2)])
        self.assertEqual(result.missing, [])

    def test_report_lists_genes_with_findings_missing_from_the_files(self):
        self.import_files([
            {'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'},
            {'hgnc_id': 'HGNC:13', 'symbol': 'A2M'},
            {'hgnc_id': 'HGNC:14', 'symbol': 'NAT1'},
        ])
        self.add_findings(5)
        self.add_findings(13)

        result = self.import_files([{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}])

        self.assertEqual(result.missing, [('A2M', 13, 1)])
        self.assertEqual(result.renamed, [])

    def test_report_is_empty_when_nothing_changed(self):
        self.import_files([{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}])
        self.add_findings(5)

        result = self.import_files([{'hgnc_id': 'HGNC:5', 'symbol': 'A1BG'}])

        self.assertEqual((result.renamed, result.missing), ([], []))


class HgncImportResultTests(TestCase):
    def test_report_lines_list_each_change(self):
        result = HgncImportResult(
            processed_count=2,
            renamed=[('OLD1', 'NEW1', 2)],
            missing=[('A2M', 13, 1)],
        )
        self.assertEqual(result.report_lines(), [
            'Genes with findings that HGNC renamed:',
            '  OLD1 -> NEW1 (2 findings)',
            "Genes with findings that are no longer in HGNC's files (withdrawn or merged; "
            'look them up on genenames.org):',
            '  A2M, HGNC:13 (1 finding)',
        ])

    def test_report_lines_when_nothing_changed(self):
        self.assertEqual(
            HgncImportResult(processed_count=2).report_lines(),
            ['No genes with findings were renamed or removed.'],
        )
