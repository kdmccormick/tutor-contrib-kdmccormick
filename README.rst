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

Plugin: quickdev
****************

This plugin provides an alternative to `Tutor's Open edX development workflow <https://docs.tutor.overhang.io/dev.html>`_ that is hopefully simpler, quicker, and less bandwidth-intensive.

Setup
=====

Run these once to enable the plugin::

  tutor plugins enable quickdev
  tutor config save
  tutor dev dc build lms

Every time you pull new images, you'll need to re-build the development image::

  tutor dev dc build lms

Of course, as usual, if you haven't already launched Tutor (a.k.a. quickstarted), you'll need to do that::

  tutor dev launch

Running Tutor with your copy of edx-platform
============================================

Developers often want to run Open edX using a modififed local copy of edx-platform. The quickdev plugin makes this easy. Just start the platform with your code bind-mounted using ``-m/--mount``::

  tutor dev start -m path/to/your/edx-platform

That's it! As usual, you should be able to load LMS at http://local.overhang.io:8000 and CMS at http://studio.local.overhang.io:8001. If you make changes to your local edx-platform code, the LMS and CMS dev servers should automatically restart and manifest your changes. If they don't, you can always force-restart the containers::

  tutor dev restart

Running commands in containers works as usual. You can ``exec`` a command in a container that is already running::

  tutor dev exec lms ./manage.py lms migrate

or you can ``run`` a command in its own container (remember: with ``run``, you need to specify ``-m/--mount`` again)::

  tutor dev run -m path/to/your/edx-platform lms ./manage.py migrate

Remember: with ``run``, you are starting a new just container for your command, so you must specify ``-m/--mount`` again. With ``exec``, you are using one of the containers that you created earlier when you ran ``start``, so whichever ``-m/--mount`` options you specified then will still be in effect.

If you want to change which directory or directories are bind-mounted, just run ``start`` again::

  tutor dev start -m path/to/another/copy/of/edx-platform

Finally, as always, you can stop the platform when you're done::

  tutor dev stop

Installing packages and re-generating assets
============================================

With ``quickdev``, your containers (whether mounted with edx-platform or not) come ready-to-use with updated reqiurements and static assets. However, if you have modified:

* the Python requirements lists under edx-platform/requirements,
* the NPM requirements lists in package-lock.json,
* the SCSS files in edx-platform, or
* the assets of an installed XBlock,

then you may want to re-generate these resources. You can do so using ``tutor dev run``. Unlike vanilla Tutor, the ``quickdev`` plugin will make sure that **your updates are persisted between platform restarts**. For example, you may want to modify the version of a specific Python requirement::
  
  tutor dev run lms pip install 'requests==2.28.1'

or re-install all Python requirements::

  tutor dev run lms pip install -r requirements/edx/development.txt

or re-install all NPM requirements::

  tutor dev run lms npm clean-install

or re-generate all static assets::

  tutor dev run lms openedx-assets build --env=dev

Finally, if you want to revert to the original version of any of these resources, as built into the ``openedx`` Docker image, ``quickdev`` provides utilities for that (note: these commands will stop your containers)::

  tutor quickdev pip-restore     # Revert back to Python packages from image.
  tutor quickdev npm-restore     # Revert back to NPM packages from image.
  tutor quickdev static-restore  # Revert bakc to generated static assets from image.

XBlock and edx-platform plugin development
==========================================

In some cases, you will have to develop features for packages that are pip-installed into edx-platform. In order to install a local copy of a package into edx-platform, simply ``pip install`` the package using editable mode (``-e``) into LMS or CMS while your repository is bind-mounted (``-m path/to/your/local/xblock-or-library``). For example::

  tutor dev run -m ../xblock-drag-and-drop-v2 lms pip install -e /openedx/mounted-packages/xblock-drag-and-drop-v2

Tip: If Tutor failed with *"No mount for ..."*, then this will be slightly more complicated for you; see the `notes on bind-mounting`_.

