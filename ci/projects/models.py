import datetime
import itertools
import logging
import os
import shutil

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .exceptions import BuildException
from .utils import Command

logger = logging.getLogger('ci')


class Project(models.Model):
    GIT = 'git'
    HG = 'hg'
    SVN = 'svn'

    REPO_TYPES = (
        (GIT, _('Git')),
        (HG, _('Mercurial')),
        (SVN, _('SVN')),
    )

    name = models.CharField(_('Name'), max_length=255)
    slug = models.SlugField(_('Slug'), max_length=255)

    repo = models.CharField(_('Repository'), max_length=1024)
    repo_type = models.CharField(_('Repository type'), max_length=10,
                                 choices=REPO_TYPES)
    build_instructions = models.TextField(_('Build instructions'))
    sequential = models.BooleanField(_('Sequential build?'), default=True)
    keep_build_data = models.BooleanField(_('Keep build data'), default=False)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return u'%s' % self.name

    @property
    def vcs_command(self):
        return {self.GIT: 'git clone %s',
                self.HG: 'hg clone %s',
                self.SVN: 'svn checkout %s'}[self.repo_type]

    @property
    def checkout_command(self):
        return self.vcs_command % self.repo

    @property
    def local_checkout_command(self):
        """
        For VCS that supports it, clone from the local copy instead
        of from the network.
        """
        return self.vcs_command % self.cache_dir

    # Update commands courtesy of Eric Holscher,
    # http://ericholscher.com/blog/2010/nov/15/correct-commands-check-out-
    # and-update-vcs-repos/

    @property
    def update_command(self):
        return {
            self.GIT: ('git --git-dir=.git fetch && '
                       'git --git-dir=.git reset --hard origin/master'),
            self.HG: ('hg pull && '
                      'hg update -C .'),
            self.SVN: ('svn revert --recursive . && '
                       'svn up --accept theirs-full'),
        }[self.repo_type]

    @property
    def cache_dir(self):
        """
        Directory where to put the local clone.
        """
        prefix = os.path.join(settings.WORKSPACE, 'repos')
        if not os.path.exists(prefix):
            os.makedirs(prefix)
        return os.path.join(prefix, str(self.pk))

    def build(self):
        """
        Trigger a build!
        """
        self.update_source()
        configs = self.configurations.all()
        meta = MetaBuild.objects.create(
            project=self,
            revision=self.latest_revision,
        )
        if configs:
            products = []
            for config in configs:
                products.append(config.values.all())
            items = itertools.product(*products)
            for values in items:
                build = Build.objects.create(
                    metabuild=meta,
                )
                if not self.sequential:
                    build.queue()
                build.values.add(*values)
            if self.sequential:
                meta.queue()
        else:
            build = Build.objects.create(
                metabuild=meta,
            )
            build.queue()

    def update_source(self):
        """
        Projects keep a full clone / checkout of the upstream repo for
        polling changes.
        """
        if os.path.exists(self.cache_dir):
            cmd = Command('cd %s && %s' % (
                self.cache_dir,
                self.update_command,
            ))
        else:
            cmd = Command('cd %s && %s %s' % (
                os.path.abspath(os.path.join(self.cache_dir, os.pardir)),
                self.checkout_command,
                self.pk
            ))
        if cmd.return_code != 0:
            assert False, "%s failed" % cmd.command

    @property
    def latest_revision(self):
        """
        Fetch the latest revision from SCM
        """
        if self.repo_type == self.SVN:
            cmd = Command('cd %s && svn info' % self.cache_dir)
            if not cmd.return_code == 0:
                assert False, "svn info failed"
            return cmd.out.split('\nRevision: ')[1].split()[0]

        if self.repo_type == self.GIT:
            cmd = Command('cd %s && git rev-parse HEAD' % self.cache_dir)
            if not cmd.return_code == 0:
                assert False, "git rev-parse failed"
            return cmd.out[:-1]

        if self.repo_type == self.HG:
            cmd = Command('cd %s && hg summary' % self.cache_dir)
            if not cmd.return_code == 0:
                assert False, "hg summary failed"
            return cmd.out.split('parent: ')[1].split(':')[0]


class Configuration(models.Model):
    """
    Multi-configurations ala jenkins: a key, several values, a build per value.
    """
    project = models.ForeignKey(Project, verbose_name=_('Project'),
                                related_name='configurations')
    key = models.CharField(_('Key'), max_length=255)

    def __unicode__(self):
        return u'%s' % self.key


