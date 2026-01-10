from django.test import TestCase
from sickgenes.models import Study

class StudyTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.study1 = Study.objects.create(
            authors = 'Lewis, Brooke; Allen, Joe; Blaine, Amy'
        )
        cls.study2 = Study.objects.create(
            authors = 'Allen, Joe'
        )
        cls.study3 = Study.objects.create(
            authors = ''
        )

    def test_shortened_author_property_correct(self):
        short_authors1 = self.study1.short_authors
        short_authors2 = self.study2.short_authors
        short_authors3 = self.study3.short_authors

        self.assertEqual(short_authors1, 'Lewis et al.')
        self.assertEqual(short_authors2, 'Allen')
        self.assertEqual(short_authors3, '')