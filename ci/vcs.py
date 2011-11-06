import os

from StringIO import StringIO

from dulwich.repo import Repo
from dulwich.walk import Walker
from mercurial import ui, hg

from .projects.utils import Command


class Vcs(object):
    def __init__(self, repo_url, path):
        self.repo_url = repo_url
        self.path = path


class Git(Vcs):
    default_branch = 'master'

    @property
    def repo(self):
        """Needed as a property since self.path may not exist at
        instanciation time."""
        return Repo(self.path)

    def update_source(self):
        """
        Clones if the project hasn't been cloned yet. Fetches otherwise.
        """
        if os.path.exists(self.path):
            cmd = 'cd %s && git fetch && git reset --hard origin/master' % (
                self.path,
            )
        else:
            cmd = 'git clone %s %s' % (self.repo_url, self.path)
        command = Command(cmd)

    def latest_revision(self):
        return self.latest_branch_revision('master')

    def branches(self):
        """
        Lists all local branches
        """
        return sorted([
            br[20:] for br in self.repo.refs.keys() if (
                br.startswith('refs/remotes/origin/') and
                br[20:] != 'HEAD'
            )
        ])

    def checkout(self, branch, revision):
        Command('cd %s && git checkout %s && git reset --hard %s' % (
            self.path, branch, revision,
        ))

    def latest_branch_revision(self, branch):
        """
        Returns the SHA of a branch's HEAD
        """
        return self.repo.get_refs()['refs/remotes/origin/' + branch]

    def changelog(self, branch, since=None):
        """
        Returns the commits made in branch <branch> since revision <since>.
        """
        walker = Walker(self.repo, [self.latest_branch_revision(branch)])
        commits = []
        for entry in walker:
            if since is not None and entry.commit.id == since:
                break
            yield entry.commit


class ci(ui.ui):
    def __init__(self, *args, **kwargs):
        super(ci, self).__init__(*args, **kwargs)
        self.fout = StringIO()


class Hg(Vcs):
    default_branch = 'default'

    def update_source(self):
        if os.path.exists(self.path):
            cmd = 'cd %s && hg pull && hg update -C' % self.path
        else:
            cmd = 'hg clone %s %s' % (self.repo_url, self.path)
        command = Command(cmd)

    def latest_revision(self):
        return self.latest_branch_revision('default')

    def branches(self):
        repo = hg.repository(ci(), self.path)
        return sorted(repo.branchtags().keys())

    def latest_branch_revision(self, branch):
        repo = hg.repository(ci(), self.path)
        return repo.changelog.rev(repo.branchtags()[branch])

    def checkout(self, branch, revision):
        Command('cd %s && hg update -C %s && hg update -r %s' % (
            self.path, branch, revision,
        ))
