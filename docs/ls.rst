==============
`dds ls`
==============

.. admonition:: Section structure 
   
   This section begins with a description and step-by-step guide to how you could test this command. You can find the different commands and their options at the :ref:`bottom<dds-ls>` of the section. 

How to test the `dds ls` command functionality
----------------------------------------------------
.. note::

   When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there’s anything we need to improve on, including the documentation in this section.
   
   Commands which should only work for Unit Adminds and Unit Personnel are noted in the step it applies to with three asterisks (\*\*\*). Asterisks applied to a main item (e.g. 3.) also applies to the subitems (e.g. 3.1., 3.2. etc). If there is additional information about the different permissions, this is displayed in a parenthesis beside the asterisk. 

Steps
~~~~~~~

.. note::

   These sections/test steps assume you have already started a session with the :ref:`dds auth<dds-auth>` command.

1. Help: ``--help``
""""""""""""""""""""
Run

.. code-block::

   dds ls --help

.. note::
   Please let us know whether there is any additional information that you would like to see added to the help text.

2. List projects: ``ls``
""""""""""""""""""""""""""
.. code-block::
   
   dds ls 

.. note::
   The output of this command is (should be) **identical** to the output produced by 

   .. code-block::
      
      dds project ls 

   See the :ref:`dds project<dds-project>` documentation.

2.1. Run the command without any options

   .. admonition:: Expected result 
   
      A table containing the projects you have access to should be displayed. 
      
   .. warning:: 

      Notify us immediately if you are a **Unit Admin** or **Unit Personnel** and have created an project, but this project is not displayed in the printed table.

2.2. Sort the projects using the ``--sort`` option.

   .. admonition:: Expected result 

      The projects should be sorted according to `Last updated` by default. 

   Try sorting the projects according to different columns.

2.3. Display the usage using the ``--usage`` flag \*\*\*

   .. admonition:: Expected result 

      This should add two columns to the table: `Usage` and `Cost`.

2.4. Display the projects in json format using the ``--json`` flag.

   .. admonition:: Expected result 

      This should print out the projects in json format instead of a table. The output should look something like this:
      
      .. code-block:: bash

         [
            {
               "Last updated": "Sun, 20 Feb 2022 11:16:18 CET",
               "PI": "PI Name",
               "Project ID": "project_1",
               "Size": 0,
               "Status": "In Progress",
               "Title": "First Project"
            },
            {
               "Last updated": "Sun, 20 Feb 2022 11:16:18 CET",
               "PI": "PI Name",
               "Project ID": "project_2",
               "Size": 0,
               "Status": "In Progress",
               "Title": "Second Project"
            }
         ]

3. List project contents: ``ls --project``
""""""""""""""""""""""""""""""""""""""""""""
.. code-block:: 

   dds ls --project

.. note::
   The output produced by this command is (should be) **identical** to the output produced by

   .. code-block::

      dds data ls
   
   See the :ref:`dds data<dds-data>` documentation.

3.1. Without any options

   .. admonition:: Expected result

      This should produce a help message. The minimum required information for this command is the Project ID, specified with the ``--project`` option. 

3.2. List the contents of a specific folder (``--folder``) 

3.3. List the project contents as json format (``--json``)

3.4. Use the ``--tree`` flag to list all project contents as a tree structure

3.5. List the researchers with access to the project (``--users``)

-------

The commands
~~~~~~~~~~~~~~
.. _dds-ls:

.. click:: dds_cli.__main__:list_projects_and_contents
   :prog: dds ls
   :nested: full