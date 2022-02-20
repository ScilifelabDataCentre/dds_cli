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
   
   Commands that should only work for Unit Adminds and Unit Personnel are noted in the step it applies to with three asterisks (\*\*\*). Asterisks applied to a main item (e.g. 3.) also applies to the subitems (e.g. 3.1., 3.2. etc). If there is additional information about the different permissions, this is displayed in a parenthesis beside the asterisk. 
   
   Although Project Owners and Researchers should not be able to successfully run most of these commands, we ask you to try these out anyway, and report back if anything unexpected happens.


Steps
~~~~~~

1. Help: ``--help``
"""""""""""""""""""
Run

.. code-block::

   dds project --help

.. note::
   Please let us know whether there is any additional information that you would like to see added to the help text.

2. List projects: ``ls``
"""""""""""""""""""""""""

.. note::
   This command performs the same actions as ``dds ls`` (with out any specified project). You can find the documentation for that :ref:`here<dds-ls>`. Please test this and compare the output, it should be identical to what you see here.

2.1. Without any options

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


3. Create a project ``create`` \*\*\*
""""""""""""""""""""""""""""""""""""""
.. note:: 
   All projects are set as **sensitive** by default. This means that all data will be encrypted before upload, and decrypted after download. Depending on the size of the data, this may take some time. There is a ``--non-sensitive`` flag available, however at this time this is not functional and all projects are handled in the same way. Therefore, if you use the ``--non-sensitive`` flag, the project will be saved in the database as non-sensitive, but the data will still be handled as if it were sensitive. This will be changed as soon as possible.

3.1. Without any options

   .. admonition:: Expected result 

      To create a project you need to specify a title, a description and the principal investigator (PI) of that project. Without this information, creating a project should not be possible. 

3.2. With all required options: ``--title``, ``--description``, ``--principal-investigator`` but without adding any users

   .. admonition:: Expected result 

      A project should be created and you should see a message displayed stating the new Project ID. This Project ID should be passed in as the ``--project`` option when running project-specific commands. If you forget the Project ID, use the ``dds ls`` command to list all projects.

3.3. Create a project and specify a Researcher (``--researcher``) that should have access to the project.

   You can either specify a researcher that you know has a DDS account, or you can specify a user which you wish to invite to the DDS. 

   .. admonition:: Expected result 

      A project should be created, a message should be displayed stating the new Project ID, and an additional message should be displayed, stating that the specified Researcher has either been sent an invitation, or granted access to the project, depending on whether or not the specified email has an existing account. 

3.4. Create a project and specify an Project Owner (``--owner``)
   
   As in 3.3. above, the owner can either be a new user or and existing one. 

   .. admonition:: Expected result 

      A project should be created, a message should be displayed stating the new Project ID, and an additional message should be displayed, stating that the specified owner has either been sent an invitation, or granted access to the project, depending on whether or not the specified email has an existing account. The message should also inform you that the user has been granted access as a Project Owner.

3.5. Specify both a Researchuser and an owner. 

   Perform the same steps as in 3.3. and 3.4. but specify both a ``--researcher`` and an ``--owner``. 

   .. admonition:: Expected result 

      This should result in a similar output as in the previous steps.

3.6. With multiple users. 

   Perform the same steps as in 3.3. and 3.4. but try specifying multiple researchers and / or owners. 

   .. admonition:: Expected result 

      This should result in a similar output as in the previous steps.

