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
   
   Commands that should only work for Unit Adminds and Unit Personnel are noted in the step it applies to with three asterisks (\*\*\*). Asterisks applied to a main item (e.g. 3.) also applies to the subitems (e.g. 3.1., 3.2. etc). If there is additional information about the different permissions, this is displayed in a parenthesis beside the asterisk. 
   
   Although Project Owners and Researchers should not be able to successfully run most of these commands, we ask you to try these out anyway, and report back if anything unexpected happens.

Steps
~~~~~~

1. Run

   .. code-block::

      dds data --help

   .. note::
      Please let us know whether there is any additional information that you would like to see added to the help text.

2. Upload data with the ``put`` subcommand \*\*\*
   (- change the number of threads)
   (- try silent -- should only show the main progressbar, not for each file)

   this is a bit complicated since you're not allowed to upload in all project statuses
   see the possible statuses here 
   
   recommend: 
   1. create project
   2. test upload -- should succeed
   3. change status to available -- should send emails to the users that have access to the project
   4. test upload -- should fail 
   5. change status to in progress again
   6. test upload -- should succeed
   7. change status to any other status -- should fail   
   
   do this with files that are typical when it comes to size and number 

   try different 
   - without any options
   - specify one --source and multiple
   - specify one source path file and multiple
   - specify both source and source path file
   - upload a large number of files/folders
   - upload a few large files
   - try uploading same file
   - upload same file with overwrite 

3. List data with the ``ls`` subcommand
   -- this calls the same as  ``dds ls --project`` command, see the documentation for this here -- 
   -- compare, should produce identical output -- 
   -- compare to the files you just uploaded, does it seem correct --

   - ls 
   - folder
   - json
   - tree 
   - users 

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
   2. download file
   3. download folder
   4. download both
   5. 

   see the possible statuses here 

   try different 
   - without any options
   - specify files that
   - specify one --source and multiple
   - specify one source path file and multiple
   - specify both source and source path file
   - 





5. Delete (remove) data with the ``rm`` \*\*\*

-------

.. _dds-data:

The command
~~~~~~~~~~~~~

.. click:: dds_cli.__main__:data_group_command
   :prog: dds data
   :nested: full