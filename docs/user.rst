==============
`dds user`
==============

How to test the `dds user` command functionality
----------------------------------------------------
When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there's anything we need to improve on. 

As a *Unit Admin* or *Unit Personnel* account, you should be able to run all commands successfully. As a *Researcher* however, you will only be able to run the `info` command, unless you're a *Project Owner* for a specific project. In this case you should only be able to handle other Project Owners and Researchers which are involved in the project you are set as Project Owner in. 

Although Project Owners and Researchers should not be able to successfully run most of these commands, we ask you to try these out anyway, and report back if anything unexpected happens.

.. list-table:: Different roles and their permissions
   :header-rows: 1

   * - Command
     - Unit Admin
     - Unit Personnel
     - Project Owner
     - Researcher
   * - `info`
     - Yes
     - Yes 
     - Yes
     - Yes
   * - `add`
     - Yes
     - Yes
     - Yes (within certain projects)
     - No
   * - `deactivate`
     - Yes
     - Yes 
     - Yes (Other Project Owners and Researchers within certain projects)
     - No
   * - `activate` 
     - Yes
     - Yes
     - Yes (Other Project Owners and Researchers within certain projects)
     - No
   * - `delete`
     - Yes
     - Yes
     - Yes (Other Project Owners and Researchers within certain projects)
     - Yes (Only own account)


Steps
~~~~~~~

#. Run

   .. code-block::

      dds auth --help

   Is there any information you're missing from this help text? 

#. Run the `info` subcommand
   The information printed out should contain your

   * Username
   * Role
   * Name
   * Emails connected to the account

#. Run the `add` subcommand

   #. Invite a new user to the DDS

      .. warning::
         Please either use one of your own accounts or a colleague that is also involved in the testing of the DDS.

   #. Invite the same user to DDS again
      
      .. note:: 
         This should not work and a message notifying you that the user has an ongoing invite should be displayed.

   #. Try to invite yourself
      
      .. note:: 
         This should not work and a message notifying you of this should be displayed.
   
   #. Try to invite a user (no `--project`) and specify the `--role`

      * Unit Admin

         .. note:: 
         Should only work for other Unit Admin accounts.

      * Unit Personnel
         
         .. note:: 
         Should only work for other Unit Personnel and Unit Admin accounts.

      * Project Owner

         .. note::
         Should work for Researcher accounts assigned as Project Owners  within a specific project, Unit Personnel and Unit Admin accounts.
      
      * Researcher 

         .. note::
            Anyone should be able to invite a user with the role Researcher. 

   #. Try to invite a user (`--project` specified) and specifying the `--role`

      * Unit Admin

         .. note:: 
         This should work for other Unit Admins as above, but there should be a message displayed saying that all Unit Admins get access to all projects within a specific unit.

      * Unit Personnel
         
         .. note:: 
         This should work for other Unit Personnel and Unit Admin accounts, but as for the Unit Admin, all Unit Personnel accounts get access to all unit projects and there should therefore be a print out of a message informing you of this.

      * Project Owner

         .. note::
         Should work for Researcher accounts assigned as Project Owners  within a specific project, Unit Personnel and Unit Admin accounts.
      
      * Researcher 

         .. note::
            Anyone should be able to invite a user with the role Researcher. 

#. Run the `deactivate` subcommand

   #. Try to deactivate your own account
      
      .. note::
         This should not work and a message notifying you of this should be displayed.

   #. Try to deacti

#. Run the `activate` subcommand

#. Run the `delete` subcommand


.. _dds-user:

.. click:: dds_cli.__main__:user_group_command
   :prog: dds user
   :nested: full