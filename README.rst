CI
==

**[Work In Progress]** A simple continuation integration tool written with
Django.

Don't use it unless you're interested in contributing. In which case, see
below.

Hacking
-------

Setup your environment::

    git clone git://github.com/brutasse/ci.git
    cd ci
    sh bootstrap.sh
    make syncdb

Get `gorun`_.

.. _gorun: https://github.com/peterbe/python-gorun

Run all the things::

    make run

This will run:

* Django's runserver
* The Celery worker(s)
* Compass for compiling the CSS
* Gorun for running the tests when code changes (linux-only, cross-platform
  *and* native alternatives are welcome)
