import anyjson as json
import datetime
import itertools
import logging
import os
import shutil

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .. import vcs
from ..parsers import XunitParser
from .exceptions import BuildException
from .utils import Command

logger = logging.getLogger('ci')


class Project(models.Model):
    GIT = 'git'
    HG = 'hg'

    REPO_TYPES = (
        (GIT, _('Git')),
        (HG, _('Mercurial')),
    )

    ALL_BRANCHES = 'all'
    DEFAULT_BRANCH = 'default'

    BRANCHES = (
        (DEFAULT_BRANCH, _('Default branch')),
        (ALL_BRANCHES, _('All')),
    )

    name = models.CharField(_('Name'), max_length=255)
    slug = models.SlugField(_('Slug'), max_length=255, unique=True)

    repo = models.CharField(
        _('Repository'), max_length=1024,
        help_text=_('The clone or checkout URL of your repository'),
    )
    repo_type = models.CharField(_('Repository type'), max_length=10,
                                 choices=REPO_TYPES, default=GIT)
    build_instructions = models.TextField(
        _('Build instructions'),
        help_text=_('The commands that need to be run in order to build the '
                    'project. The instructions are run from the root of your '
                    'repository. If you have mutliple configurations to run, '
                    'you can configure build axis separately.'),
    )
    sequential = models.BooleanField(
        _('Sequential build?'), default=True,
        help_text=_('Check this box to disallow parallel builds.'),
    )
    keep_build_data = models.BooleanField(
        _('Keep build data'), default=False,
        help_text=_('Check this box to keep build data on disk. Useful for '
                    'debugging builds but potentially eats a lot of disk '
                    'space.'),
    )
    xunit_xml_report = models.CharField(_('XML test report'), blank=True,
                                        max_length=1023)
    build_branches = models.CharField(_('Branches to build'), max_length=50,
                                      choices=BRANCHES, default=DEFAULT_BRANCH)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return u'%s' % self.name

    def save(self, *args, **kwargs):
        clone = self.pk is None
        super(Project, self).save(*args, **kwargs)
        if clone:
            from .tasks import clone_on_creation
            clone_on_creation.delay(self.pk)

    def get_absolute_url(self):
        return reverse('project', args=[self.slug])

    def vcs(self):
        return {
            self.GIT: vcs.Git,
            self.HG: vcs.Hg,
        }[self.repo_type](self.repo, self.cache_dir)

    @property
    def cache_dir(self):
        """
        Directory where to put the local clone.
        """
        prefix = os.path.join(settings.WORKSPACE, 'repos')
        if not os.path.exists(prefix):
            os.makedirs(prefix)
        return os.path.join(prefix, self.slug)

    def build(self):
        """
        Triggers a build!

        Returns True if the build is triggered, False if not
        (revisions are not built twice).
        """
        self.update_source()
        vcs = self.vcs()
        branches = ([vcs.default_branch]
                    if self.build_branches == self.DEFAULT_BRANCH
                    else vcs.branches())

        jobs = []
        for branch in branches:
            branch_jobs = self.build_branch(branch)
            if branch_jobs is not None:
                jobs = list(itertools.chain(jobs, branch_jobs))

        if self.sequential:
            from .tasks import execute_jobs
            execute_jobs.delay([j.pk for j in jobs])
        else:
            for job in jobs:
                job.queue()
        return bool(jobs)

    def build_branch(self, branch):
        rev = self.vcs().latest_branch_revision(branch)
        if self.builds.filter(branch=branch, revision=rev).exists():
            # Latest rev already build -- don't bother
            return
        configs = self.configurations.all()
        if configs:
            products = []
            matrix = {}
            for config in configs:
                matrix[config.key] = []
                values = config.values.all()
                products.append(values)
                for val in values:
                    matrix[config.key].append(val.value)
            items = itertools.product(*products)
        else:
            matrix = {}

        build = Build.objects.create(
            project=self,
            revision=rev,
            branch=branch,
            matrix=json.dumps(matrix),
            build_instructions=self.build_instructions,
            xunit_xml_report=self.xunit_xml_report,
        )
        jobs = []

        if configs:
            for values in items:
                job = Job.objects.create(
                    build=build,
                    values=json.dumps({v.key.key: v.value for v in values}),
                )
                jobs.append(job)
        else:
            job = Job.objects.create(
                build=build,
            )
            jobs.append(job)
        return jobs

    def update_source(self):
        """
        Projects keep a full clone / checkout of the upstream repo for
        polling changes.
        """
        self.vcs().update_source()

    @property
    def latest_revision(self):
        """
        Fetch the latest revision from SCM
        """
        vcs = self.vcs()
        vcs.update_source()
        return vcs.latest_revision()

    @property
    def build_status(self):
        """
        Success or failure? Or maybe still running...
        """
        if not self.builds.exists():
            return _('no build yet')
        return self.builds.all()[0].build_status

    def build_progress(self):
        builds = self.builds.all()[0].jobs.all()
        total = len(builds)
        done = len([b for b in builds if b.status in (b.SUCCESS, b.FAILURE)])
        return '%s/%s' % (done, total)

    def axis_initial(self):
        """
        Returns the initial data for axis forms.
        """
        initial = []
        for axis in self.configurations.all():
            initial.append({
                'name': axis.key,
                'values': ', '.join(map(unicode, axis.values.all())),
            })
        return initial


