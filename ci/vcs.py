import os

from StringIO import StringIO

from dulwich.repo import Repo
from mercurial import ui, hg

from .projects.utils import Command


class Vcs(object):
    def __init__(self, repo_url, path):
        self.repo_url = repo_url
        self.path = path


class Git(Vcs):
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
        repo = Repo(self.path)
        return repo.head()

    def branches(self):
        """
        Lists all local branches
        """
        repo = Repo(self.path)
        return [
            br[11:] for br in repo.refs.keys() if br.startswith('refs/heads/')
        ]

    def latest_branch_revision(self, branch):
        """
        Returns the SHA of a branch's HEAD
        """
        repo = Repo(self.path)
        return repo.get_refs()['refs/heads/' + branch]


class ci(ui.ui):
    def __init__(self, *args, **kwargs):
        super(ci, self).__init__(*args, **kwargs)
        self.fout = StringIO()


class Hg(Vcs):
    def update_source(self):
        if os.path.exists(self.path):
            cmd = 'cd %s && hg pull && hg update -C' % self.path
        else:
            cmd = 'hg clone %s %s' % (self.repo_url, self.path)
        command = Command(cmd)

    def latest_revision(self):
        repo = hg.repository(ci(), self.path)
        return str(repo.changectx(repo.changelog.tip()))