class Value(models.Model):
    key = models.ForeignKey(Configuration, verbose_name=_('Key'),
                            related_name='values')
    value = models.CharField(_('Value'), max_length=255)

    def __unicode__(self):
        return u'%s' % self.value


class MetaBuild(models.Model):
    """
    Stores the metadata for a build axis / matrix
    """
    project = models.ForeignKey(Project, verbose_name=_('Project'),
                                related_name='builds')
    revision = models.CharField(_('Revision built'), max_length=1023)
    creation_date = models.DateTimeField(_('Date created'),
                                         default=datetime.datetime.now)

    def __unicode__(self):
        return u'Build #%s of %s' % (self.pk, self.project.name)

    class Meta:
        ordering = ('-creation_date',)

    def queue(self):
        """
        Trigger a sequential build.
        """
        from .tasks import execute_metabuild
        execute_metabuild.delay(self.pk)


class Build(models.Model):
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

    metabuild = models.ForeignKey(MetaBuild, verbose_name=_('Meta build'),
                                  related_name='builds')
    status = models.CharField(_('Status'), max_length=10,
                              choices=STATUSES, default=PENDING)
    creation_date = models.DateTimeField(_('Date created'),
                                         default=datetime.datetime.now)
    start_date = models.DateTimeField(_('Date started'), null=True)
    end_date = models.DateTimeField(_('Date ended'), null=True)
    values = models.ManyToManyField(Value, blank=True,
                                    verbose_name=_('Values'),
                                    related_name='builds')
    output = models.TextField(_('Build output'), blank=True)

    def __unicode__(self):
        values = ', '.join(map(unicode, self.values.all()))
        return u'Build #%s (%s)' % (self.pk, values)

    @property
    def build_path(self):
        prefix = os.path.join(settings.WORKSPACE, 'builds')
        if not os.path.exists(prefix):
            os.makedirs(prefix)
        return os.path.join(prefix, str(self.pk))

    def delete_build_data(self):
        if os.path.exists(self.build_path):
            logger.info("Cleaning build data")
            shutil.rmtree(self.build_path)

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
        logger.info("%s finished: SUCCESS" % self.__unicode__())
        self.end_date = datetime.datetime.now()
        self.status = self.SUCCESS
        if not self.metabuild.project.keep_build_data:
            self.delete_build_data()
        self.save()

    def checkout_source(self):
        """
        Performs a checkout / clone in the build directory.
        """
        logger.info("Checking out %s" % self.metabuild.project.repo)
        if self.metabuild.project.repo_type == Project.SVN:
            command = self.metabuild.project.checkout_command
        else:  # DVCS, we have a full local copy
            command = self.metabuild.project.local_checkout_command
        cmd = Command('cd %s && %s %s' % (
            os.path.join(settings.WORKSPACE, 'builds'),
            command,
            self.pk,
        ))
        self.check_response(cmd)

    def run(self):
        """
        Execute the build instructions given by the user.
        """
        logger.info("Generating build script")
        env = {value.key.key: value.value for value in self.values.all()}
        with open(os.path.join(self.build_path, 'ci-run.sh'), 'wb') as f:
            f.write(self.metabuild.project.build_instructions.replace('\r\n',
                                                                      '\n'))
        logger.info("Running build script")
        cmd = Command('cd %s && sh ci-run.sh' % self.build_path,
                      environ=env)
        self.check_response(cmd)

    def check_response(self, cmd):
        """
        Checks that a command is successful. Raises a BuildError if
        not, adds stdout and stderr to the build log.
        """
        if cmd.out:
            self.output += cmd.out
        if cmd.err:
            self.output += cmd.err
        if cmd.return_code != 0:
            msg = 'Error while running "%s": returned %s' % (
                cmd.command, cmd.return_code,
            )
            self.output += msg + '\n'
            self.status = self.FAILURE
            self.end_date = datetime.datetime.now()
            logger.info("%s failed: %s" % (self.__unicode__(), msg))
            self.save()
            raise BuildException(msg, cmd)
        logger.info("Command completed successfully: %s" % cmd.command)
        self.save()

    def queue(self):
        """
        Fires a celery task that runs the build.
        """
        from .tasks import execute_build  # avoid circular imports
        execute_build.delay(self.pk)