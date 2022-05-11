Installation guide
####################

Independent on operating system (OS), we recommend installing the ``dds-cli`` from `PyPi <https://pypi.org/project/dds-cli/>`_. However, you can also install it via the executables, located in the latest release on `GitHub <https://github.com/ScilifelabDataCentre/dds_cli/releases/latest>`_.

.. _mac-linux:

MacOS / Linux
==============

You can either install the DDS CLI using pip (https://pypi.org/project/dds-cli/) or with an executable.

PyPi
-----

1. To perform these steps you need to have Python version 3.7 or higher installed.

   * To install Python, please first run
      
      .. code-block::

         python --version

      It's possible that this shows ``Python 2.7``, in which case you should run 

      .. code-block::

         python3 --version

      If this does not return ``Python 3.7.x`` or higher, you will need to `install Python <https://www.python.org/downloads/>`_.
   
   .. warning:: 
   
      Make sure you have the latest version of **pip**.

         .. code-block:: 

            python3 -m pip install --upgrade pip

2. The DDS CLI is available on `PyPi <https://pypi.org/project/dds-cli/>`_. To install the DDS CLI, open the terminal and run

   .. code-block:: bash

      $ pip install dds-cli

3. Once the installation has finished, test that the CLI has been installed correctly by verifying the version:

   .. code-block:: bash

      $ dds --version

   This should display something like this

   .. code-block:: bash
      
      Data Delivery System, version 1.0.0
   
   If the version does not say the same as what is displayed on PyPi, run the following command and try again.

   .. code-block:: bash

      $ pip install --upgrade dds-cli
   

Executable
----------

1. Download the executable from the GitHub release page: https://github.com/ScilifelabDataCentre/dds_cli/releases/latest/download/dds_cli_macos_x86_64
   If you have an M1 Mac, you need to download this one instead: https://github.com/ScilifelabDataCentre/dds_cli/releases/latest/download/dds_cli_macos_arm64
2. Open the terminal and go to the directory where the downloaded file is located
3. You should now be able to run the dds with the following command
   
   .. code-block:: bash

      $ ./<name-of-file> 

      Example:
      $ ./dds_cli_macos_x86_64

4. To specify options, follow the documentation instructions. The only difference should be that you may need to change the permissions regarding executables, allowing your laptop to trust the software and finally running the dds by specifying the executables name instead of ``dds``. 


---

.. _windows:

Windows
=======

PyPi
-----
Detailed instructions on how install the DDS CLI on Windows `here <https://github.com/ScilifelabDataCentre/dds_cli/blob/dev/WINDOWS.md>`_.

Executable
----------

1. Download the executable from the GitHub release page: https://github.com/ScilifelabDataCentre/dds_cli/releases/latest/download/dds_cli_win_x86_64.exe
2. Open the Powershell (Start -> Search "Powershell" -> Click) or terminal (Powershell recommended)
3. Drag the executable into the Powershell window and press enter. This should result in the help text being displayed.
4. To run the dds command, press the up arrow and use the options that you want, specified in this documentation. The only difference should be that you run the dds by specifying the executables name (/path) instead of ``dds``. You may need to change the permissions regarding executables and allow your laptop to trust the software.


---

.. _uppmax:

Uppmax 
=======

Rackham
--------
.. warning:: Do not deliver sensitive data to Rackham.

The DDS CLI will be made a global module at Uppmax and you will be able to load it after having ssh:ed into Rackham. Until it is a module though, you can install the CLI with PyPi as in the previous sections.

.. code-block:: bash

   $ pip install dds-cli 

A detailed user guide for Rackham can be found here: https://www.uppmax.uu.se/support/user-guides/rackham-user-guide/

Bianca
-------

.. admonition:: To be aware of

   * Mount the correct SENS project on transit
   * You need to have enough space on the nobackup storage allocation in the corresponding SENS project. If the data you are trying to download is larger than the allocated space, the download will fail.
   * If your data is larger than a few hundreds of GB: start the download in a screen/tmux session


1. ssh into transit
   
   .. code-block:: bash

      $ ssh -A <username>-<projid>@bianca.uppmax.uu.se

   You will get into the home directory. 

   .. danger:: 

      Any files that are created here are not persistent; If you download data from DDS to this directory, your data will be deleted as soon as you exit the session.

2.  Mount your specific SENS project directory on transit
   
   .. code-block:: bash

      username@transit:~$ mount_wharf <sens_project>

3.  Download the data with the DDS CLI

   .. danger:: 

      You **must use** the ``--destination`` option. If you do not, the data will end up in your home directory and will be deleted when your ssh session ends.

   .. code-block:: bash

      $ dds data get --destination <sens_project>/<destination>/

   The downloaded data ends up in a non-backed up storage on Bianca.

.. admonition:: Links

   * Bianca user guide: https://www.uppmax.uu.se/support/user-guides/bianca-user-guide/
   * Transit user guide: https://www.uppmax.uu.se/support/user-guides/transit-user-guide/