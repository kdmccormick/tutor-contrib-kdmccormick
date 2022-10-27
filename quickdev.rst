The "quickdev" Tutor plugin
***************************

This plugin provides an alternative to `Tutor's Open edX development workflow <https://docs.tutor.overhang.io/dev.html>`_ that is hopefully simpler, quicker, and less bandwidth-intensive.

Documentation:

* `Why? <#why>`_
* `Setup <#setup>`_
* `Running Tutor with your copy of edx-platform <#running-tutor-with-your-copy-of-edx-platform>`_
* `Installing packages and re-generating assets <#installing-packages-and-re-generating-assets>`_
* `XBlock and edx-platform plugin development <#xblock-and-edx-platform-plugin-development>`_
* `Roadmap <#roadmap>`_

If you are interested in the plugin's internal technical details, please see the code itself in `quickdev.py <./tutorkdmccormick/quickdev.py>`_. I've tried to make the implementation and its rationale as clear as possible.

Why?
====

The current ``tutor dev`` workflow (`documented here <https://docs.tutor.overhang.io/dev.html>`_) is excellent, right up until the point where you start wanting to run Open edX using edx-platform or edx-platform packages from your host machine. (If you already understand this, you might skip right to the `Setup <#setup>`_ section.) At that point, you'll either need to `rebuild your openedx-dev image every time you make a change <https://docs.tutor.overhang.io/configuration.html#custom-open-edx-docker-image>`_, or you'll need to bind-mount edx-platform using ``-m/--mount``.

Bind-mounting works great, except that when you mount edx-platform, it overshadows several important folders built into the container image:

* edx-platform's NPM packages (``/openedx/edx-platform/node_modules``),
* edx-platform's metadata/entrypoint bundle (``/openedx/edx-platform/Open_edX.egg-info``), and
* edx-platform's static assets (various ``/openedx/edx-platform`` subdirectories).

That is why you need to run `some costly additional setup commands <https://docs.tutor.overhang.io/dev.html#setting-up-a-development-environment-for-edx-platform>`_ in order to prepare your bind-mounted edx-platform repository for use with Tutor, which, frustatingly, generally just *re-downloads and re-generates what was already on the openedx-dev image*. Even worse, bind-mounted volumes (like your edx-platform repository) are subject to write performance penalties on macOS and Windows hosts, meaning that these steps can take a very long time for many Open edX developers.

The quickdev plugin addresses this by turning all those "overshadowed" folders into `named Docker volumes <https://docs.docker.com/storage/volumes>`_, which are pre-populated with the contents from the image, and layered on top of edx-platform. That way, developers can ``start`` tutor with ``--mount=edx-platform``, and it Just Works (TM), no additional setup required. Of course, a developer can still re-run those setup steps (``npm install``, ``pip install ...``, and ``openedx-assets ...``), but they only need to do so *if they made a change that would warrant re-running those commands*, such as updating a requirements list or changing an SCSS file.

Furthermore, the plugin makes a named Docker volume for all LMS/CMS dev containers' Python virtual environments, which means *changes to installed requirements or generated assets are shared between containers and saved between platform restarts*. For developers who wish to work on Python packages, this `provides an alternative <#xblock-and-edx-platform-plugin-development>`_ to the current `edx-platform package development workflow <https://docs.tutor.overhang.io/dev.html#xblock-and-edx-platform-plugin-development>`_. It also removes the need for developers to ever worry about the complexities of copy or bind-mounting virtual environments into Tutor containers, as the LMS/CMS dev containers will all share one more-efficiently-mounted virtual environment.

Setup
=====

Install the ``tutor-plugin-kdmccormick`` project as described in the `README <./README.rst>`_::

  pip install git+https://github.com/kdmccormick/tutor-contrib-kdmccormick

Run these commands once to enable the quickdev plugin::

  tutor plugins enable quickdev
  tutor config save
  tutor dev dc build lms

Every time you pull new images, you'll need to re-build the development image::

  tutor dev dc build lms

Of course, as usual, if you haven't already launched Tutor (a.k.a. quickstarted), you'll need to do that::

  tutor dev launch

Notes for this guide
--------------------

This guide assumes that you haved cloned edx-platform (and, optionally, edx-platform packages) to be siblings of your working directory. Your directories do not have to be organized that way, but if they're not, make sure to adjust the paths in the commands below accordingly.

This plugin has been tested with the latest version of `Tutor Nightly <https://docs.tutor.overhang.io/tutorials/nightly.html>`_, on both Ubuntu 20.04 (AMD64) and macOS Ventura (ARM64).


Running Tutor with your copy of edx-platform
============================================

Developers often want to run Open edX using a modified local copy of edx-platform. The quickdev plugin makes this easy. Just start the platform with your code bind-mounted using ``-m/--mount``::

  tutor dev start -m ../edx-platform

That's it! As usual, you should be able to load LMS at http://local.overhang.io:8000 and CMS at http://studio.local.overhang.io:8001. If you make changes to your local edx-platform code, the LMS and CMS dev servers should automatically restart and manifest your changes. If they don't, you can always force-restart the containers::

  tutor dev restart

Running commands in containers works as usual. You can ``exec`` a command in a container that is already running::

  tutor dev exec lms ./manage.py lms migrate