4. View and manage the project statuses: ``status``
"""""""""""""""""""""""""""""""""""""""""""""""""""" 

4.1. Display the status of a project (``status display``)

   * Specify a non-existent project 

      .. admonition:: Expected result 

         A message saying that the project does not exist should be displayed.

   * Specify an existing project

      .. admonition:: Expected result 

         The output should look something like this:

         .. code-block:: bash

            Current status of someunit00002: In Progress

   * Also show the status history with the ``--show-history`` flag

      .. admonition:: Expected result 

         The output should look something like this:

         .. code-block:: bash

            Current status of someunit00002: In Progress
            INFO     Status history
            In Progress, Sun, 20 Feb 2022 11:51:13 CET 

4.2. Attempt changing the project status \*\*\*
   
   .. tip:: 
      We recommend testing this functionality in the following steps: 

      (i) Create a project
      (ii) Display status. The status should always be **In Progress** at this point.
      (iii) Attempt changing the status.
      (iv) Display status.

      Please attempt to change the project status in different orders. 

   The possible status changes are displayed visually `on this board <https://app.diagrams.net/?page-id=vh0lXXhkObWnrkoySPmn&hide-pages=1&viewbox=%7B%22x%22%3A-753%2C%22y%22%3A-503%2C%22width%22%3A1676%2C%22height%22%3A1656%2C%22border%22%3A100%7D#G1ophR0vtGByHxPG90mzjAPXgMTCjVcN_Z>`_ and are listed in the :ref:`documentation below<dds-project>`.

5. Manage project access: ``access`` \*\*\* (Also possible for Project Owners)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. tip:: 
   We recommend testing this functionality in the following steps:
      
   (i) List the users with access to a specific project: ``dds ls --project <project_id> --users``. More details on the ``dds ls`` command can be found :ref:`here<dds-ls>`. 
   (ii) Grant / Revoke / Fix access for a specific user as described in the steps below.
   (iii) Do step (i)

5.1. Grant access to a project (``access grant``)
   
   .. tip:: 
      We suggest you list the users with access to the project in question before performing the following tests. Go :ref:`here<dds-ls>` for the instructions on how to do this.

   (i) Specify a non-existent user.

      .. admonition:: Expected result 

         The user should be invited and a message notifying you of this should be displayed. Note that you can only use ``grant`` for Researchers, not Unit Admins or Unit Personnel. 

   (ii) Specify an existing user.

      * Attempt to grant access to a user with the role **Unit Admin** or **Unit Personnel**

         .. admonition:: Expected result 

            This command should produce an error message. Unit Admins / Personnel have access to *all* projects connected to a specific unit. Only researchers can be granted access with this command.

      * Attempt to grant access to a user with the role **Researcher**

         Try to grant access both to a user which already has access to the specified project, and one who does not. Also try this with the ``--owner`` flag. 

         .. admonition:: Expected result 

            If the user already has access to the project, and is already set as the Project Owner, using the ``--owner`` flag for this command should return a message stating that the user is already associated to the project in that capacity. The same applies to it the user is associated to the project as a Researcher and the ``--owner`` flag is *not used*.

5.2. Revoke project access (``access revoke``)

   .. tip:: 
      We suggest you list the users with access to the project in question before performing the following tests. Go :ref:`here<dds-ls>` for the instructions on how to do this.

   (i) Specify a non-existent user
      
      .. admonition:: Expected result 

         A non-existent user cannot have access to a project and it should therefore not be possible to revoke project access for that user.

   (ii) Specify an existing user that does not have access to the current project.

      .. admonition:: Expected result 

         This should produce a message saying that the specified user does not have access to the project. 

   (iii) Revoke project access for the users that you granted access in step 5.1. (ii)

      .. admonition:: Expected result 
      
         A message should be displayed informing you that the users' project access has been revoked.

5.3 Fix project access (``access fix``)

   .. note:: 

      This command is used to reactivate a users' project access a password reset. More specifically, the user has performed the following steps:
      
      (i) Requested a password reset
      (ii) Clicked on the link in the received email 
      (iii) Chosen a new password 
      (iv) Contacted the Project Owner or a Unit Admin / Personnel connected to the unit responsible for a specific project to regain access

   .. tip::

      Unless someone contacts you about losing access, this step is slightly difficult to test. However, you can follow the :ref:`web instructions<web>` on how to request a password reset and ask another user to reactivate your project access with this command. 

      You can also attempt this with users that do not have access to a specific project.

----------

.. _dds-project:

The command
~~~~~~~~~~~~

.. click:: dds_cli.__main__:project_group_command
   :prog: dds project
   :nested: full