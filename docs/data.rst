==============
`dds data`
==============

This section begins with a description and step-by-step guide to how you could test this command. You can find the different commands and their options at the :ref:`bottom<dds-data>` of the section. 

How to test the `dds data` command functionality
----------------------------------------------------

.. note::

   When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there’s anything we need to improve on, including the documentation in this section.

From a *Unit Admin* or *Unit Personnel* account, you should be able to run all commands successfully. From a *Researcher* account, however, you should only be able to run the **dds data get** and **dds data ls** commands. 

.. note:: 
   
   Commands which should only work for Unit Adminds and Unit Personnel are noted in the step it applies to with three asterisks (\*\*\*). Asterisks applied to a main item (e.g. 3.) also applies to the subitems (e.g. 3.1., 3.2. etc). If there is additional information about the different permissions, this is displayed in a parenthesis beside the asterisk. 
   
   Although Project Owners and Researchers should not be able to successfully run most of these commands, we ask you to try these out anyway, and report back if anything unexpected happens.

Steps
~~~~~~

1. Run

   .. code-block::

      dds data --help

   .. note::
      Please let us know whether there is any additional information that you would like to see added to the help text.

2. Upload data with the ``put`` subcommand \*\*\*

   .. note::
      Some project statuses do not permit uploads. A visual respresentation of the project statuses can be found `on this board <https://app.diagrams.net/?page-id=vh0lXXhkObWnrkoySPmn&hide-pages=1#G1ophR0vtGByHxPG90mzjAPXgMTCjVcN_Z>`_. 

   .. admonition:: Recommended testing procedure

      We highly recommend that you test the upload functionality with data that is typical (both in size and number) for a project within your unit.

      We also recommend that you test the upload functionality by performing the following general steps:
      
      (i). Create a project with the ``dds project create`` command as described :ref:`here<dds-project>`. 
      
      (ii). Try uploading.
         
         .. admonition:: Expected result

            When creating a project the status should automatically be set to **In Progress** and therefore the upload should be successful.

      (iii). Change the project status to **Available** (``dds project status release``, more information :ref:`here<dds-project>`)
      
      (iv). Try uploading.

         .. admonition:: Expected result

            The upload should *not* work.
      
      (v). Change the project status to **In Progress** again (``dds project status retract``, more information :ref:`here<dds-project>`)
      
      (vi). Try uploading.

         .. admonition:: Expected result

            The upload should once again succeed.

      (vii). Change the project status to any other status and try the upload again.

         .. admonition:: Expect result

            Upload should not be allowed.

   .. admonition:: Options to test

      Test this command by trying different flags and options, for example: 
      
      * Without any specified options

         .. admonition:: Expected result

            The upload requires at least a project and data to upload. The CLI should display a help message. 

      * Specify a file / folder with the ``--source`` option. Also try specifying ``--source`` multiple times.
      * Specify files / folders within a text file and use the ``--source-path-file`` option.
      * Specify both the ``--source`` and ``--source-path-file`` option
      * Test the upload with a large number of files
      * Test the upload with a few large files 
      * Try uploading the same file twice

         .. admonition:: Expected result

            A message should be displayed stating that there's no data to upload. To upload the same file again, overwriting the previous file, specify the  ``--overwrite`` option.

      * Try the ``--silent`` flag and ``--num-threads`` option

3. List data with the ``ls`` subcommand

   .. note::
      This command performs the same actions as ``dds ls --project``. You can find the documentation for this :ref:`here<dds-ls>`. Please test this and compare the output, it should be identical to what you see here.

      Make sure to compare the output to the file structure you recently uploaded. If it does not seem correct, please contact us.
   
   3.1. Without any options

      .. admonition:: Expected result

         This should produce a help message. The minimum required information for this command is the Project ID, specified with the ``--project`` option. 
   
   3.2. List the contents of a specific folder (``--folder``) 

   3.3. List the project contents as json format (``--json``)

   3.4. Use the ``--tree`` flag to list all project contents as a tree structure

   3.5. List the researchers with access to the project (``--users``)

4. Download data with the ``get`` subcommand
   (- change the number of threads)
   (- try silent -- should only show the main progressbar, not for each file)
   (- try destination -)

   For unit personnel and admins:
   - download possible in in progress too
   recommended: 
   1. set project as in progress
   2. list project contents with the ls command described in 3.
   3. try to download a file 
   4. try to download a folder
   5. both
   4. set project as available 
   5. try to download a file
   6. set project as archived or aborted - this should remove data 
   7. try to list projcet contents - should not work 

   For researchers 
   - download possible only in available
   - should get an email when there is data available for download and the project is set as available
   recommended: 
   1. list project contents with 3. 
   2. download file (with and with and withoout source and spf)
      - doesn't exist
      - exists
   3. download folder (with and with and withoout source and spf)
      - doesn't exist
      - exists
   4. download both
   5. download all
   5. use the destination and play around with the flags

   NOTIFY immediately if the verify checksum fails 

   see the possible statuses here 


5. Delete (remove) data with the ``rm`` \*\*\*
   
   recommended: 
   1. list project contents
   2. remove a file
   3. list project contents
   4. remove a folder
   5. list project contents
   6. remove all 

-------

.. _dds-data:

The command
~~~~~~~~~~~~~

.. click:: dds_cli.__main__:data_group_command
   :prog: dds data
   :nested: full