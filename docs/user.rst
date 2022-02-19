==============
`dds user`
==============

How to test the `dds user` command functionality
----------------------------------------------------

.. note::

   When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there’s anything we need to improve on, including the documentation on this page.

As a *Unit Admin* or *Unit Personnel* account, you should be able to run all commands successfully. As a *Researcher* however, you will only be able to run the `info` command, unless you're a *Project Owner* for a specific project. In this case you should only be able to handle other Project Owners and Researchers which are involved in the project you are set as Project Owner in. 

Although Project Owners and Researchers should not be able to successfully run most of these commands, we ask you to try these out anyway, and report back if anything unexpected happens.

.. list-table:: Different roles and their permissions
   :header-rows: 1
   :stub-columns: 1
   :widths: auto

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
     - Yes 
       
       *Within certain projects*

     - No
   * - `deactivate`
     - Yes
     - Yes 
     - Yes 
     
       *Other Project Owners and Researchers 
       within certain projects*

     - No
   * - `activate` 
     - Yes
     - Yes
     - Yes 
     
       *Other Project Owners and Researchers 
       within certain projects*

     - No
   * - `delete`
     - Yes
     - Yes
     - Yes 
     
       *Other Project Owners and Researchers 
       within certain projects*

     - Yes 
     
       *Only own account*


Steps
~~~~~~~

.. note::

   These test steps assume you have already started a session with the :ref:`dds auth<dds-auth>` command.

#. Run

   .. code-block::

      dds user --help

   Is there any information you're missing from this help text? 

#. Run the `info` subcommand
   
   .. note:: 
      
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

   #. Try to invite yourself by specifying the email your current account is registered with
      
      .. note:: 
         This should not work and a message notifying you of this should be displayed.
   
   #. Try to invite a user (without the `project` option) and specify the `role`

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

   #. Try to invite a user (`project` option *specified*) and the `--role`:

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

   #. Try to deactivate a fake account

      .. note:: 
         A fake account does not exist and should therefore not be possible to deactivate.

   #. Try to deactivate another account, either one of your own, created in the steps above, or another colleagues.

      .. warning:: 
         Please make sure to notify the user you are attempting to deactivate. 

      .. note:: 
         You can also attempt inviting yourself to multiple accounts and specifying different roles, after which (and after registration in the `web<web>`) you can attempt to deactivate the different accounts. Have a look at the table at the top of the page if you are uncertain about which actions should be possible.

#. Run the `activate` subcommand

#. Run the `delete` subcommand

-----

.. _dds-user:

.. click:: dds_cli.__main__:user_group_command
   :prog: dds user
   :nested: full