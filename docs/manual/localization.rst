.. _localizaation:

Localization / Multi-lingual Support
------------------------------------

pywb supports configuring different language locales and loading different language translations, and dynamically switching languages.

pywb can extract all text from templates and generate CSV files for translation and convert them back into a binary format used for localization/internationalization.

(pywb uses the `Babel library <http://babel.pocoo.org/en/latest/>`_  which extends the `standard Python i18n system <https://docs.python.org/3/library/gettext.html>`_)

Locales to use are configured in the ``config.yaml``.

The command-line ``wb-manager`` utility provides a way to manage locales for translation, including generating extracted text, and to update translated text.

Adding a Locale and Extracting Text
===================================

To add a new locale for translation and automatically extract all text that needs to be translated, run::

  wb-manager i18n extract <loc>

The ``<loc>`` can be one or more supported two-letter locales or CLDR language codes. To list available codes, you can run ``pybabel --list-locales``.

Localization data is placed in the ``i18n`` directory, and translatable strings can be found in ``i18n/translations/<locale>/LC_MESSAGES/messages.csv``

Each CSV file looks as follows, listing each source string and an empty string for the translated version::

  "location","source","target"
  "pywb/templates/banner.html:6","Live on",""
  "pywb/templates/banner.html:8","Calendar icon",""
  "pywb/templates/banner.html:9 pywb/templates/query.html:45","View All Captures",""
  "pywb/templates/banner.html:10 pywb/templates/header.html:4","Language:",""
  "pywb/templates/banner.html:11","Loading...",""
  ...


This CSV can then be passed to translators to translate the text.

(The extraction parameters are configured to load data from ``pywb/templates/*.html`` in ``babel.ini``)


For example, the following will generate translation strings for ``es`` and ``pt`` locales::

   wb-manager i18n extract es pt


The translatable text can then be found in ``i18n/translations/es/LC_MESSAGES/messages.csv`` and ``i18n/translations/pt/LC_MESSAGES/messages.csv``.


The CSV files should be updated with a translation for each string in the ``target`` column.

The extract command adds any new strings without overwriting existing translations, so after running the update command to compile translated strings (described below), it is safe to run the extract command again.


Updating Locale Catalog
=======================

Once the text has been translated, and the CSV files updated, simply run::

  wb-manager i18n update <loc>

This will parse the CSVs and compile the translated string tables for use with pywb.


Specifying locales in pywb
==========================

To enable the locales in pywb, one or more locales can be added to the ``locales`` key in ``config.yaml``, ex::

  locales:
     - en
     - es

Single Language Default Locale
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pywb can be configured with a default, single-language locale, by setting the ``default_locale`` property in ``config.yaml``::


  default_locale: es
  locales:
     - es


With this configuration, pywb will automatically use the ``es`` locale for all text strings in pywb pages.

pywb will also set the ``<html lang="es">`` so that the browser will recognize the correct locale.


Mutli-language Translations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If more than one locale is specified, pywb will automatically show a language switching UI at the top of collection and search pages, with an option
for each locale listed. To include English as an option, it should also be added as a locale (and no strings translated). For example::

  locales:
     - en
     - es
     - pt

will configure pywb to show a language switch option on all pages.


Localized Collection Paths
==========================

When localization is enabled, pywb supports the locale prefix for accessing each collection with a localized language:
If pywb has a collection ``my-web-archive``, then:

* ``/my-web-archive/`` - loads UI with default language (set via ``default_locale``)
* ``/en/my-web-archive/`` - loads UI with ``en`` locale
* ``/es/my-web-archive/`` - loads UI with ``es`` locale
* ``/pt/my-web-archive/`` - loads UI with ``pt`` locale

The language switch options work by changing the locale prefix for the same page.

Listing and Removing Locales
============================

To list the locales that have previously been added, you can also run ``wb-manager i18n list``.

To disable a locale from being used in pywb, simply remove it from the ``locales`` key in ``config.yaml``.

To remove data for a locale permanently, you can run: ``wb-manager i18n remove <loc>``. This will remove the locale directory on disk.

To remove all localization data, you can manually delete the ``i18n`` directory.


UI Templates: Adding Localizable Text
=====================================

Text that can be translated, localizable text, can be marked as such directly in the UI templates:

1. By wrapping the text in ``{% trans %}``/``{% endtrans %}`` tags. For example::

   {% trans %}Collection {{ coll }} Search Page{% endtrans %}

2. Short-hand by calling a special ``_()`` function, which can be used in attributes or more dynamically. For example::

   ... title="{{ _('Enter a URL to search for') }}">


These methods can be used in all UI templates and are supported by the Jinja2 templating system.

See :ref:`ui-customizations` for a list of all available UI templates.

