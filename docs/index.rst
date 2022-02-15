.. Data Delivery System documentation master file, created by
   sphinx-quickstart on Mon Dec  6 10:33:02 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====================================================================
Welcome to the Data Delivery System's documentation / Test Protocol!
=====================================================================

.. note:: During testing on 2022-02-28 to 2022-03-07, this will also work as a test protocol. The goal is to give you ideas on what aspects of the system to try out, but if you feel that we have missed something, please test it and let us know what works and what doesn't. 

The Data Delivery System (DDS) consists of a command line interface (CLI) and a very minimal web interface. The web interface will be improved on asap, but we have decided that having a working CLI is highest on the priority list. 

To go to the DDS web interface, go to https://dds.dckube.se/. There will only be a log in page and the possibility of requesting a password change. (ADD LINK TO HTML -- STEPS TO TRY OUT IN THE WEB)

How to use the DDS CLI
======================

Installation
------------
Information about installing here
* pip
* executable at some point
* windows? should work the same way

Main command and options
------------------------
The main command `dds` has some options and possible customizations. A detailed list of these can be found :ref:`here<dds-main>`.

The five major commands
-----------------------

The DDS CLI has the following major commands: :ref:`auth<auth-info>`, :ref:`user<user-info>`, :ref:`project<project-info>`, :ref:`data<data-info>` and :ref:`ls<ls-info>`.

.. _auth-info:

`dds auth`
~~~~~~~~~~
some auth info here + link to docs

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
