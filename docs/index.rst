.. Data Delivery System documentation master file, created by
   sphinx-quickstart on Mon Dec  6 10:33:02 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====================================================================
Welcome to the Data Delivery Systems' Documentation / Test Protocol!
=====================================================================

.. note:: 

   During testing on 2022-02-28 to 2022-03-07, this will also work as a test protocol. The goal is to give you ideas on what aspects of the system to try out, but please also test anything else you can think of (e.g. if you feel we have missed something). Also, please make note of whether the documentation of the system has any deficiencies such as unclear, misleading or incomplete instructions. 

.. warning::
   
   **Please do not use any sensitive data during this testing phase.** The key management has been implemented and your data should be secure, however there may be bugs and/or issues which we need to solve before DDS is put in production. 

The Data Delivery System (DDS) consists of a command line interface (CLI) and a very minimal web interface. The web interface will be improved on as soon as possible, but we have decided that having a working CLI and its corresponding API is highest on the priority list. 

The DDS web interface can be found at https://delivery.scilifelab.se/. There will only be a log in page and the possibility of requesting a password change. A guide on how to test out the existing web can be found :ref:`here<web>`.

How will I get my user account?
===============================
The testing will begin with you getting an invite via email. The email will be from `dsw@scilifelab.se` during the testing. If you do not get an email, please have a look in the junk folder. If it's not there either, please contact Ina (*email:* ina.oden.osterbo@scilifelab.uu.se, *slack:* Ina Odén Österbo) and we will look into it. 

Once you get the invitation email, follow the link in the email and register your account. After this, you should have access to the system and can begin testing the different features. To be able to test the CLI (which contains most of the functionality) please follow the installation guide :ref:`below<how-to-use>`.

.. warning::
   Forgetting passwords in the DDS means that you will lose access to all project data. We highly recommend that you use a password management system such as `LastPass <https://www.lastpass.com/>`_ or similar.

   When resetting a password you can, of course, regain access to the projects you lost access to. This procedure is explained <here>.

Your account will be either a *Unit Admin*, *Unit Personnel* or a *Researcher* account. These are called the different roles which define the commands and actions you are allowed to perform in the DDS, including some administrative permissions. The roles are defined <here>. 


.. _how-to-use:

How to use the DDS CLI
======================

Installation
------------

PyPi - MacOS / Linux 
~~~~~~~~~~~~~~~~~~~~~
#. To perform these steps you need to have Python version 3.8 or higher installed. It's possible that it works with other versions as well, but we cannot guarantee it. 

   * To install Python, please first run
      
      .. code-block::

         python --version

      It's possible that this shows `Python 2.7`, in which case you should run 

      .. code-block::

         python3 --version

      If this does not return `Python 3.8.x` or higher, you will need to `install Python <https://www.python.org/downloads/>`_.
      
#. To install the DDS CLI, open the terminal and run

   .. code-block:: bash

      $ pip install dds-cli

#. Once the installation has finished, test that everything is working correctly:

   .. code-block:: bash

      $ dds --help

   This should display a logo, version information and a short usage message. 


Executable - Windows
~~~~~~~~~~~~~~~~~~~~~

WE NEED TO FIX AN EXECUTABLE OR COPY/EDIT LAST YEARS WINDOWS INSTRUCTIONS

-------

Main command and options
------------------------

The main command `dds` has some options and possible customizations. A detailed list of these can be found :ref:`here<dds-main>`.

The five group commands
-----------------------

The DDS CLI has the following major commands: :ref:`auth<auth-info>`, :ref:`user<user-info>`, :ref:`project<project-info>`, :ref:`data<data-info>` and :ref:`ls<ls-info>`.

.. _auth-info:

:ref:`dds auth<dds-auth>`
~~~~~~~~~~~~~~~~~~~~~~~~~~

`dds auth` and its subcommands are used for creating and managing sessions. This will enable you to run multiple commands within a certain amount of time (currently 48 hours) without specifying your user credentials. 

See the subcommands and documentation :ref:`here<dds-auth>`.

.. _user-info:

:ref:`dds user<dds-user>`
~~~~~~~~~~~~~~~~~~~~~~~~~~
You can use the `add user` group command to manage your own and (if you have administrative permissions) other user accounts. 

See the subcommands and documentation :ref:`here<dds-user>`.

.. _project-info:

:ref:`dds project<dds-project>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
some project info here + link to docs

See the subcommands and documentation :ref:`here<dds-project>`.

.. _data-info:

:ref:`dds data<dds-data>`
~~~~~~~~~~~~~~~~~~~~~~~~~~
some data info here + link to docs

See the subcommands and documentation :ref:`here<dds-data>`.

.. _ls-info:

:ref:`dds ls<dds-ls>`
~~~~~~~~~~~~~~~~~~~~~~
some listing info here + link to docs

See the subcommands and documentation :ref:`here<dds-ls>`.

Links to documentation
=======================

.. toctree::

   web
   main
   auth
   user
   project
   data
   ls


.. toctree::
   :maxdepth: 2
   :caption: DDS CLI Modules :

   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



1. = 
2. - 
3. ~
4. "
5. '
6. ^
7. #
8. *
9. $ 
10. `
