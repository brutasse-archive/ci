import anyjson as json

from django.core.urlresolvers import reverse
from django.test import TestCase

from .models import Project, Configuration, Value, MetaBuild


class ProjectTests(TestCase):
    def _create_project(self):
        self.project = Project.objects.create(
            name='django-floppyforms',
            slug='django-floppyforms',
            repo='https://github.com/brutasse/django-floppyforms',
            repo_type='git',
            build_instructions='echo "lol"',
        )

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
        self.assertContains(response,
                            '<h1>Build instructions for django-le-social</h1>')
        self.assertContains(response, 'django-le-social has been ')
        self.assertContains(response, 'You may review the build config')
        self.assertEqual(len(response.redirect_chain), 1)

    def test_home_no_build(self):
        """Home when no project has been built yet"""
        self._create_project()
        url = reverse('projects')
        response = self.client.get(url)
        self.assertContains(response, 'no build yet')

    def test_project_admin(self):
        """Build config for projects"""
        self._create_project()
        url = reverse('project_admin', args=[self.project.slug])
        response = self.client.get(url)
        self.assertContains(response, 'Sequential build?')
        self.assertNotContains(response, 'Add a new project')

        data = {
            'build_instructions': 'echo "LOL"',
            'sequential': False,
            'keep_build_data': True,
        }
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'successfully updated')
        self.assertEqual(len(response.redirect_chain), 1)

    def test_project_axis(self):
        """Managing multi-configuration builds"""
        self._create_project()
        url = reverse('project_axis', args=[self.project.slug])
        response = self.client.get(url)
        self.assertContains(response, 'Build axes')

        data = {
            'form-TOTAL_FORMS': 1,
            'form-INITIAL_FORMS': 0,
            'form-0-name': 'python',
            'form-0-values': 'py26, py27',
        }
        response = self.client.post(url, data, follow=True)
        self.assertContains(response,
                            'Build axis have been successfully updated')
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(Configuration.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 2)

        # Adding pypy and a new axis
        data.update({
            'form-TOTAL_FORMS': 2,
            'form-INITIAL_FORMS': 1,
            'form-0-values': 'py26, py27, pypy',
            'form-1-name': 'django',
            'form-1-values': '1.2, 1.3, trunk',
        })
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(Configuration.objects.count(), 2)
        self.assertEqual(Value.objects.count(), 6)

        # Deleting the python axis
        data.update({
            'form-0-delete': True,
        })
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(Configuration.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 3)

        # Removing the django 1.2 key
        data = {
            'form-TOTAL_FORMS': 2,
            'form-INITIAL_FORMS': 1,
            'form-0-name': 'django',
            'form-0-values': '1.3, trunk',
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(Configuration.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 2)

        # Submitting duplicate keys
        data['form-0-values'] = '1.3, 1.3, trunk, trunk, trunk'
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(Configuration.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 2)

    def test_build_axis(self):
        """Displaying configuration axes"""
        self._create_project()

        metabuild = MetaBuild.objects.create(
            project=self.project,
            matrix=json.dumps({'python': ['py25', 'py26', 'py27'],
                               'django': ['1.2', '1.3', 'trunk']}),
            revision='1',
        )

        build = metabuild.builds.create(
            status='running',
            values=json.dumps({'python': 'py25', 'django': '1.2'}),
        )

        url = reverse('project', args=[self.project.slug])
        response = self.client.get(url)
        build_url = reverse('build', args=[build.pk])
        self.assertContains(response, build_url)
        self.assertContains(response, 'Build status: running')
