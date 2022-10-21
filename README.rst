Kyle's Tutor plugins
####################

Various single-module `Tutor <https://docs.tutor.overhang.io>`_ plugins that I use in my daily setup.

Some of these may be precursors to proper plugins;
others may be prototypes of new core Tutor functionality that I plan to propose;
others yet may always remain one-off plugins in this repository.

Installation
************

::

    pip install git+https://github.com/kdmccormick/tutor-contrib-kdmccormick

Plugins
*******

quickdev
========

An alternative to `Tutor's Open edX development workflow <https://docs.tutor.overhang.io/dev.html>`_ that is hopefully simpler, quicker, and less bandwidth-intensive.

Setup
-----

Run these once to enable the plugin::

  tutor plugins enable quickdev
  tutor config save
  tutor dev dc build lms

Every time you pull new images, you'll need to re-build the development image::

  tutor dev dc build lms

Of course, as usual, if you haven't already launched (a.k.a. quickstarted), you'll need to do that::

  tutor dev launch

Running Tutor with your copy of edx-platform
--------------------------------------------

Start the platform with your code mounted using ``-m/--mount``::

  tutor dev start -m path/to/your/edx-platform

That's it! As usual, you should be to load LMS a http://local.overhang.io:8000 and CMS at http://studio.local.overhang.io:8001. If you change your local edx-platform code, you should be able to see the changes reflected immediately. If you don't, you can always force-restart the containers::

  tutor dev restart

Running commands in containers works as usual. You can use ``exec`` a command in a container that are already running::

  tutor dev exec lms ./manage.py lms migrate

or you can use ``run`` the command in its own container (remember: with ``run``, you need to specify ``-m/--mount`` again)::

  tutor dev run -m path/to/your/edx-platform lms ./manage.py migrate

Finally, as always, you can stop the platform when you're done::

  tutor dev stop

Installing packages and re-generating assets
--------------------------------------------

With ``quickdev``, your containers (whether mounted with edx-platform or not) come ready-to-use with updated reqiurements and static assets. However, if you have modified:

* the Python requirements lists under edx-platform/requirements,
* the NPM requirements lists in package-lock.json,
* the SCSS files in edx-platform, or
* the assets of an installed XBlock,

then you may want to re-generate these resources. You can do so using ``tutor dev run``. Unlike vanilla Tutor, the ``quickdev`` plugin will make sure that **your updates are persisted between platform restarts**. For example, you may want to modify the version of a specific Python requirement::
  
  tutor dev run lms pip install 'requests==2.28.1'

or re-install all Python requirements::

  tutor dev run lms pip install -r requirements/edx/

or re-install all NPM requirements::

  tutor dev run lms npm clean-install

or re-generate all static assets::

  tutor dev run lms openedx-assets build --env=dev

Finally, if you want to revert to the original version of any of these resources, as built into the ``openedx`` Docker image, ``quickdev`` provides utilities for that (note: these command will stop your containers)::

  tutor quickdev pip-restore
  tutor quickdev npm-restore
  tutor quickdev static-restore

XBlock and edx-platform plugin development
------------------------------------------

In some cases, you will have to develop features for packages that are pip-installed next to the edx-platform. This is easy with ``quickdev``.

TODO.

automountvenvs
==============

Auto-mount folders prefixed with "venv-" as virtualenvs in various Tutor services.

::

    # setup:
    tutor plugins enable automountvenvs
    tutor config save

    # example usage:
    tutor dev start -d -m edx-platform -m venv-openedx -m course-discovery -m venv-discovery

    # without this plugin, that would have been:
    tutor dev start -d -m edx-platform \
        -m lms,lms-worker,lms-job,cms,cms-worker,cms-job:venv-openedx:/openedx/venv
        -m course-discovery \
        -m discovery,discovery-job:venv-discovery:/openedx/venv

Roadmap: Retire this plugin in favor of ``quickdev``.

stopnightly
===========

Automatically stop Tutor Nightly containers whenever starting (stable) Tutor containers, and vice versa.

Running multiple instances of Tutor simultaneously one machine will cause a lot of errors than can be hard to diagnose until you realize what's going on. 
In recognition of this, Tutor v13+ already automatically stops local your local platform when starting a dev platform, and vice versa. It doesn't, however, stop Nightly platforms when starting a stable platform (or vice versa).
This plugin handles that, although the approach is kinda hacky.

::

    # setup (assumes you have Tutor installed from a local git repo)
    cd < path to your tutor repo >
    git checkout master
    tutor plugins enable stopnightly
    tutor config save
    git checkout nightly
    tutor plugins enable stopnightly
    tutor config save

    # example usage:
    cd < path to your tutor repo >
    git checkout master     # From the latest stable Tutor version...
    tutor local start -d    #   start a local platform.
    git checkout nightly    # From the latest Tutor Nightly version...
    tutor local start -d    #   start a local platform. Your first platform is automatically stopped.
    git checkout master     # Switching back to the latest stable Tutor version...
    tutor dev start -d      #   start a dev platform. Your Nightly platform is automatically stopped.

Roadmap: Propose as core Tutor feature, if and only if I can find a less hacky way to implement it. May require expansion of the V1 plugin API as a prerequisite. Related to a `Tutor DevEnv project issue <https://github.com/overhangio/2u-tutor-adoption/issues/74>`_.
    

License
*******

This software is licensed under the terms of the Apache License 2.0