class Configuration(models.Model):
    """
    Multi-configurations ala jenkins: a key, several values, a build per value.
    """
    project = models.ForeignKey(Project, verbose_name=_('Project'),
                                related_name='configurations')
    key = models.CharField(_('Key'), max_length=255)

    def __unicode__(self):
        return u'%s' % self.key

    class Meta:
        unique_together = ('project', 'key')


class Value(models.Model):
    key = models.ForeignKey(Configuration, verbose_name=_('Key'),
                            related_name='values')
    value = models.CharField(_('Value'), max_length=255)

    def __unicode__(self):
        return u'%s' % self.value

    class Meta:
        unique_together = ('key', 'value')


class Build(models.Model):
    """
    Stores the metadata for a build axis / matrix
    """
    project = models.ForeignKey(Project, verbose_name=_('Project'),
                                related_name='builds')
    revision = models.CharField(_('Revision built'), max_length=1023)
    branch = models.CharField(_('Branch'), max_length=1023)
    creation_date = models.DateTimeField(_('Date created'),
                                         default=datetime.datetime.now)

    # These fields are serialized from the project. Lets users safely alter
    # config values when a build has already been trigerred: the build
    # has everything it needs.
    matrix = models.TextField(_('Build matrix'), blank=True)
    build_instructions = models.TextField(_('Build instructions'))
    xunit_xml_report = models.CharField(_('XML test report'), blank=True,
                                        max_length=1023)

    def __unicode__(self):
        return u'Build #%s of %s' % (self.pk, self.project.name)

    class Meta:
        ordering = ('-creation_date',)

    def queue(self):
        """
        Trigger a sequential build.
        """
        from .tasks import execute_jobs
        job_ids = list(self.jobs.values_list('pk', flat=True))
        execute_jobs.delay(job_ids)

    @property
    def matrix_data(self):
        """
        Returns the build matrix, json-loaded.
        """
        return json.loads(self.matrix)

    @property
    def build_status(self):
        builds = self.jobs.all()
        running = [build for build in builds if build.status == build.RUNNING]
        if running:
            return 'running'
        failed = [build for build in builds if build.status == build.FAILURE]
        if failed:
            return 'failed'
        success = [build for build in builds if build.status == build.SUCCESS]
        if success:
            return 'success'
        pending = [build for build in builds if build.status == build.PENDING]
        if pending:
            return 'pending'
        return 'not running. not failed. not success. not pending. what is it?'

    @property
    def short_rev(self):
        if len(self.revision) > 8:
            return self.revision[:8]
        return self.revision


