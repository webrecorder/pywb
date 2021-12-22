.. _new-vue-ui:


New Vue-based UI (Alpha)
========================

With 2.7.0, pywb introduces a new `Vue UI <https://vuejs.org/>`_ based system, which can be enabled to provide a more feature-rich representation of a web archive.

The UI consists of two parts, which can be enabled using the ``ui`` block in ``config.yaml``

.. code::  yaml

  ui:
    vue_calendar_ui: true
    vue_timeline_banner: true


Note: This UI is still in development and not all features are operational yet.
In particular, localization switching is not yet available in the alpha version.

Overview
--------

Calendar UI
^^^^^^^^^^^

The new calendar UI provides a histogram and a clickable calendar representation of a web archive.

The calendar is rendered in place of the standard URL query page.

.. image:: images/vue-cal.png
  :width: 600
  :alt: Calendar UI Screenshot


To enable this UI for URL query pages, set the ``ui.vue_calendar_ui`` property to true in the ``config.yaml``


Banner Replay UI
^^^^^^^^^^^^^^^^

The new banner histogram allows for zooming in on captures per year as well as per month.

Navigation preserves the different levels. The full calendar UI is also available as a dropdown by clicking the calendar icon.

The new banner should allow for faster navigation across multiple captures.

.. image:: images/vue-banner.png
  :width: 600
  :alt: Calendar UI Screenshot


To enable this UI for replay pages, set the ``ui.vue_timeline_banner`` property to true in the ``config.yaml``


Custom Logo
^^^^^^^^^^^

When using the custom banner, it is possible to configure a logo by setting ``ui.logo`` to a static file.

If omitted, the standard pywb logo will be used by default.


Updating the Vue UI
-------------------

The UI is contained within the ``pywb/vueui`` directory.

The Vue component sources can be found in ``pywb/vueui/src``.

Updating the UI requires ``node`` and ``yarn``.

To install and build, run:


.. code:: console

   cd pywb/vueui
   yarn install
   yarn build


This will generate the output to ``pywb/static/vue/vueui.js`` which is loaded from the default templates when the Vue UI rendering is enabled.

Additional styles for the banner are loaded from ``pywb/static/vue_banner.css``.
