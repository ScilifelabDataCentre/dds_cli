.. _installation:

Installation guide
##################

These instructions describe how to install ``dds-cli``. If you wish to install it on your own laptop or desktop machine, go to :ref:`Install on my machine<my_machine>`. If you instead want to install it on one of the available HPC facilities, e.g. UPPMAX, go to :ref:`Install on an HPC facility<hpc>`.

.. _my_machine:

Install on my machine
=====================

You can install ``dds-cli`` on your own machine in two different ways - installing manually via `PyPI <https://pypi.org/project/dds-cli/>`_ (recommended), or installing a pre-built executable.

.. note::

   The executables are only available for Ubuntu, MacOS and Windows.

   If you want to request an executable for another OS, please contact us at `delivery@scilifelab.se <delivery@scilifelab.se>`_. Start the subject line with "Feature Request".

The following links will take you to detailed instructions depending on your machine's operating system.
Note that the sections describing installation from PyPI are focused on the ``install`` command, and do not provide a guide on how to verify the package integrity with checksums. Instructions on how to do this can be found at the :ref:`bottom of this page<verify-integrity>`.

MacOS/Linux
-----------

Install manually via PYPI: :ref:`MacOS / Linux via PyPI <installation_mac_linux_pypi>`

Install executable: :ref:`MacOS / Linux executable <installation_mac_linux_exec>`

Windows
-------

Install manually via PYPI: :ref:`Windows via PyPI <installation_windows_pypi>`

Install executable: :ref:`Windows executable <installation_windows_exec>`

.. _hpc:

Install on an HPC facility
==========================

The ``dds-cli`` package is currently available to install on :ref:`UPPMAX/Rackham<rackham>`, :ref:`UPPMAX/Bianca<bianca>` and :ref:`Dardel<dardel>`.
For instructions on how to verify the package integrity with checksums if needed, see :ref:`verify package integrity<verify-integrity>`.

.. _uppmax:

Uppmax 
=======

.. note:: 

   This information may be outdated, as both Rackham and Bianca are being replaced. See `here <https://www.uu.se/en/centre/uppmax>` for more information.

The ``dds-cli`` package is a global module on Uppmax; No installation required. However, there are a few steps you need to perform prior to using it. These steps differ between Rackham and Bianca. 

.. note:: 

   When there is a new version of ``dds-cli``, Uppmax upgrades the version automatically the following day.

.. _rackham:

Rackham
--------

.. warning:: Do not deliver sensitive data to Rackham.

1. SSH into Rackham

   .. code-block:: 
      
      ssh -AX <username>@rackham.uppmax.uu.se

2. Load the ``bioinfo-tools`` module and ``dds-cli``

   .. code-block:: 

      ml bioinfo-tools dds-cli

3. Run ``dds --help``. The output should look like this:

   .. image:: ../img/dds-help-2.svg

.. admonition:: Rackham user guide

   A detailed user guide for Rackham can be found here: https://docs.uppmax.uu.se/cluster_guides/rackham/

.. _bianca: 

Bianca
-------

.. admonition:: Terminology in this section

   * **SENS project** / ``<SENS-project>``: The active SNIC SENS research project on the Bianca cluster at Uppmax. Not a DDS delivery project.
   * **DDS project** / ``<DDS-project>``: The active DDS delivery project you want to upload data to / download data from or manage. 

.. admonition:: Important

   * For downloading data to a SENS project on Bianca, you need to connect to a server called Transit, and not to your SENS project cluster.
   * Mount the correct SENS project on transit
   * You need to have enough space on the nobackup storage allocation in the corresponding SENS project. If the data you are trying to download is larger than the allocated space, the download will fail.
   * If your data is larger than a few hundreds of GB: start the download in a screen/tmux session


1. SSH into transit
   
   .. code-block:: bash

      $ ssh -A <username>@transit.uppmax.uu.se

   You will get into the home directory. 

   .. danger:: 

      Any files that are created here are not persistent; If you download data from DDS to this directory, your data will be deleted as soon as you exit the session.

2.  Mount your specific **SENS project** directory on transit
   
   .. code-block:: bash

      <username>@transit:~$ mount_wharf <SENS-project>

