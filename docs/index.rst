.. Data Delivery System documentation master file, created by
   sphinx-quickstart on Mon Dec  6 10:33:02 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====================================================================
Welcome to the Data Delivery Systems' Documentation / Test Protocol!
=====================================================================

.. note:: 

   During testing on 2022-02-28 to 2022-03-07, this will work as **both documentation and as a test protocol**. The goal is to give you ideas on what aspects of the system to try out, but please also test anything else you can think of (e.g. if you feel we have missed something). Also, please make note of whether the documentation of the system has any deficiencies such as unclear, misleading or incomplete instructions. 

.. warning::
   
   **Please do not use any sensitive data during this testing phase.** Since the last testing period we have implemented a key management system for the storage of all required keys (e.g. encryption keys) and your data should be secure, however there may be bugs and/or issues which we need to solve before DDS is put into production. 

The Data Delivery System (DDS) consists of a command line interface (CLI) and a very minimal web interface. The web interface will be improved on as soon as possible, but we have decided that having a working CLI and its corresponding API is highest on the priority list. 

How will I get my user account?
===============================
The testing will begin with you getting an invite via email. The email will be from `dsw@scilifelab.se` during the testing (note that any emails sent to this address regarding the DDS *will not be responded to*). If you do not get an email, please have a look in the junk/spam folder. If it's not there either, please contact Ina (*email:* ina.oden.osterbo@scilifelab.uu.se, *slack:* Ina Odén Österbo) and we will look into it. 

Once you get the invitation email, follow the link in the email and register your account. After this, you should have access to the system and can begin testing the different features. To be able to test the CLI (which contains most of the functionality) please follow the installation guide :ref:`below<how-to-use>`.

.. warning::
   Forgetting passwords in the DDS means that you will lose access to all project data. We highly recommend that you use a password management system such as `LastPass <https://www.lastpass.com/>`_ or similar.

   When resetting a password you can, of course, regain access to the projects you lost access to. This procedure is explained :ref:`here<web>`.

Your account will be either a *Unit Admin*, *Unit Personnel* or a *Researcher* account. These are called the different roles which define the commands and actions you are allowed to perform in the DDS, including some administrative permissions. The roles are defined `on this board <https://app.diagrams.net/?page-id=iAQ0dwp1xBzZl6jLjueX&hide-pages=1#G1ophR0vtGByHxPG90mzjAPXgMTCjVcN_Z>`_. 


.. _how-to-use:

How to use the DDS CLI
======================

Installation
------------

Uppmax
~~~~~~~
*Uppmax instructions coming are in progress* 

PyPi - MacOS / Linux 
~~~~~~~~~~~~~~~~~~~~~
1. To perform these steps you need to have Python version 3.8 or higher installed. It's possible that it could work with other versions, but this cannot be guaranteed. 

   * To install Python, please first run
      
      .. code-block::

         python --version

      It's possible that this shows ``Python 2.7``, in which case you should run 

      .. code-block::

         python3 --version

      If this does not return ``Python 3.8.x`` or higher, you will need to `install Python <https://www.python.org/downloads/>`_.
      
2. To install the DDS CLI, open the terminal and run

   .. code-block:: bash

      $ pip install dds-cli

3. Once the installation has finished, test that everything is working correctly:

   .. code-block:: bash

      $ dds --help

   This should display a logo, version information and a short usage message. If there are no errors when running this command, the test has succeeded and you should be able to move on to :ref:`Running the command<Running the command>`.


Windows
~~~~~~~~~~~~~~~~~~~~~
We are working on creating an executable which will perform all required installations. However, for now, we have made detailed instructions for how you can install the DDS CLI on Windows. The instructions can be found :ref:`here<windows>`. 
*Windows instructions are in progress.*

-------

.. _Running the command:

Running the command
---------------------

The main command ``dds`` has some options and possible customisations. A detailed list of these can be found :ref:`here<dds-main>`.

Some commands should not be possible to successfully run from a Researcher account. The affected commands are marked with asterisks (\*\*\*). However, we ask you to try these commands anyway and report back to us if anything unexpected occurs. 

The five group commands
~~~~~~~~~~~~~~~~~~~~~~~~

The DDS CLI has the following group commands: :ref:`auth<auth-info>`, :ref:`user<user-info>`, :ref:`project<project-info>`, :ref:`data<data-info>` and :ref:`ls<ls-info>`.

.. _auth-info:

:ref:`dds auth<dds-auth>`
""""""""""""""""""""""""""
``dds auth`` and its subcommands are used for creating and managing sessions. This will enable you to use the CLI without specifying your user credentials for a certain amount of time, currently 48 hours. 

See the test protocol and the command documentation :ref:`here<dds-auth>`.

.. _user-info:

:ref:`dds user<dds-user>`
""""""""""""""""""""""""""
You can use the ``add user`` group command to manage your own and (if you have administrative permissions) other user accounts. 

See the test protocol and the command documentation :ref:`here<dds-user>`.

.. _project-info:

:ref:`dds project<dds-project>`
""""""""""""""""""""""""""""""""
The ``dds project`` command is for creating and managing projects. The majority of the functionalities regarding project management is only available to *Unit Admin* and *Unit Personnel* accounts.

See the test protocol and the command documentation :ref:`here<dds-project>`.

.. _data-info:

:ref:`dds data<dds-data>`
""""""""""""""""""""""""""
The ``dds data`` group command is used for uploading, downloading, listing and deleting data. Only **Unit Admin** and **Unit Personnel** accounts can upload and delete data. All account types can list and download. 

See the test protocol and the command documentation :ref:`here<dds-data>`.

.. _ls-info:

:ref:`dds ls<dds-ls>`
""""""""""""""""""""""
The ``dds ls`` group command can be used for listing both projects and project contents. Calling the ``dds ls`` command should produce the same output as ``dds project ls``, and calling ``dds ls --project`` should result in the same output as when calling ``dds data ls``. 

See the test protocol and the command documentation :ref:`here<dds-ls>`.

How to test the web interface
==============================
The DDS web interface can be found at https://delivery.scilifelab.se/. There will only be a log in page and the possibility of requesting a password change. A guide on how to test out the existing web can be found :ref:`here<web>`.

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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
