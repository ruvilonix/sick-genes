import os
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from projectfinding.settings import required_env


class StaticFilesStorageTest(SimpleTestCase):
    def test_static_files_are_compressed_by_whitenoise(self):
        # Django 5.1 dropped the old STATICFILES_STORAGE setting, which then
        # did nothing without any warning; STORAGES is the one that counts
        self.assertEqual(
            settings.STORAGES['staticfiles']['BACKEND'],
            'whitenoise.storage.CompressedStaticFilesStorage',
        )

    def test_uploaded_file_storage_is_still_set(self):
        # STORAGES replaces Django's whole default, so it must list both
        self.assertIn('default', settings.STORAGES)


class RequiredEnvTest(SimpleTestCase):
    def test_returns_the_value(self):
        with mock.patch.dict(os.environ, {'SICKGENES_TEST_SETTING': 'abc'}):
            self.assertEqual(required_env('SICKGENES_TEST_SETTING'), 'abc')

    def test_missing_setting_names_it_in_the_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesMessage(ImproperlyConfigured, 'SICKGENES_TEST_SETTING'):
                required_env('SICKGENES_TEST_SETTING')

    def test_empty_setting_counts_as_missing(self):
        with mock.patch.dict(os.environ, {'SICKGENES_TEST_SETTING': '  '}):
            with self.assertRaises(ImproperlyConfigured):
                required_env('SICKGENES_TEST_SETTING')
