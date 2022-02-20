==============
`dds data`
==============

.. admonition:: Page structure 
   
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

.. _dds-data-help:

1. Help: ``--help``
""""""""""""""""""""
Run

.. code-block::

   dds data --help

.. note::
   Please let us know whether there is any additional information that you would like to see added to the help text.

.. _dds-data-put:

2. Upload: ``put`` \*\*\*
""""""""""""""""""""""""""
.. code-block::

   dds data put

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

.. _dds-data-ls:

3. List data: ``ls`` 
"""""""""""""""""""""
.. code-block::

   dds data ls

.. note::
   This command performs the same actions as ``dds ls --project``. You can find the documentation for this :ref:`here<dds-ls>`. Please test this and compare the output, it should be identical to what you see here.

   Make sure to compare the output to the file structure you recently uploaded. If it does not seem correct, please contact us.

3.1. Run the command without any options

   .. admonition:: Expected result

      This should produce a help message. The minimum required information for this command is the Project ID, specified with the ``--project`` option. 

3.2. List the contents of a specific folder (``--folder``) 

3.3. List the project contents as json format (``--json``)

3.4. Use the ``--tree`` flag to list all project contents as a tree structure

3.5. List the researchers with access to the project (``--users``)

.. _dds-data-get:

4. Download: ``get`` 
""""""""""""""""""""""
.. code-block::

   dds data get

.. note:: 

   Some project statuses do not permit downloads. For Researcher accounts, data is only available for download in projects with the status **Available**. For Unit Admin and Unit Personnel accounts, data is *also* available for download when the projects have the status **In Progress**. A visual representation of the project statuses can be found `on this board <https://app.diagrams.net/?page-id=vh0lXXhkObWnrkoySPmn&hide-pages=1#G1ophR0vtGByHxPG90mzjAPXgMTCjVcN_Z>`_.

   To simplify the testing of this section, we have split it up into :ref:`4.1. Unit Admins and Unit Personnel<dds-data-get-unit>` and :ref:`4.2. Researchers<dds-data-get-researcher>`.

   .. admonition:: Options to test

      **Independent of account role**, test this command by trying different flags and options, for example:

      * Without any specified options

         .. admonition:: Expected result

            The download requires a project ID and information on which data to download. The CLI should display a help message. 

      * Specify a file / folder with the ``--source`` option. Also try specifying ``--source`` multiple times in the same command. 

      * Specify files / folders within a text file and use the ``--source-path-file`` option.

      * Try the ``--silent`` flag and ``--num-threads`` option. 

      * Specify where you would like to download the data to by using the ``--destination`` option. 

         .. note:: 

            The ``--destination`` cannot (at this time) be an existing directory. You need to specify a new directory name and the DDS CLI will create it for you. 

      * Use the ``--verify-checksum`` flag. This performs an additional check to verify that the downloaded file is identical to the file uploaded by the Unit Admin / Personnel. 

         .. admonition:: Expected result

            A message informing you that the checksum verification passed should be displayed. 

         .. warning:: 

            Notify us immediately if the checksum verification fails. 

.. _dds-data-get-unit:

