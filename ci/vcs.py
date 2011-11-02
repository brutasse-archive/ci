import os

from StringIO import StringIO

from dulwich.client import get_transport_and_path
from dulwich.repo import Repo
from mercurial import hg, ui, localrepo


class Vcs(object):
    def __init__(self, repo_url, path):
        # For some reason mercurial has isinstance(foo, str) checks -- meaning
        # we are forced to explicitly use strings here.
        self.repo_url = str(repo_url)
        self.path = str(path)


class Git(Vcs):
    def update_source(self):
        """
        Clones if the project hasn't been cloned yet. Fetches otherwise.
        """
        client, host_path = get_transport_and_path(self.repo_url)
        if os.path.exists(self.path):
            target = Repo(self.path)
            client.fetch(
                host_path, target,
                determine_wants=target.object_store.determine_wants_all,
            )
        else:
            target = Repo.init(self.path, mkdir=True)
            refs = client.fetch(
                host_path, target,
                determine_wants=target.object_store.determine_wants_all,
            )
            target["HEAD"] = refs["HEAD"]
            tree_id = target["HEAD"].tree
            # Dulwich doesn't have a checkout command -- walk the tree
            # and write files.
            for entry in target.object_store.iter_tree_contents(tree_id):
                directory, path = os.path.split(entry.path)
                base = os.path.join(self.path, directory)
                if not os.path.exists(base):
                    os.makedirs(base)
                with open(os.path.join(base, path), 'wb') as f:
                    f.write(target.get_object(entry.sha).as_raw_string())
        return target

    def latest_revision(self):
        repo = Repo(self.path)
        return repo.ref('HEAD')


class ci(ui.ui):
    def __init__(self, *args, **kwargs):
        super(ci, self).__init__(*args, **kwargs)
        self.fout = StringIO()


class Hg(Vcs):
    def update_source(self):
        if os.path.exists(self.path):
            dest = localrepo.localrepository(ci(), path=self.path)
            remote = hg.peer(dest, {}, self.repo_url)
            dest.pull(remote)
            hg.clean(dest, None)
            hg.update(dest, None)
        else:
            source = hg.repository(ci(), self.repo_url)
            source, dest = hg.clone(ci(), {}, source, self.path,
                                    pull=True, update=True)
        return dest

    def latest_revision(self):
        repo = hg.repository(ci(), self.path)
        return str(repo.changectx(repo.changelog.tip()))
