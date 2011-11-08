import anyjson as json
import os
import shutil
import tarfile

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase

from celery.decorators import task

from ..shell import Command
from . import tasks
from .models import Project, Configuration, Value, Build, Job


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
            'repo': 'git://github.com/brutasse/django-le-social.git',
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
            'build_branches': 'default',
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

    def test_duplicate_slug(self):
        url = reverse('add_project')
        data = {
            'name': 'django-floppyforms',
            'repo': 'git://github.com/brutasse/django-floppyforms.git',
            'repo_type': 'git',
            'build_instructions': 'echo "lol"',
        }

        # First submission: project creation
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # 2nd submission: conflict
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response, 'form', 'name', ['This name conflicts with an existing '
                                       '"django-floppyforms" project.'])

    def test_validate_git_url(self):
        url = reverse('add_project')
        data = {
            'name': 'django-floppyforms',
            'repo': 'garbage garbage',
            'repo_type': 'git',
            'build_instructions': 'echo "lol"',
        }
        response = self.client.post(url, data)
        self.assertFormError(response, 'form', None,
                             "Invalid Git URL: '%s'" % data['repo'])

        data['repo'] = 'git://github.com/brutasse/django-floppyforms.git'
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

    def test_validate_hg_url(self):
        url = reverse('add_project')
        data = {
            'name': 'django-floppyforms',
            'repo': 'garbage garbage',
            'repo_type': 'hg',
            'build_instructions': 'echo "lol"',
        }
        response = self.client.post(url, data)
        self.assertFormError(response, 'form', None,
                             "Invalid Hg URL: '%s'" % data['repo'])

        data['repo'] = 'ssh://hg@bitbucket.org/bruno/testproject'
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)


