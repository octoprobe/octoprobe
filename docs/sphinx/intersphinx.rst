Intersphinx
===========

palletsprojects.com
-------------------

This project is the paradigm for octoprobe.

* palletsprojects.com: Entry page with links to Flask, Jinja, Click

 * https://palletsprojects.com/projects/flask

  * Documentation: https://flask.palletsprojects.com/en/3.0.x/
  * Releases on PyPi: https://pypi.org/project/Flask/
  * Source on Github: https://github.com/pallets/flask

 * https://palletsprojects.com/projects/jinja

  * Documentation: https://jinja.palletsprojects.com/en/3.1.x/
  * Releases on PyPi: https://pypi.org/project/Jinja/
  * Source on Github: https://github.com/pallets/jinja

Drawback: requires sub-url: `flask.palletsprojects.com`, `jinja.palletsprojects.com`



octoprobe.org
-------------

* www.octoprobe.org: Entry page with links to Flask, Jinja, Click

 * https://docs.octoprobe.org/testbed_showcase
 * https://docs.octoprobe.org/octoprobe
 * https://docs.octoprobe.org/tentacle
 * https://docs.octoprobe.org/usbhubctl

Consideration

 * Positiv: Only `www.octoprobe.com` / `docs.octoprobe.com`. Both map to `www.octoprobe.com`.
 * Positiv: All projects use the same mapping / no top project.
 * Negativ: The entry page is handled seperately.

.. code-block:: bash

  python -m sphinx.ext.intersphinx http://octoprobe.org/octoprobe/objects.inv
  python -m sphinx.ext.intersphinx http://octoprobe.org/tentacle/objects.inv
  python -m sphinx.ext.intersphinx http://octoprobe.org/testbed_showcase/objects.inv
  python -m sphinx.ext.intersphinx http://octoprobe.org/usbhubctl/objects.inv

.. code-block:: rst

  Test: :external+octoprobe:doc:`Terms <design/terms>`
  :external+octoprobe:doc:`License <license>`

