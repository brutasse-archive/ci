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
    default_branch = 'master'

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
        repo = Repo(self.path)
        return sorted([
            br[20:] for br in repo.refs.keys() if (
                br.startswith('refs/remotes/origin/') and
                br[20:] != 'HEAD'
            )
        ])

    def checkout(self, revision):
        Command('cd %s && git checkout %s' % (self.path, revision))

    def latest_branch_revision(self, branch):
        """
        Returns the SHA of a branch's HEAD
        """
        repo = Repo(self.path)
        return repo.get_refs()['refs/remotes/origin/' + branch]


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
        return sorted([repo[n].branch() for n in repo.heads()])

    def latest_branch_revision(self, branch):
        repo = hg.repository(ci(), self.path)
        return repo.changelog.rev(repo.branchtags()[branch])

    def checkout(self, revision):
        Command('cd %s && hg checkout %s' % (self.path, revision))
