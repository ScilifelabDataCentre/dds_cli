:orphan:

.. _installation_mac_linux_pypi:

MacOS / Linux via PyPI
======================

1. To perform these steps you need to have Python version 3.10 or higher installed.

   * First check which Python version you have

      .. image:: ../img/python-version.svg

      If this displays ``Python 2.7``, run ``python3 --version`` instead.

      .. image:: ../img/python3-version.svg

      If this does not return ``Python 3.10.x`` or higher, you will need to `install Python <https://www.python.org/downloads/>`_.

   .. warning::

      Make sure you have the latest version of **pip**.

         .. code-block::

            python3 -m pip install --upgrade pip

         .. image:: ../img/pip-upgrade.svg

2. The DDS CLI is available on `PyPI <https://pypi.org/project/dds-cli/>`_. To install the DDS CLI, run this command in the terminal:

   .. code-block:: bash

      $ pip install --upgrade dds-cli

3. Once the installation has finished, test that the CLI has been installed correctly by verifying the version:

   .. code-block:: bash

      $ dds --version

   The output should be the following:

   .. image:: ../img/dds-version.svg
