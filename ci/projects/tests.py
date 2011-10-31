import anyjson as json
import os

from django.core.urlresolvers import reverse
from django.test import TestCase

from celery.decorators import task

from . import tasks
from .models import Project, Configuration, Value, Build


class ProjectTests(TestCase):
    def setUp(self):
        # Disconnect the clone task to avoid implicit cloning during the tests
        @task
        def clone_on_creation(project_id):
            pass
        self._old_clone = tasks.clone_on_creation
        tasks.clone_on_creation = clone_on_creation

    def tearDown(self):
        tasks.clone_on_creation = self._old_clone

    def _create_project(self):
        self.project = Project.objects.create(
            name='django-floppyforms',
            slug='django-floppyforms',
            repo='https://github.com/brutasse/django-floppyforms',
            repo_type='git',
            build_instructions='echo "lol"',
        )

    def _create_build(self, **kwargs):
        defaults = {
            'project': self.project,
            'matrix': json.dumps({'python': ['py25', 'py26', 'py27'],
                                  'django': ['1.2', '1.3', 'trunk']}),
            'revision': '1',
        }
        defaults.update(kwargs)
        self.build = Build.objects.create(**defaults)

    def _create_job(self, **kwargs):
        defaults = {
            'status': 'success',
            'values': json.dumps({'python': 'py27', 'django': 'trunk'}),
            'output': 'Build finished: SUCCESS',
        }
        defaults.update(kwargs)
        self.job = self.build.jobs.create(**defaults)

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

        # Save and continue editing
        data.update({'_continue': True})
        response = self.client.post(url, data)
        self.assertRedirects(response, url)

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
        self._create_build()

        job = self.build.jobs.create(
            status='running',
            values=json.dumps({'python': 'py25', 'django': '1.2'}),
        )

        url = reverse('project', args=[self.project.slug])
        response = self.client.get(url)
        build_url = reverse('project_job', args=[self.project.slug,
                                                 self.build.pk, job.pk])
        self.assertContains(response, build_url)
        self.assertContains(response, 'Build status: running')

    def test_build_detail(self):
        """Detailed page for a single build"""
        self._create_project()
        self._create_build()
        self._create_job()

        url = reverse('project_job', args=[self.project.slug, self.build.pk,
                                           self.job.pk])
        response = self.client.get(url)
        self.assertContains(response, 'success')

    def test_delete_build(self):
        """Delete a build"""
        self._create_project()
        self._create_build()
        self._create_job()

        url = reverse('delete_build', args=[self.project.slug,
                                            self.build.pk])
        response = self.client.get(url)
        self.assertContains(response, 'Delete')
        self.assertEqual(Build.objects.count(), 1)

        response = self.client.post(url, {})
        self.assertRedirects(response, reverse('project',
                                               args=[self.project.slug]))
        self.assertEqual(Build.objects.count(), 0)

        # Disallow deleting a build that's not success or failure
        self._create_build()
        self._create_job()
        self.job.status = 'running'
        self.job.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Build.objects.count(), 1)

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Build.objects.count(), 1)

    def test_project_builds(self):
        """A list of builds for a project"""
        self._create_project()
        self._create_build()
        self._create_job()
        self._create_job(status='failure')
        self._create_build()
        self._create_job()
        self._create_job()

        url = reverse('project_builds', args=[self.project.slug])
        response = self.client.get(url)
        self.assertContains(response, "Builds for " + self.project.name)

    def test_project_build(self):
        """Detailed view of a build"""
        self._create_project()
        self._create_build()
        self._create_job()
        self._create_job()

        url = reverse('project_build', args=[self.project.slug,
                                             self.build.pk])
        response = self.client.get(url)
        self.assertContains(response, 'success')

    def test_xunit_report(self):
        """XUnit XML test results"""
        self._create_project()
        self._create_build()
        self._create_job()

        # Attach an XML report
        with open(os.path.join(
            os.path.dirname(__file__),
            os.pardir, 'test_data', 'xunit.xml')) as f:
            self.job.xunit_xml_report = f.read()
        self.job.save()

        url = reverse('project_job', args=[self.project.slug, self.build.pk,
                                           self.job.pk])
        response = self.client.get(url)
        self.assertContains(response, 'Test results')
        self.assertContains(response, 'Ran 79 tests in 37.225s')
        self.assertContains(response, '1 failure')
        self.assertContains(response, '0 errors')
        self.assertContains(response, 'AssertionError: False is not True')
