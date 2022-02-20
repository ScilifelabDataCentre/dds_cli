==============
`dds project`
==============

This section begins with a description and step-by-step guide to how you could test this command. You can find the different commands and their options at the :ref:`bottom<dds-project>` of the section. 

How to test the `dds project` command functionality
----------------------------------------------------

.. note::

   When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there’s anything we need to improve on, including the documentation in this section.

From a *Unit Admin* or *Unit Personnel* account, you should be able to run all commands successfully. From a *Researcher* account, however, you should only be able to run the **dds project ls** and **dds status display** commands, unless you're a *Project Owner* for a specific project. In this case you should also be able to grant (**dds project access grant**) and revoke (**dds project access revoke**) project access to other Project Owners and Researchers that are involved in the project you are set as Project Owner in. 

.. note:: 
   
   Commands that should only work for Unit Adminds and Unit Personnel are noted in the step it applies to with three asterisks \*\*\*). Asterisks applied to a main item (e.g. 3.) also applies to the subitems (e.g. 3.1., 3.2. etc). If there is additional information about the different permissions, this is displayed in a parenthesis beside the asterisk. 
   
   Although Project Owners and Researchers should not be able to successfully run most of these commands, we ask you to try these out anyway, and report back if anything unexpected happens.


Steps
~~~~~~

1. Run

   .. code-block::

      dds project --help

   .. note::
      Please let us know whether there is any additional information that you would like to see added to the help text.

2. List the projects with the ``ls`` subcommand

   .. note::
      This command performs the same actions as ``dds ls`` (with out any specified project). You can find the documentation for that :ref:`here<dds-ls>`. Please test this and compare the output, it should be identical to what you see here.

   2.1. Without any options

      .. note::
         A table containing the projects you have access to should be displayed. 
         
      .. warning::
         Notify us immediately if you are a **Unit Admin** or **Unit Personnel** and have created an project, but this project is not displayed in the printed table.

   2.2. Sort the projects using the ``--sort`` option.

      .. note:: 
         The projects should be sorted according to `Last updated` by default. 

      Try sorting the projects according to different columns.

   2.3. Display the usage using the ``--usage`` flag \*\*\*

      .. note::
         This should add two columns to the table: `Usage` and `Cost`.

   2.4. Display the projects in json format using the ``--json`` flag.

      .. note::
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


3. Create a project with the ``create`` subcommand \*\*\*

   .. note:: 
      All projects are set as **sensitive** by default. This means that all data will be encrypted before upload, and decrypted after download. Depending on the size of the data, this may take some time. There is a ``--non-sensitive`` flag available, however at this time this is not functional and all projects are handled in the same way. Therefore, if you use the `--non-sensitive` flag, the project will be saved in the database as non-sensitive, but the data will still be handled as if it is sensitive. This will be changed as soon as possible.

   3.1. Without any options

      .. note::
         To create a project you need to specify a title, a description and the principal investigator (PI) of that project. Without this information, creating a project should not be possible. 

   3.2. With all required options: ``--title``, ``--description``, ``--principal-investigator`` but without adding any users

      .. note::
         A project should be created and you should see a message displayed stating the new Project ID. This Project ID should be passed in as the ``--project`` option when running project-specific commands. If you forget the Project ID, use the ``dds ls`` command to list all projects.

   3.3. Create a project and specify a Researcher (``--researcher``) that should have access to the project.

      You can either specify a researcher that you know has a DDS account, or you can specify a user which you wish to invite to the DDS. 

      .. note:: 
         A project should be created, a message should be displayed stating the new Project ID, and an additional message should be displayed, stating that the specified Researcher has either been sent an invitation, or granted access to the project, depending on whether or not the specified email has an existing account. 

   3.4. Create a project and specify an Project Owner (``--owner``)
      
      As in 3.3. above, the owner can either be a new user or and existing one. 

      .. note:: 
         A project should be created, a message should be displayed stating the new Project ID, and an additional message should be displayed, stating that the specified owner has either been sent an invitation, or granted access to the project, depending on whether or not the specified email has an existing account. The message should also inform you that the user has been granted access as a Project Owner.

   3.5. Specify both a Researchuser and an owner. 
   
      Perform the same steps as in 3.3. and 3.4. but specify both a ``--researcher`` and an ``--owner``. 

      .. note::
         This should result in a similar output as in the previous steps.

   3.6. With multiple users. 

      Perform the same steps as in 3.3. and 3.4. but try specifying multiple researchers and / or owners. 

      .. note:: 
         This should result in a similar output as in the previous steps.

4. View and manage the project statuses with the ``status`` subcommand 

   4.1. Display the status of a project (``status display``)

      * Specify a non-existent project 

         .. note::
            A message saying that the project does not exist should be displayed.

      * Specify an existing project

         .. note::
            The output should look something like this:

            .. code-block:: bash

               Current status of someunit00002: In Progress

      * Also show the status history with the ``--show-history`` flag

         .. note:: 
            The output should look something like this:

            .. code-block:: bash

               Current status of someunit00002: In Progress
               INFO     Status history
               In Progress, Sun, 20 Feb 2022 11:51:13 CET 
   
   4.2. try the different changes \*\*\*
      
      .. note:: 
         We recommend testing this functionality in the following steps: 

         (i) Create a project
         (ii) Display status. The status should always be **In Progress** at this point.
         (iii) Attempt changing the status.
         (iv) Display status.

      The possible status changes are displayed `on this board <https://app.diagrams.net/?page-id=vh0lXXhkObWnrkoySPmn&hide-pages=1&viewbox=%7B%22x%22%3A-753%2C%22y%22%3A-503%2C%22width%22%3A1676%2C%22height%22%3A1656%2C%22border%22%3A100%7D#G1ophR0vtGByHxPG90mzjAPXgMTCjVcN_Z>`_.

      -- We recommend to test different changes in different combinations -- 
5. Run the `access` subcommand
   -- Unit Personnel / Admins -- 
   -- before doing this you can list the project users as described :ref:`here<dds-ls>` -- 
   5.1. grant 
      * non existent user 
      * existent user
      * existent unit Personnel
   5.2. revoke
      * non existent user
      * existent user that doesn't have access
      * revoke access for those that you granted
   5.3 fix
      -- Unit Personnel / Admins / Project Owner -- 
      -- this is to reactivate a users project access if they have lost it after requesting a password reset -- 
      -- difficult to test unless someone contacts you about losing access, but you can follow the :ref:`web instructions<web>` on how to request a password reset, and then ask someone in your unit to perform this command for you. -- 
      * non existent user
      * a user you have deactivated (as tested :ref:`here<dds-user>`)

----------

.. _dds-project:

The command
~~~~~~~~~~~~

.. click:: dds_cli.__main__:project_group_command
   :prog: dds project
   :nested: full