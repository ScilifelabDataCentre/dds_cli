Installation guide
####################

You can install ``dds-cli`` in two different ways: 

* From `PyPI <https://pypi.org/project/dds-cli/>`_. Independent on operating system (OS), we recommend this option. Note that this does not apply to Uppmax. 
* Via executables. These are located in the latest release on `GitHub <https://github.com/ScilifelabDataCentre/dds_cli/releases/latest>`_. 

.. note:: 
   
   The executables are only available for Ubuntu, MacOS and Windows.
   
   If you want to request an executable for another OS, please contact us at `delivery@scilifelab.se <delivery@scilifelab.se>`_. Start the subject line with "Feature Request".

The following sections describe the installation process on :ref:`MacOS / Linux<mac-linux>` and :ref:`Windows<windows>`, and how to load ``dds-cli`` on :ref:`Uppmax<uppmax>`. 
Note that the sections describing installation from PyPI are focused on the ``install`` command, and do not provide a guide on how to verify the package integrity with checksums. Instructions on how to do this can be found at the :ref:`bottom of this page<verify-integrity>`.

.. _mac-linux:

MacOS / Linux
==============

As mentioned above, you can install ``dds-cli`` from PyPI or via an executable. 

.. _pypi-unix:

Install from **PyPI**
-----------------------

1. To perform these steps you need to have Python version 3.7 or higher installed.

   * First check which Python version you have

      .. image:: ../img/python-version.svg 

      If this displays ``Python 2.7``, run ``python3 --version`` instead.

      .. image:: ../img/python3-version.svg

      If this does not return ``Python 3.7.x`` or higher, you will need to `install Python <https://www.python.org/downloads/>`_.
   
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
   

.. _exec-unix:

Install via the **executable**
-------------------------------

1. Download the executable from the GitHub release page:

   * Executable for Linux: `Download Linux Executable <https://github.com/ScilifelabDataCentre/dds_cli/releases/latest/download/dds_cli_ubuntu_x86_64>`_
   * Executable for MacOS: `Download MacOS Executable <https://github.com/ScilifelabDataCentre/dds_cli/releases/latest/download/dds_cli_macos_x86_64>`_
   
2. Open the terminal, go to the directory where the downloaded file is located, and make the file executable by running the following command:

   * On Linux: 

      .. code-block:: bash

         $ chmod +x dds-cli_ubuntu_x86_64   

   * On MacOS: 

      .. code-block:: bash

         $ chmod +x dds-cli_macos_x86_64   

3. Test that the ``dds-cli`` command works by running the following:
   
   .. code-block:: bash

      $ ./<name-of-executable-file> 

   **Example:** 
   
   .. image:: ../img/mac-executable-help.svg

   
   .. admonition:: Information to MacOS users 
      
      On MacOS, you may need to allow your Mac to trust the software. Please, refer to the following sources for more information: https://support.apple.com/en-us/HT202491 and https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unidentified-developer-mh40616/mac

4. When reading through the rest of the documentation and running the commands, replace ``dds`` with the path to the executable. For example:

   .. code-block:: bash
      
      $ ./dds_cli_macos_x86_64 auth login
      $ ./dds_cli_macos_x86_64 user info
      $ ./dds_cli_macos_x86_64 ls
      ...
   


.. _windows:

Windows
=======

.. _pypi-windows:

Install from **PyPI**
-----------------------

Detailed instructions on how install the DDS CLI on Windows `here <https://github.com/ScilifelabDataCentre/dds_cli/blob/dev/WINDOWS.md>`_.

.. _exec-windows:

Install via the **executable**
-------------------------------

1. Download the executable from the GitHub release page: `Download <https://github.com/ScilifelabDataCentre/dds_cli/releases/latest/download/dds_cli_win_x86_64.exe>`_
2. Open the Powershell

  a. Click on ``Start`` (Windows symbol in corner)
  b. Type "Powershell" or "Command Prompt" (**Powershell** recommended)
  c. Click on the Powershell or Command Prompt symbol
  
3. Open the file explorer and navigate to the location of the downloaded executable. 
4. Drag the executable into the Powershell/Command Prompt window and press enter. This should result in the help text being displayed. 
   
   .. note:: 
      
      You may need to change the permissions regarding executables and allow your laptop to trust the software.

5. When reading through the rest of the documentation and running the commands, replace ``dds`` with the path to the executable. If you press the up arrow you will see the previous command which will reveal the exact path on you computer. 


.. _uppmax:

Uppmax 
=======

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

   A detailed user guide for Rackham can be found here: https://www.uppmax.uu.se/support/user-guides/rackham-user-guide/

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

   * Bianca user guide: https://www.uppmax.uu.se/support/user-guides/bianca-user-guide/
   * Transit user guide: https://www.uppmax.uu.se/support/user-guides/transit-user-guide/


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