4.1. *Unit Admins and Unit Personnel* 
''''''''''''''''''''''''''''''''''''''
.. admonition:: Recommended testing prodecure

   We recommend that you test the functionality by performing the following general steps:

   (i) Use a project which you've uploaded data to. Make sure the project status is **In Progress**. See the :ref:`dds project section<dds-project>` for instructions on how to do this. 

   (ii) List the project contents with the ``ls`` command described in point 3. above. 

   (iii) Download a file

      * Try to download a file that is not listed in step (ii) above

         .. admonition:: Expected result

            A message should be printed out, letting you know that the file could not be found.
      
      * Download a file that is listed in step (ii) above. 

         .. admonition:: Expected result

            A folder should be created in your current working directory (or in the location you choose, see ``--destination`` below), the file should be downloaded, and finally decrypted. Once the file has been downloaded and decrypted, a message should be displayed notifying you where you can find the file.

   (iv) Download a folder

      * Try to download a folder that is not listed in step (ii) above

         .. admonition:: Expected result

            A message should be printed out, notifying you that the folder could not be found.

      * Download a folder that is listed in step (ii) above

         .. admonition:: Expected result 

            The result of this should be similar to the download in step (iii) above. 

   (v) Download a folder and a file

      .. admonition:: Expected result

         The result of this command should be similar to the download in steps (iii) and (iv) above.

   (vi) Set the project status as **Available**. See the :ref:`dds project section<dds-project>` for instructions on how to do this. 

   (vii) Try to download a file / folder

      .. admonition:: Expected result

         Since download is available for Unit Admins and Unit Personnel when the project status is **Available**, the download should be successful and the output should be similar to that of the download steps above.

   (viii) Set the project as **Archived** or **Aborted**. 
      
      .. admonition:: Expected result

         Archiving or aborting a project should delete all project data. 

   (ix) Try to download data 

      .. admonition:: Expected result 

         Download should not be possible and a message informing you that the project status prevents you from downloading should be displayed. 

.. _dds-data-get-researcher:

4.2. *Researchers*
'''''''''''''''''''
.. admonition:: Recommended testing prodecure

   We recommend that you test the functionality by performing the following general steps:

   (i) Display the status of a project you have access to. Use ``dds ls`` to list the projects, and ``dds project status display`` to see the status of a specific project. Choose a project which has the status **Available**. 

      .. note:: 

         When a project status is changed from **In Progress** to **Available**, you should receive an email informing you that there is data available for download. If you have access to a project which is **Available** but you have not received an email about this, first check your junk folder. If you still cannot find this email, contact us and we will look into it.

   (ii) List the contents of the project. See :ref:`List data<dds-data-ls>` above. 

   (iii) Download a file

      * Try to download a file that is not listed in step (ii) above

         .. admonition:: Expected result

            A message should be printed out, letting you know that the file could not be found.
      
      * Download a file that is listed in step (ii) above. 

         .. admonition:: Expected result

            A folder should be created in your current working directory (or in the location you choose, see ``--destination`` below), the file should be downloaded, and finally decrypted. Once the file has been downloaded and decrypted, a message should be displayed notifying you where you can find the file.

   (iv) Download a folder

      * Try to download a folder that is not listed in step (ii) above

         .. admonition:: Expected result

            A message should be printed out, notifying you that the folder could not be found.

      * Download a folder that is listed in step (ii) above

         .. admonition:: Expected result 

            The result of this should be similar to the download in step (iii) above. 

   (v) Download a folder and a file

      .. admonition:: Expected result

         The result of this command should be similar to the download in steps (iii) and (iv) above.

   (vi) Use the ``--get-all`` flag to download the entire project. 

      .. note:: 

         Make sure you have enough space.
   
.. _dds-data-rm:

5. Delete (remove): ``rm`` \*\*\*
""""""""""""""""""""""""""""""""""
.. code-block::

   dds data rm

.. admonition:: Recommended testing prodecure

   We recommend that you test the functionality by performing the following general steps:

   (i) List the project contents with the ``dds data ls`` command as described in :ref:`List data<dds-data-ls>` above. 

   (ii) Attempt to remove a file.

   (iii) List the project contents again.

   (iv) Attempt to remove a folder.

   (v) List the project contents again.
   
   (vi) Use the `--rm-all` flag to remove all project contents.

   .. note:: If the CLI displays a success message, but the data is not removed, contact us and we will look into it. 

.. admonition:: Expected result (all ``rm`` steps above)

   When attempting to remove data which does not exist, a message should be displayed in the terminal saying that the data was not found. 

   When attempting to remove data which does exist in the project and is listed in step (i), a success message should be displayed, informing you that the data was removed. 

-------

.. _dds-data:

The command
~~~~~~~~~~~~~

.. click:: dds_cli.__main__:data_group_command
   :prog: dds data
   :nested: full