Next, for pacakges that add static assets to the platform, such as most XBlocks, you will then want to rebuild static assets using ``openedx-assets``::

  tutor dev run -m ../xblock-drag-and-drop-v2 lms openedx-assets build --env=dev

Notice that we continue bind-mounting our local repository with ``-m``; we will need to do this as long as our local package is installed. Now, finallly, start your platform::

  tutor dev start -m ../xblock-drag-and-drop-v2

That's it! Changes to your local package should be immediately manifested in the LMS and CMS. If they are not, manually restarting the platform (``tutor dev restart``) should do the trick. 

Going further, you can bind-mount multiple edx-platform packages, and even edx-platform itself, simultaneously. For example, if you were working on both ``xblock-drag-and-drop-v2`` and ``platform-plugin-coaching``, *and* you wanted to run local edx-platform code as well, you might run::

  tutor dev run -m ../xblock-drag-and-drop-v2 -m ../platform-plugin-coaching lms bash
  app@lms$ pip install -e /openedx/mounted-packages/xblock-drag-and-drop-v2
  app@lms$ pip install -e /openedx/mounted-packages/platform-plugin-coaching
  app@lms$ openedx-assets build --env=dev
  app@lms$ exit
  tutor dev start -m ../edx-platform -m ../xblock-drag-and-drop-v2 -m ../platform-plugin-coaching

For conveninece, the quickdev plugin also provides the ``pip-install-mounted`` command, which installs all packages at /openedx/mounted-packages and. When provided the ``-s/--build-static`` flag, the command will also rebuild static assets. For example, the commands above could be shortened to::

  tutor quickdev pip-install-mounted -m ../xblock-drag-and-drop-v2 -m ../platform-plugin-coaching
  tutor dev start -m ../edx-platform -m ../xblock-drag-and-drop-v2 -m ../platform-plugin-coaching

_notes on bind-mounting::

Notes on package bind-mounting
------------------------------

For convenience, quickdev will try to recognize when you mount edx-platform packages and automatically mount them in a helpful location. Specifically, if you provide ``-m/--mount`` with a directory named any of the following:

* ``xblock-*``
* ``platform-lib-*``
* ``platform-plugin-*``

then the directory will be automatically mounted in all LMS and CMS containers (including workers and job runners) under the path /openedx/mounted-packages. That is why we were able to execute ``pip install -e /openedx/mounted-package/xblock-drag-and-drop-v2`` in previous steps without ever specifying where xblock-drag-and-drop-v2 should be mounted.

Now, you may have an edx-platform package that does not use the supported directory naming conveition. In that case, you have two options. Firstly, you could rename your package's directory so that it matches the naming convention. For example::

  mv ../staff_graded-xblock ../xblock-staff-graded
  tutor dev run -m ../xblock-staff-graded lms pip install -e /openedx/mounted-packages/xblock-staff-graded
  ...

Secondly, you could manually specify where and how your package directory should be mounted using the explicit form of ``-m/--mount``. For example::
   
  tutor dev run \
    -m lms,cms,lms-worker,cms-worker,lms-job,cms-job:../staff_graded-xblock:/openedx/mounted-packages/staff_graded-xblock \
    lms pip install -e /openedx/mounted-packages/staff_graded-xblock
  ...

For more details, see Tutor's official `documentation on bind-mounting <https://docs.tutor.overhang.io/dev.html#bind-mount-volumes-with-mount>`_.

Roadmap
=======

I will propose to incorporate these changes upstream into Tutor via a TEP (Tutor Enhancement Proposal).


Plugin: automountvenvs
**********************

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


Roadmap
=======

I am be retiring this plugin in favor of ``quickdev``, described above.

Plugin: stopnightly
*******************

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

Roadmap
=======

Propose as core Tutor feature, if and only if I can find a less hacky way to implement it. May require expansion of the V1 plugin API as a prerequisite. Related to a `Tutor DevEnv project issue <https://github.com/overhangio/2u-tutor-adoption/issues/74>`_.
    

License
*******

This software is licensed under the terms of the Apache License 2.0
