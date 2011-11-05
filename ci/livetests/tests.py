import os
import shutil

from django.conf import settings
from django.test import TestCase

from ..projects.models import Project, Job

BUILD = """virtualenv ci --python python2
source ci/bin/activate
pip install nose coverage
nosetests -v --with-xunit --with-coverage --cover-package=project project.py
"""


class LiveTests(TestCase):
    def _clean(self):
        if os.path.exists(settings.WORKSPACE):
            shutil.rmtree(settings.WORKSPACE)

    setUp = _clean
    tearDown = _clean

    def _create_git_project(self):
        self.project = Project.objects.create(
            name='testproject-git',
            slug='testproject-git',
            repo='https://github.com/brutasse/testproject',
            build_instructions=BUILD,
        )

    def _create_hg_project(self):
        self.project = Project.objects.create(
            name='testproject-hg',
            slug='testproject-hg',
            repo='ssh://hg@bitbucket.org/bruno/testproject',
            repo_type='hg',
            build_instructions=BUILD,
        )

    def test_git_handling(self):
        """Git-related operations"""
        self._create_git_project()
        vcs = self.project.vcs()

        self.assertEqual(vcs.latest_revision(),
                         "e451f81061f3b832e0455ce257ea608022ee18b0")

        self.assertEqual(vcs.branches(), [
            'experimental', 'master',
        ])

        self.assertEqual(vcs.latest_branch_revision('experimental'),
                         '1bdf1363d154e476628d584654c602ccaad23332')

    def test_git_build(self):
        """Building a Git project"""
        self._create_git_project()
        self.project.build()

        self.assertTrue('Ran 3 tests in ' in Job.objects.get().output)
        self.assertEqual(Job.objects.get().status, 'success')

    def test_hg_handling(self):
        """Hg-related operations"""
        self._create_hg_project()
        vcs = self.project.vcs()

        self.assertEqual(vcs.latest_revision(), 7)

        self.assertEqual(vcs.branches(), [
            'default',
        ])

        self.assertEqual(vcs.latest_branch_revision('default'), 7)

    def test_hg_build(self):
        """Building a Mercurial project"""
        self._create_hg_project()
        self.project.build()

        self.assertTrue('Ran 3 tests in ' in Job.objects.get().output)
        self.assertEqual(Job.objects.get().status, 'success')
