Experiment Section 4
==========================================

SubSection A
-------------------

SubSubSection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SubSubSubSection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Paragraph
"""""""""""""""""""""""""""""""""""

SubSection B
-------------------

SubSubSection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SubSubSubSection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Paragraph
"""""""""""""""""""""""""""""""""""

.. note::

   Above summarizes the different titles.

   Rule: Every page with a section. No other sections on this page!


Replace titles
--------------

Search for title, in this case ``------------``.

.. code-block:: text

   ^-+$

And replace by

.. code-block:: text

   ~~~~~~~~~~~~~~~~~~~~~~~

Source code
-----------

See: https://github.com/pallets/flask/blob/main/docs/quickstart.rst

.. code-block:: python

   from flask import url_for

.. code-block:: text

   Blabla
   
   
.. sourcecode:: html+jinja

    <!doctype html>
    <title>Hello from Flask</title>
    {% if person %}
      <h1>Hello {{ person }}!</h1>
    {% else %}
      <h1>Hello, World!</h1>
    {% endif %}


Markup
------------------

Filename
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The file has to be stored on the filesystem as :file:`static/style.css`.

References external
--------------------

For a reference to HTML, CSS, and other web APIs, use the `MDN Web Docs`_.

.. _MDN Web Docs: https://developer.mozilla.org/


References internal
----------------------

.. _this-is-an-anchor:

This is an anchor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Link to above anchor. See :ref:`this-is-an-anchor`.



Python Documentation
------------------------

To render a template you can use the :func:`~flask.render_template`
