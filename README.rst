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

Roadmap: Propose as core Tutor feature.

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
    
quickdev
========

Docs coming soon!

License
*******

This software is licensed under the terms of the Apache License 2.0
