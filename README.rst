CI
==

**[Work In Progress]** A simple continuous integration server written with
Django.

Don't use it unless you're interested in contributing. In which case, see
below.

Goals
-----

* Support for major DVCSs
* Build axes ala Jenkins
* Branch support
* Xunit, Cobertura reports. Stats porn.
* Comprehensive, read-write, HTTP API
* Real-time endpoint. No plugins.

Stack
-----

* Python
* Django
* SQL (Django ORM)
* Redis
* Celery

Hacking
-------

Setting up
``````````

Add to your ``~/.virtualenvs/postactivate``::

    export GEM_HOME="$VIRTUAL_ENV/gems"
    export GEM_PATH=""
    export PATH=$PATH:$GEM_HOME/bin

Setup your environment::

    git clone git://github.com/brutasse/ci.git
    cd ci
    sh bootstrap.sh
    make syncdb

Get `gorun`_.

.. _gorun: https://github.com/peterbe/python-gorun

Running
```````

Run all the things::

    make run

This will run:

* Django's runserver
* The Celery worker(s)
* Compass for compiling the CSS
* Gorun for running the tests when code changes (linux-only, cross-platform
  *and* native alternatives are welcome)

Testing
```````

To run the local test suite, do::

    make tests

The local tests are only mostly local, you need an internet connection for all
tests to pass.

To run the "live" tests (they make actual clones and builds from the
internet)::

    make livetests
