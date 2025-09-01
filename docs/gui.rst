.. _gui:

========
The DDS GUI
========

.. contents::
   :local:


.. _gui-installation:

GUI Installation
=================

The DDS GUI is available in the following ways:

- From the CLI
- From the binaries downloads

Installation from the CLI
-------------------------

Install the DDS CLI as described in :ref:`<installation>`.

Install binaries
----------------

Download the binaries from the `GitHub releases page <https://github.com/ScilifelabDataCentre/dds_cli/releases/latest>`_.

Start the GUI from the CLI
--------------------------

Run the ``dds gui`` command.

.. code-block:: bash
   :caption: Start the GUI from the CLI
   
   dds gui

Start the GUI from the binaries
------------------------------

After downloading the binaries, either run the ``dds-gui`` binary or double click the file.

.. _authentication:

Authentication
==============

The GUI requires an authenticated session to access projects and their contents. 

Login
-----

.. _login:

To login, click the "Authenticate" button in the bottom left corner of the GUI. A pop up window will appear. 
Enter your username and password in the pop up window and click the "Login" button. A two-factor authentication code will be sent to your chosen two-factor authentication method.
Enter the two-factor authentication code and click the "Authenticate" button.

If the authentication was unsuccessful, you will get an error message displayed in the bottom right corner of the GUI. 

.. TODO:: Add image of the authentication process 

Re-authentication
----------------

The authentication session is valid for 7 days. To reset the session during the 7 days, click the "Re-authenticate" 
button in the bottom left corner of the GUI. The re-authentication process is the same as the login process :ref:`<login>`.

.. TODO:: Add image of the re-authentication process

Logout
------

To logout, click the "Logout" button in the bottom left corner of the GUI. You need to confirm the logout by clicking the logout button in the pop-up window.
If you do not wish to logout, you can either:

- Click the "Cancel" button in the pop-up window
- Click the "Close" button in the bottom left of the pop-up window
- Press the "Escape" key on your keyboard

.. TODO:: Add images of the logout process

.. _important-information:

Important Information
=====================

Important information about the DDS are displayed in the middle left of the GUI. To view all content you may need to scroll down in the container. 

.. TODO:: Add image of the important information

.. _project-list:

Projects
============

Project Select
--------------

The project list is displayed in the top left of the GUI. 
In the dropdown menu you can select the project you want to view. You need to select a project to view its contents.
When selecting a project, it might take a few seconds to load the project contents. There is a loading indicator displayed in the project content container.

.. TODO:: Add image of the project select

Project content
---------------

The project content is displayed in the middle of the GUI. The project content are always displayed in a tree structure.
The tree structure is collapsed by default, to expand the tree structure, click on the folder you want to expand. 
If there is a lot of content, you may need to scroll to view all content. The selected file/folder is highlighted in the tree structure and 
displayed in the bottom right border of the container. 

.. TODO:: Add image of the project content

Project information
-------------------

The project information is displayed in the top right of the GUI. The project information is displayed in a table format.
The project information is updated when you select a new project.

.. TODO:: Add image of the project information

Project Actions
===============

.. TODO:: Add information on the project actions