class Job(models.Model):
    SUCCESS = 'success'
    FAILURE = 'failure'
    RUNNING = 'running'
    PENDING = 'pending'

    STATUSES = (
        (SUCCESS, _('Success')),
        (FAILURE, _('Failure')),
        (RUNNING, _('Running')),
        (PENDING, _('Pending')),
    )

    build = models.ForeignKey(Build, verbose_name=_('Build'),
                              related_name='jobs')
    status = models.CharField(_('Status'), max_length=10,
                              choices=STATUSES, default=PENDING)
    creation_date = models.DateTimeField(_('Date created'),
                                         default=datetime.datetime.now)
    start_date = models.DateTimeField(_('Date started'), null=True)
    end_date = models.DateTimeField(_('Date ended'), null=True)
    values = models.TextField(_('Values'), blank=True)
    output = models.TextField(_('Build output'), blank=True)
    xunit_xml_report = models.TextField(_('XML test report'), blank=True)

    def __unicode__(self):
        return u'Build #%s (%s)' % (self.pk,
                                    ", ".join(self.values_data.values()))

    class Meta:
        ordering = ('-id',)

    @property
    def build_path(self):
        prefix = os.path.join(settings.WORKSPACE, 'builds')
        if not os.path.exists(prefix):
            os.makedirs(prefix)
        return os.path.join(prefix, str(self.pk))

    @property
    def values_data(self):
        if self.values:
            return json.loads(self.values)
        return {}

    @property
    def xunit(self):
        """
        Parsed XML output.
        """
        if not hasattr(self, '_xunit'):
            self._xunit = XunitParser(self.xunit_xml_report)
        return self._xunit

    def delete_build_data(self):
        if os.path.exists(self.build_path):
            logger.info("Cleaning build data")
            shutil.rmtree(self.build_path)

    def vcs(self):
        return {
            Project.GIT: vcs.Git,
            Project.HG: vcs.Hg,
        }[self.build.project.repo_type](self.build.project.cache_dir,
                                        self.build_path)

    def execute(self):
        """
        Execute all the things!
        """
        logger.info("Starting %s" % self.__unicode__())
        self.status = self.RUNNING
        self.start_date = datetime.datetime.now()
        self.save()

        if not os.path.isdir(settings.WORKSPACE):
            logger.info("Creating workspace")
            os.makedirs(settings.WORKSPACE)

        self.delete_build_data()
        self.output = ''

        self.checkout_source()
        self.run()
        self.fetch_reports()
        logger.info("%s finished: SUCCESS" % self.__unicode__())
        self.end_date = datetime.datetime.now()
        self.status = self.SUCCESS
        if not self.build.project.keep_build_data:
            self.delete_build_data()
        self.save()

    def checkout_source(self):
        """
        Performs a checkout / clone in the build directory.
        """
        logger.info("Checking out %s" % self.build.project.repo)
        self.output += '[CI] Cloning...\n'
        vcs = self.vcs()
        vcs.update_source()
        vcs.checkout(self.build.revision)

    def run(self):
        """
        Execute the build instructions given by the user.
        """
        logger.info("Generating build script")
        env = json.loads(self.values) if self.values else {}
        with open(os.path.join(self.build_path, 'ci-run.sh'), 'wb') as f:
            f.write(self.build.build_instructions.replace('\r\n', '\n'))
        logger.info("Running build script")
        self.output += '[CI] Running build script...\n'
        self.save()
        cmd = Command('cd %s && sh ci-run.sh' % self.build_path,
                      environ=env, stream_to=self.stream_to)
        self.check_response(cmd)

    def check_response(self, cmd):
        """
        Checks that a command is successful. Raises a BuildError if
        not, adds stdout and stderr to the build log.
        """
        if cmd.out:
            self.output += cmd.out
        if cmd.return_code != 0:
            msg = 'Error while running "%s": returned %s' % (
                cmd.command, cmd.return_code,
            )
            self.output += msg + '\n'
            self.status = self.FAILURE
            self.end_date = datetime.datetime.now()
            logger.info("%s failed: %s" % (self.__unicode__(), msg))
            self.save()
            if not self.build.project.keep_build_data:
                self.delete_build_data()
            raise BuildException(msg, cmd)
        logger.info("Command completed successfully: %s" % cmd.command)
        self.save()

    def fetch_reports(self):
        """
        Stores the XML reports.
        """
        if not self.build.xunit_xml_report:
            return

        with open(os.path.join(self.build_path,
                               self.build.xunit_xml_report)) as xml:
            self.xunit_xml_report = xml.read()
        self.save()

    def queue(self):
        """
        Fires a celery task that runs the build.
        """
        from .tasks import execute_job  # avoid circular imports
        execute_job.delay(self.pk)

    def stream_to(self, output):
        """
        Method passed to the command constructor, which appends the
        ouput and saves it every second.
        """
        if not hasattr(self, 'last_save'):
            self.last_save = datetime.datetime.now()

        self.output += output
        if (self.last_save + datetime.timedelta(seconds=1) <
            datetime.datetime.now()):
            self.save()
            self.last_save = datetime.datetime.now()
