CI
==

**[Work In Progress]** A simple continuation integration tool written with
Django.

Don't use it unless you're interested in contributing. In which case, see
below.

Hacking
-------

Setup your environment::

    git clone @git://github.com/brutasse/ci.git
    cd ci
    sh bootstrap.sh
    django-admin.py syncdb --settings=ci.settings

Run the dev server::

    foreman start
