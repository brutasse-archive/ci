import datetime
import itertools
import os
import shutil

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .exceptions import BuildException
from .utils import Command


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
    def checkout_command(self):
        return {self.GIT: 'git clone %s',
                self.HG: 'hg clone %s',
                self.SVN: 'svn checkout %s'}[self.repo_type] % self.repo

    def build(self):
        """
        Trigger a build!
        """
        configs = self.configurations.all()
        if configs:
            products = []
            for config in configs:
                products.append(config.values.all())
            items = itertools.product(*products)
            for values in items:
                build = Build.objects.create(
                    project=self,
                )
                build.values.add(*values)
        else:
            Build.objects.create(
                project=self,
            )


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

    project = models.ForeignKey(Project, verbose_name=_('Project'),
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
        return u'Build #%s (%s) - %s' % (self.pk, values,
                                         self.get_status_display())

    @property
    def build_path(self):
        return os.path.join(settings.WORKSPACE, str(self.pk))

    def delete_build_data(self):
        if os.path.exists(self.build_path):
            shutil.rmtree(self.build_path)

    def execute(self):
        """
        Execute all the things!
        """
        self.status = self.RUNNING
        self.start_date = datetime.datetime.now()
        self.save()

        if not os.path.isdir(settings.WORKSPACE):
            os.makedirs(settings.WORKSPACE)

        self.delete_build_data()
        self.output = ''

        self.checkout_source()
        self.run()
        self.end_date = datetime.datetime.now()
        self.status = self.SUCCESS
        if not self.project.keep_build_data:
            self.delete_build_data()
        self.save()

    def checkout_source(self):
        """
        Performs a checkout / clone in the build directory.
        """
        cmd = Command('cd %s && %s %s' % (
            settings.WORKSPACE,
            self.project.checkout_command,
            self.pk,
        ))
        self.check_response(cmd)

    def run(self):
        """
        Execute the build instructions given by the user.
        """
        env = {value.key.key: value.value for value in self.values.all()}
        with open(os.path.join(self.build_path, 'ci-run.sh'), 'wb') as f:
            f.write(self.project.build_instructions.replace('\r\n', '\n'))
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
            self.save()
            raise BuildException(msg, cmd)
        self.save()
