.. Data Delivery System documentation master file, created by
   sphinx-quickstart on Mon Dec  6 10:33:02 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====================================================================
Welcome to the Data Delivery Systems' Documentation / Test Protocol!
=====================================================================

.. note:: During testing on 2022-02-28 to 2022-03-07, this will also work as a test protocol. The goal is to give you ideas on what aspects of the system to try out, but if you feel that we have missed something, please test it and let us know what works and what doesn't. 

The Data Delivery System (DDS) consists of a command line interface (CLI) and a very minimal web interface. The web interface will be improved on asap, but we have decided that having a working CLI is highest on the priority list. 

To go to the DDS web interface, go to https://delivery.scilifelab.se/. There will only be a log in page and the possibility of requesting a password change. A guide on how to test out the existing web can be found :ref:`here<web>`.


How to use the DDS CLI
======================

Installation
------------

PyPi - MacOS / Linux 
~~~~~~~~~~~~~~~~~~~~~
1. To perform these steps you need to have Pip and Python (the DDS requires Python version 3.7 or higher) installed. These are generally installed by default on Unix systems. If they are not, please install those first.
   * Install Python: 
   * Install Pip: 
2. To install the CLI, open the terminal and run

   .. code-block:: bash

      $ pip install dds-cli
3. Once the installation has finished, test that everything is working correctly:

   .. code-block:: bash

      $ dds --help

   This should display something like this:

   .. code-block:: bash

           ︵ 
       ︵ (  )   ︵ 
      (  ) ) (  (  )   SciLifeLab Data Delivery System 
       ︶  (  ) ) (    https://www.scilifelab.se/data 
            ︶ (  )    Version 1.5.9 
                ︶

                                                                                                         
      Usage: dds [OPTIONS] COMMAND [ARGS]...                                                              
                                                                                                         
      SciLifeLab Data Delivery System (DDS) command line interface.                                       
      Access token is saved in a .dds_cli_token file in the home directory. 

Executable - Windows
~~~~~~~~~~~~~~~~~~~~~
WE NEED TO FIX AN EXECUTABLE

Main command and options
------------------------
The main command `dds` has some options and possible customizations. A detailed list of these can be found :ref:`here<dds-main>`.

The five major commands
-----------------------

The DDS CLI has the following major commands: :ref:`auth<auth-info>`, :ref:`user<user-info>`, :ref:`project<project-info>`, :ref:`data<data-info>` and :ref:`ls<ls-info>`.

.. _auth-info:

`dds auth`
~~~~~~~~~~
`dds auth` and its subcommands is used for creating and managing sessions. This will enable you to run multiple commands within a certain amount of time (current 48 hours) without specifying your user credentials. 

If you do not authenticate yourself and start a new session, you will need to provide your DDS username when running the other commands. If you do not provide the username as an option, you will be prompted to fill it in.

See the subcommands and documentation :ref:`here<dds-auth>`.

.. _user-info:

`dds user`
~~~~~~~~~~
some user info here + link to docs

See the subcommands and documentation :ref:`here<dds-user>`.

.. _project-info:

`dds project`
~~~~~~~~~~~~~
some project info here + link to docs

See the subcommands and documentation :ref:`here<dds-project>`.

.. _data-info:

`dds data`
~~~~~~~~~~
some data info here + link to docs

See the subcommands and documentation :ref:`here<dds-data>`.

.. _ls-info:

`dds ls`
~~~~~~~~
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
