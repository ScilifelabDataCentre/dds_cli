.. _mac-linux:

MacOS / Linux
==============

You can either install the DDS CLI using pip (https://pypi.org/project/dds-cli/) or with an executable.

PyPi
-----

1. To perform these steps you need to have Python version 3.7 or higher installed. It's possible that it could work with other versions, but this cannot be guaranteed. 

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

3. Once the installation has finished, test that everything is working correctly:

   .. code-block:: bash

      $ dds --help

   This should display a logo, version information and a short usage message. If there are no errors when running this command, the test has succeeded and you should be able to move on to use the CLI.

Executable
----------
<instructions here>


---

.. _windows:

Windows
=======
* As with MacOS and Linux, you can use PyPi or an executable to install the DDS CLI. We recommend the executable.
* Detailed instructions on how install the DDS CLI on Windows `here <https://github.com/ScilifelabDataCentre/dds_cli/blob/dev/WINDOWS.md>`_.

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
* Bianca 
   * ssh into transit: $ ssh -A <username>-<projid>@bianca.uppmax.uu.se
   * you get to home directory - any files that are created here are not persistent - if you download data from dds  here is will not persist beyond their ssh session!!!
   * Mount specific directory of a SENS project on transit: username@transit:~$ mount_wharf <sens_project>
   * Set mount point as destination in the dds get command: dds data get --destination <sens_project>/<destination>/ (!!!)
      * downloaded data ends up in a non-backed up storage on bianca 
   * TO BE AWARE OF:
      * Mount the correct SENS project on transit
      * The size of the data they need to download vs the nobackup storage allocation of the corresponding SENS project
      * start the download in a screen/tmux session for anything larger than a few hundreds of GB
   * Bianca user guide: https://www.uppmax.uu.se/support/user-guides/bianca-user-guide/
   * Transit user guide: https://www.uppmax.uu.se/support/user-guides/transit-user-guide/