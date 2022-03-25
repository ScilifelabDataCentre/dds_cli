.. Data Delivery System documentation master file, created by
   sphinx-quickstart on Mon Dec  6 10:33:02 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====================================================================
Welcome to the Data Delivery Systems' Documentation!
=====================================================================

The Data Delivery System (DDS, https://delivery.scilifelab.se/) consists of a command line interface (CLI) and a currently minimal web interface. The web interface will be improved on as soon as possible, but we have decided that having a working CLI and its corresponding API is highest on the priority list. 

How do I get my user account?
===============================
An invite from an existing user is required in order for you to get an account within the DDS. The email will be from `dsw@scilifelab.se`, we will notify you if and when this changes. Note that any emails sent to this address regarding the DDS *will not be responded to*. If you do not get an email, please have a look in the junk/spam folder. If your email adress has the `scilifelab.se` domain, keep in mind that your emails may take a while to deliver due to the KTH spam filters. If you do not receive an email, please contact Ina (*email:* ina.oden.osterbo@scilifelab.uu.se, *slack:* Ina Odén Österbo) and we will look into it. 

Once you get the invitation email, follow the link in the email and register your account. After this, you should have access to the system. To be able to use the CLI (which contains most of the functionality) please follow the installation guide :ref:`below<how-to-use>`.

.. warning::
   Forgetting passwords in the DDS means that you will lose access to all project data. We highly recommend that you use a password management system such as `LastPass <https://www.lastpass.com/>`_ or similar.

   When resetting a password you can, of course, regain access to the projects you lost access to. You will get information on how when you perform a password reset.

Your account will be either a *Unit Admin*, *Unit Personnel* or a *Researcher* account. These are called the different roles which define the commands and actions you are allowed to perform in the DDS, including some administrative permissions. The roles are defined `on this board <https://app.diagrams.net/?page-id=iAQ0dwp1xBzZl6jLjueX&hide-pages=1#G1ophR0vtGByHxPG90mzjAPXgMTCjVcN_Z>`_. 

.. _how-to-use:

How to use the DDS CLI
======================

Installation
------------

MacOS / Linux 
~~~~~~~~~~~~~~
You can either install the DDS CLI using pip (https://pypi.org/project/dds-cli/) or with an executable.

PyPi
"""""

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

   This should display a logo, version information and a short usage message. If there are no errors when running this command, the test has succeeded and you should be able to move on to :ref:`Running the command<Running the command>`.

Executable
""""""""""""
<instructions here>

Windows
~~~~~~~~~
As with MacOS and Linux, you can use PyPi or an executable to install the DDS CLI. We recommend the executable.

PyPi
""""""
Detailed instructions on how install the DDS CLI on Windows: https://github.com/ScilifelabDataCentre/dds_cli/blob/dev/WINDOWS.md

Executable
""""""""""""
<instructions here>


Uppmax
~~~~~~~

Rackham
"""""""""
.. warning:: Do not deliver sensitive data to Rackham.

The DDS CLI will be made a global module at Uppmax and you will be able to load it after having ssh:ed into Rackham. Until it is a module though, you can install the CLI with PyPi as in the previous sections.

.. code-block:: bash

   $ pip install dds-cli 

A detailed user guide for Rackham can be found here: https://www.uppmax.uu.se/support/user-guides/rackham-user-guide/

Bianca
""""""""
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



-------

.. _Running the command:

Running the command
---------------------

The main command ``dds`` has some options and possible customisations. A detailed list of these can be found :ref:`here<dds-main>`. The sub/group commands are ``dds auth``, ``dds user``, ``dds project``, ``dds data``, ``dds ls`` and ``dds unit``.

Some commands should not be possible to successfully run from a Researcher account. The affected commands are marked with asterisks (\*\*\*).

.. _auth-info:

:ref:`dds auth<dds-auth>`
~~~~~~~~~~~~~~~~~~~~~~~~~~
``dds auth`` and its subcommands are used for creating and managing sessions. This will enable you to use the CLI without specifying your user credentials for a certain amount of time, currently 7 days. 

.. admonition:: Accessible by
   
   All user roles.

See the command documentation :ref:`here<dds-auth>`.

.. _user-info:

:ref:`dds user<dds-user>`
~~~~~~~~~~~~~~~~~~~~~~~~~~
You can use the ``add user`` group command to manage your own and (if you have administrative permissions) other user accounts. 

.. admonition:: Accessible by
   
   All user roles. Some subcommands are limited to Unit Admins, Unit Personnel and in come cases Researchers marked as Project Owners for specific projects.

See the command documentation :ref:`here<dds-user>`.

.. _project-info:

:ref:`dds project<dds-project>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ``dds project`` command is for creating and managing projects. The majority of the functionalities regarding project management is only available to *Unit Admin* and *Unit Personnel* accounts.

.. admonition:: Accessible by
   
   Researchers can use the ``dds project ls``.
   Researchers marked as Project Owners in specific projects can also use ``dds project access grant/revoke``. 
   The rest of the subcommands are limited to Unit Admins and Unit Personnel.

See the command documentation :ref:`here<dds-project>`.

.. _data-info:

:ref:`dds data<dds-data>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ``dds data`` group command is used for uploading, downloading, listing and deleting data. Only **Unit Admin** and **Unit Personnel** accounts can upload and delete data. All account types can list and download. 

.. admonition:: Accessible by
   
   Researchers can use `dds data get`.
   The rest of the subcommands are limited to Unit Admins and Unit Personnel.

See the command documentation :ref:`here<dds-data>`.

.. _ls-info:

:ref:`dds ls<dds-ls>`
~~~~~~~~~~~~~~~~~~~~~~
The ``dds ls`` group command can be used for listing both projects and project contents. Calling the ``dds ls`` command should produce the same output as ``dds project ls``, and calling ``dds ls --project`` should result in the same output as when calling ``dds data ls``. 

.. admonition:: Accessible by
   
   All user roles.


See the command documentation :ref:`here<dds-ls>`.

.. _unit-info:

:ref:`dds unit<dds-unit>`
~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``dds unit`` group command can be used by Super Admins to list all units and their information. 

.. admonition:: Accessible by
   
   Super Admins only.

Command documentation and guide
================================

.. toctree::
   :maxdepth: 1

   main
   auth
   user
   project
   data
   ls
   unit

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