or you can ``run`` a command in its own container (remember: with ``run``, you need to specify ``-m/--mount`` again)::

  tutor dev run -m ../edx-platform lms ./manage.py lms migrate

Remember: with ``run``, you are starting a new just container for your command, so you must specify ``-m/--mount`` again. With ``exec``, you are using one of the containers that you created earlier when you ran ``start``, so whichever ``-m/--mount`` options you specified then will still be in effect.

If you want to change which directory or directories are bind-mounted, just run ``start`` again::

  # Bind-mount a different copy of edx-platform:
  tutor dev start -m ../another-copy-of/edx-platform
  
  # Stop bind-mounting edx-platform (i.e., go back to using the code on the image):
  tutor dev start

Finally, as always, you can stop the platform when you're done::

  tutor dev stop

Installing packages and re-generating assets
============================================

With ``quickdev``, your containers (whether mounted with edx-platform or not) come ready-to-use with updated requirements and static assets. However, if you have modified:

* the Python requirements lists under edx-platform/requirements,
* the NPM requirements list in package-lock.json,
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
  tutor quickdev static-restore  # Revert back to generated static assets from image.

XBlock and edx-platform plugin development
==========================================

In some cases, you will have to develop features for packages that are pip-installed into edx-platform. In order to install a local copy of a package into edx-platform, simply ``pip install`` the package using editable mode (``-e``) from LMS or CMS while your package directory is bind-mounted at /openedx/mounted-packages (``-m path/to/your/local/xblock-or-library``). For example::

  tutor dev run -m ../xblock-drag-and-drop-v2 lms pip install -e /openedx/mounted-packages/xblock-drag-and-drop-v2

Tip: If Tutor failed with *"No mount for ..."*, then this will be slightly more complicated for you; see the `notes on bind-mounting <#notes-on-package-bind-mounting>`_ below.

Next, for packages that add static assets to the platform, such as most XBlocks, you will then want to rebuild static assets using ``openedx-assets``::

  tutor dev run -m ../xblock-drag-and-drop-v2 lms openedx-assets build --env=dev

Notice that we continue bind-mounting our local directory with ``-m``; we will need to do this as long as our local package is installed. Now, finally, start your platform::

  tutor dev start -m ../xblock-drag-and-drop-v2

That's it! Changes to your local package should be immediately manifested in the LMS and CMS. If they are not, manually restarting the platform (``tutor dev restart``) should do the trick. 

Going further, you can bind-mount multiple edx-platform packages, and even edx-platform itself, simultaneously. For example, if you were working on both ``xblock-drag-and-drop-v2`` and ``platform-plugin-notices``, *and* you wanted to run local edx-platform code as well, you might run::

  tutor dev run -m ../edx-platform -m ../xblock-drag-and-drop-v2 -m ../platform-plugin-notices lms bash
  app@lms$ pip install -e /openedx/mounted-packages/xblock-drag-and-drop-v2
  app@lms$ pip install -e /openedx/mounted-packages/platform-plugin-notices
  app@lms$ openedx-assets build --env=dev
  app@lms$ exit
  tutor dev start \
      -m ../edx-platform -m ../xblock-drag-and-drop-v2 -m ../platform-plugin-notices

For convenience, the quickdev plugin also provides the ``pip-install-mounts`` command, which installs all packages at /openedx/mounted-packages. When provided the ``-s/--build-static`` flag, the command will also rebuild static assets. For example, the commands above could be shortened to::

  tutor quickdev pip-install-mounts --build-static \
      -m ../edx-platform -m ../xblock-drag-and-drop-v2 -m ../platform-plugin-notices
  tutor dev start \
      -m ../edx-platform -m ../xblock-drag-and-drop-v2 -m ../platform-plugin-notices

Notes on package bind-mounting
------------------------------

For convenience, quickdev will try to recognize when you mount edx-platform packages and automatically mount them in a helpful location. Specifically, if you provide ``-m/--mount`` with a directory named any of the following:

* ``xblock-*``
* ``platform-lib-*``
* ``platform-plugin-*``

then the directory will be automatically mounted in all LMS and CMS containers (including workers and job runners) under the path /openedx/mounted-packages. That is why we were able to execute ``pip install -e /openedx/mounted-package/xblock-drag-and-drop-v2`` in previous steps without ever specifying where xblock-drag-and-drop-v2 should be mounted.

Now, you may have an edx-platform package that does not use the supported directory naming convention. In that case, you have two options. Firstly, you could rename your package's directory so that it matches the naming convention. For example::

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

This plugin is maintained by me, `Kyle McCormick (@kdmccormick) <https://github.com/kdmccormick>`_, as part of my job at `the Center for Reimagining Learning (tCRIL) <https://openedx.atlassian.net/wiki/spaces/COMM/pages/3241640370/tCRIL+Engineering+Team>`_. If you have feedback or need help with it, I am happy to hear from you. Just mention ``@kdmccormick`` on the `Open edX forums <https://discuss.openedx.org>`_ and I'll get back to you as soon as I can.

I've written a TEP (Tutor Enhancement Proposal) to incorporate these changes upstream. I am not planning on maintaining this plugin in the long term, because I would rather these features be part of Tutor itself.

