Documentatation generation
==========================

Goal
----

* The documentation should be very close to the Micropython documentation.

Decisions
---------

* Sphinx
* autodoc
* Support for: reStructuredText
* Support for: Markdown
* VSCode Extensions
* Manually push documentation to octoprobe.org
* Forward from octoprobe.readthedocs.io to octoprobe.org

Based on Flask documentation
----------------------------

Flask makes intense use of autodoc. Therefore I used Flask as a base.

* Documentatation: https://flask.palletsprojects.com/en/3.0.x/api/#application-object
* Requirements: https://github.com/pallets/flask/blob/main/requirements/docs.in
* Config: https://github.com/pallets/flask/blob/main/docs/conf.py
* Index: https://github.com/pallets/flask/blob/main/docs/index.rst

Evaluation of the theme
-----------------------

* See: `docs/conf.py` `html_theme = "sphinx_rtd_theme"`
* See: https://www.sphinx-doc.org/en/master/examples.html

Page width: The page width for all themes seems to be the same: The width is 100% of the window to some limit. Then there is a hard limit.


* Theme `classic`
  * ...

* Theme `alabaster`
  
  * `pip install -`

    **Positive**: no dependency
  * `html_sidebars` support unknown.
  
* Theme `sphinx_rtd_theme`
  
  * `pip install sphinx_rtd_theme`

    **Positive**: maintained by sphinx
  * Used by: https://docs.micropython.org

    **Positive**: known by the micropython community
  * `html_sidebars` is NOT supported!
  
    **Negative**

* Theme `sphinx13`
  * Used by: https://www.sphinx-doc.org/en/master/ https://github.com/sphinx-doc/sphinx/blob/master/doc/conf.py
  
  **Positive**: Sphinx documentation 'another builtin theme'
  * `inherit = "basic"`, https://github.com/sphinx-doc/sphinx/blob/master/doc/_themes/sphinx13/theme.toml#L2C1-L2C18

  **Need investigation**: Where does it come from?
  * `html_sidebars` support unknown.
  * **Positive**: Deep hierarchy helps to structure the documentation

* Theme `flask`
  
  * `pip install pallets-sphinx-themes`

    **Negative**: externally maintained
  * Used by: https://flask.palletsprojects.com

    **Negative**: May change, not widely used
  * `html_sidebars` support unknown.

* Theme `python_docs_theme`
  
  * `pip install python-docs-theme`

    **Negative**: externally maintained
  * Used by: https://docs.python.org
  
    **Positive**: Probably mature and stable
  * `html_sidebars` IS supported!
  
    **Positive**
