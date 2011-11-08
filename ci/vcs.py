import os

from datetime import datetime
from StringIO import StringIO

from dulwich.repo import Repo
from dulwich.walk import Walker
from mercurial import ui, hg

from .shell import Command


class Commit(object):
    """
    A common object to represent a commit.
    """
    def __init__(self, rev, author, timestamp, message, files):
        self.rev = rev
        self.author = author
        self.timestamp = timestamp
        self.message = message
        self.files = sorted(files)

    @property
    def serializable(self):
        serialible = self.__dict__
        serialible['timestamp'] = self.timestamp.isoformat()
        return serialible


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
        if not hasattr(self, '_repo'):
            self._repo = Repo(self.path)
        return self._repo

    def update_source(self):
        """
        Clones if the project hasn't been cloned yet. Fetches otherwise.
        """
        cwd = None
        if os.path.exists(self.path):
            cwd = self.path
            cmd = 'git fetch && git reset --hard origin/master'
        else:
            cmd = 'git clone %s %s' % (self.repo_url, self.path)
        Command(cmd, cwd=cwd)

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
        Command('git checkout %s && git reset --hard %s' % (
            branch, revision,
        ), cwd=self.path)

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
        for entry in walker:
            if since is not None and entry.commit.id == since:
                break
            commit = entry.commit
            files = Command(
                'git show --pretty="format:" --name-only %s' % commit.id,
                cwd=self.path,
            ).out.split()
            yield Commit(
                commit.id,
                commit.committer,
                datetime.fromtimestamp(commit.commit_time),
                commit.message,
                files,
            )


class ci(ui.ui):
    def __init__(self, *args, **kwargs):
        super(ci, self).__init__(*args, **kwargs)
        self.fout = StringIO()


class Hg(Vcs):
    default_branch = 'default'

    @property
    def repo(self):
        if not hasattr(self, '_repo'):
            self._repo = hg.repository(ci(), self.path)
        return self._repo

    def update_source(self):
        cwd = None
        if os.path.exists(self.path):
            cwd = self.path
            cmd = 'hg pull && hg update -C'
        else:
            cmd = 'hg clone %s %s' % (self.repo_url, self.path)
        Command(cmd, cwd=cwd)

    def latest_revision(self):
        return self.latest_branch_revision('default')

    def branches(self):
        return sorted(self.repo.branchtags().keys())

    def latest_branch_revision(self, branch):
        return self.repo.changelog.rev(self.repo.branchtags()[branch])

    def checkout(self, branch, revision):
        Command('hg update -C %s && hg update -r %s' % (
            branch, revision,
        ), cwd=self.path)

    def changelog(self, branch, since=None):
        current_ctx = self.repo.changectx(self.latest_branch_revision(branch))
        watch = [current_ctx]
        while watch:
            head = watch.pop(0)
            parents = [p for p in head.parents() if p.branch() == branch]
            watch.extend(parents)
            if head.rev() in [-1, since]:
                break
            yield Commit(
                head.rev(),
                head.user(),
                datetime.fromtimestamp(head.date()[0]),
                head.description(),
                head.files(),
            )