class GitBuildTest(TestCase):
    """
    Tests for actual build execution, with a git repository.
    """
    git_name = 'gitrepo'
    hg_name = 'hgrepo'
    repos = [git_name, hg_name]
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            os.pardir, 'test_data'))

    def setUp(self):
        self._clean_data()
        # Extract local git repo archive
        for vcsrepo in self.repos:
            repo = tarfile.open(os.path.join(self.data_dir,
                                             '%s.tar.bz2' % vcsrepo), 'r:bz2')
            repo.extractall(path=self.data_dir)

    def tearDown(self):
        self._clean_data()

    def _clean_data(self):
        to_remove = [os.path.join(settings.WORKSPACE, 'repos')] + [
            os.path.join(self.data_dir, repo) for repo in self.repos
        ]
        for directory in to_remove:
            if os.path.exists(directory):
                shutil.rmtree(directory)

    def _create_project(self):
        self.project = Project.objects.create(
            name=self.git_name,
            slug=self.git_name,
            repo=os.path.abspath(os.path.join(self.data_dir, self.git_name)),
            build_instructions='echo 1',
        )

    def test_clone_project(self):
        """Cloning a project after its creation"""
        checkout_path = os.path.join(settings.WORKSPACE, 'repos',
                                     self.git_name)
        self.assertFalse(os.path.exists(checkout_path))
        self._create_project()
        self.assertTrue(os.path.exists(checkout_path))

    def test_build_project(self):
        """Building a project"""
        self._create_project()
        self.assertEqual(Build.objects.count(), 0)

        # Trigger a build
        self.assertTrue(self.project.build())
        self.assertEqual(Build.objects.count(), 1)
        self.assertEqual(Job.objects.count(), 1)

        # Already built -- nothing happens
        self.assertFalse(self.project.build())
        self.assertEqual(Build.objects.count(), 1)

        # Re-building the last build
        self.project.builds.get().queue()

    def test_revision(self):
        """Fetching the latest revision from the VCS"""
        self._create_project()
        self.assertEqual(self.project.latest_revision,
                         'ee9001ef213388da653486a8f59a07f4aa4cfca6')

    def test_build(self):
        self._create_project()
        self.project.build()
        self.assertEqual(self.project.build_status, 'success')

        Job.objects.get().checkout_source()
        self.assertEqual(Job.objects.get().vcs().latest_revision(),
                         'ee9001ef213388da653486a8f59a07f4aa4cfca6')

    def test_new_git_branch(self):
        """New remote branch - git"""
        self._create_project()
        self.project.build_branches = Project.ALL_BRANCHES
        self.project.save()

        self.project.build()
        self.assertEqual(self.project.build_status, 'success')
        self.assertEqual(Build.objects.count(), 1)

        Command(
            ('git checkout -b foo && '
             'echo "yay" >> README && '
             'git commit -am "Added stuff to branch foo"'),
            cwd=self.project.repo,
        )
        self.project.update_source()
        self.assertEqual(self.project.vcs().branches(), ['foo', 'master'])
        self.assertNotEqual(
            self.project.vcs().latest_branch_revision('master'),
            self.project.vcs().latest_branch_revision('foo'),
        )
        self.project.build()
        self.assertEqual(Build.objects.count(), 2)

    def test_new_hg_branch(self):
        project = Project.objects.create(
            name='hgrepo',
            slug='hgrepo',
            repo=os.path.abspath(os.path.join(self.data_dir, self.hg_name)),
            repo_type=Project.HG,
            build_instructions='echo 1',
            build_branches=Project.ALL_BRANCHES,
        )

        project.build()
        self.assertEqual(project.build_status, 'success')
        self.assertEqual(Build.objects.count(), 1)

        Command(
            ('hg branch foo && '
             'hg ci -m "Creating branch foo"'),
            cwd=project.repo
        )

        self.assertEqual(project.vcs().branches(), ['default'])
        project.update_source()
        self.assertEqual(project.vcs().branches(), ['default', 'foo'])

        self.assertNotEqual(
            project.vcs().latest_branch_revision('default'),
            project.vcs().latest_branch_revision('foo'),
        )
        project.build()
        self.assertEqual(Build.objects.count(), 2)

    def test_vcs_handling(self):
        self._create_project()
        # Cleanup the existing clone
        shutil.rmtree(os.path.join(settings.WORKSPACE, 'repos'))

        # Git support
        vcs = self.project.vcs()
        # First run: clone
        vcs.update_source()
        self.assertEqual(vcs.latest_revision(),
                         'ee9001ef213388da653486a8f59a07f4aa4cfca6')

        # Second run: fetch
        vcs.update_source()
        self.assertEqual(vcs.latest_revision(),
                         'ee9001ef213388da653486a8f59a07f4aa4cfca6')

        # Mercurial support
        shutil.rmtree(os.path.join(settings.WORKSPACE, 'repos'))
        self.project.slug = 'hgrepo'
        self.project.repo = os.path.abspath(os.path.join(self.data_dir,
                                                         self.hg_name))
        self.project.repo_type = self.project.HG
        self.project.save()
        vcs = self.project.vcs()

        # First run: clone
        vcs.update_source()
        self.assertEqual(vcs.latest_revision(), 1)
        self.assertEqual(Project.objects.get().latest_revision, 1)

        # Second run: update
        vcs.update_source()
        self.assertEqual(vcs.latest_revision(), 1)

    def test_git_history(self):
        """Fetching changelog for each build"""
        self._create_project()

        vcs = self.project.vcs()
        self.assertEqual(len(list(vcs.changelog('master'))), 2)
        self.assertEqual(len(list(vcs.changelog(
            'master', since='08df487ae5005c2e699e3030c236c56356f398f8',
        ))), 1)

    def test_hg_history(self):
        self._create_project()
        shutil.rmtree(os.path.join(settings.WORKSPACE, 'repos'))
        self.project.slug = 'hgrepo'
        self.project.repo = os.path.abspath(os.path.join(self.data_dir,
                                                         self.hg_name))
        self.project.repo_type = self.project.HG
        self.project.save()
        vcs = self.project.vcs()
        vcs.update_source()

        self.assertEqual(len(list(vcs.changelog('default'))), 2)
        self.assertEqual(len(list(vcs.changelog('default', 0))), 1)

        Command(
            ('hg branch foo && '
             'hg ci -m "Creating branch foo"'),
            cwd=self.project.repo
        )
        self.project.update_source()
        vcs = self.project.vcs()
        self.assertEqual(len(list(vcs.changelog('foo'))), 1)
        self.assertEqual(len(list(vcs.changelog('default'))), 2)

    def test_build_with_history(self):
        self._create_project()
        self.project.build_branches = Project.ALL_BRANCHES
        self.project.save()
        self.assertTrue(self.project.build())
        # First build - no history
        self.assertEqual(len(Build.objects.get().history_data), 0)

        # New branch, 1 commit away from master
        Command(
            ('git checkout -b foo && '
             'echo "yay" >> README && '
             'git commit -am "Added stuff to branch foo"'),
            cwd=self.project.repo,
        )

        self.assertTrue(self.project.build())
        # 1 new commit from last build bur first time branch was built
        self.assertEqual(len(self.project.builds.all()[0].history_data), 0)

        # New commit to master
        Command(
            ('git checkout master && '
             'echo "foobar" >> README && '
             'git commit -am "More instructions"'),
            cwd=self.project.repo,
        )
        self.assertTrue(self.project.build())
        last_build = self.project.builds.all()[0]
        self.assertEqual(len(last_build.history_data), 1)
        self.assertEqual(last_build.branch, 'master')