3.  Download the data

   .. danger:: 

      You **must use** the ``--destination`` option. If you do not, the data will end up in your home directory and will be deleted when your ssh session ends.

   Either specify a file or directory with ``--source``, or download the full project contents with ``--get-all``.

   **Examples:**
   
   * Download everything in DDS project:

      .. code-block:: bash

         $ dds data get --project <DDS-project> --get-all --destination <SENS-project>/<directory>/

   * Download one or more files or directories:

      .. code-block:: bash

         $ dds data get --project <DDS-project> --source <file or directory in DDS project> --destination <SENS-project>/<directory>/

   .. note:: 
      
      ``<directory>`` should be a non-existent directory where you would like your data to be located after download.

   The downloaded data ends up in a non-backed up storage on Bianca.

.. admonition:: Bianca- and Transit user guides

   * Bianca user guide: https://docs.uppmax.uu.se/cluster_guides/bianca/
   * Transit user guide: https://docs.uppmax.uu.se/cluster_guides/transfer_transit/

.. _dardel:

Dardel
=======

The ``dds-cli`` package is a global module on Dardel; No installation required. However, there are a few steps you need to perform prior to using it. 

1. First, you need to set up an account for accessing PDC's cluster Dardel. Their guide on how to do this can be found at https://support.pdc.kth.se/doc/basics/quickstart/.
2. SSH into Dardel's dedicated transfer node ``dardel-ftn01.pdc.kth.se`` (see https://support.pdc.kth.se/doc/data_management/file_transfer/) by running

   .. code-block:: bash

      $ ssh <your_dardel_username>@dardel-ftn01.pdc.kth.se
3. Load the ``dds-cli`` module by running

   .. code-block:: bash

      $ module load dds-cli
4. Check the ``dds-cli`` version by running

   .. code-block:: bash

      $ dds --version

   The output should be the following:

   .. image:: ../img/dds-version.svg
5. Run the ``dds data get ...`` command directly on that node, i.e. do **NOT** submit data-transfer jobs to the queueing system.


.. _verify-integrity: 

Verify the package integrity prior to installing it
====================================================

This installation guide is for those that want to verify that the ``dds-cli`` package published on PyPI is identical to the one you install locally, thereby catching potential (albeit unlikely) corruptions in the package prior to running the installation. Note that the hashes used to verify this are generated by PyPI itself, not by the Data Centre. 

1. Open the terminal
2. Download the ``dds-cli`` package by running

   .. code-block:: bash
      
      # "--dest dds-downloaded" tells pip to put the downloaded files in the directory "dds-downloaded"
      pip download dds-cli --dest dds-downloaded

3. Generate hash for the dds-cli file by running

   .. code-block:: bash

      # <VERSION> should be replaced by the version you have downloaded from PyPI. When in doubt, simply type dds-downloaded/dds_cli and press tab; The path to the file will be filled in automatically.
      pip hash dds-downloaded/dds_cli-<VERSION>-py3-none-any.whl
      # Example output:
      # dds_cli-<VERSION>-py3-none-any.whl:
      # --hash=sha256:8ba6495b73d759e96c35652273cf4e4158acba02f1cf64f012cc67cf2e346cae

4. Open a browser and go to the PyPI `"Download files" page <https://pypi.org/project/dds-cli/#files>`_

   1. In the "Built Distribution" section, click "view hashes"
   2. Copy the *Hash digest* for the SHA256 *Algorithm*

5. In the terminal, verify that the copied hash (step 4) matches the generated hash (step 3) by running

   .. code-block:: bash

      if [ "<correct hash from step 4>" = "<generated hash from step 3>" ]; then echo "Package integrity verified"; else echo "Package compromised!"; fi
   
   If this prints out "Package integrity verified", continue to step 6. If it does not, the downloaded ``dds-cli`` package is compromised and you should not perform step 6. Delete the downloaded directory ``dds-downloaded`` and start from step 1 again.

6. Install the ``dds-cli`` tool by running

   .. code-block:: bash

      pip install dds-downloaded/dds_cli-<VERSION>-py3-none-any.whl

7. Once the installation has finished, test that the CLI has been installed correctly by verifying the version:

   .. code-block:: bash

      $ dds --version

   The output should be the following:

   .. image:: ../img/dds-version.svg
