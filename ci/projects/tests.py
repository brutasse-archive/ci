from django.core.urlresolvers import reverse
from django.test import TestCase

from .models import Project


class ProjectTests(TestCase):
    def test_project_list(self):
        url = reverse('projects')
        response = self.client.get(url)
        self.assertContains(response, 'any project yet')

    def test_add_project(self):
        url = reverse('add_project')
        response = self.client.get(url)
        self.assertContains(response, 'Add a new project')

        data = {
            'name': 'django-le-social',
            'repo': 'https://github.com/brutasse/django-le-social',
            'repo_type': 'git',
            'build_instructions': 'python setup.py test',
        }
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, '<h1>django-le-social</h1>')
        self.assertEqual(len(response.redirect_chain), 1)

    def test_home_no_build(self):
        """Home when no project has been built yet"""
        Project.objects.create(
            name='django-floppyforms',
            slug='django-floppyforms',
            repo='https://github.com/brutasse/django-floppyforms',
            repo_type='git',
            build_instructions='echo "lol"',
        )
        url = reverse('projects')
        response = self.client.get(url)
        self.assertContains(response, 'no build yet')
