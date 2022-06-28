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

License
*******

This software is licensed under the terms of the Apache License 2.0
