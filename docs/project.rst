==============
`dds project`
==============

This section begins with a description and step-by-step guide to how you could test this command. At the :ref:`bottom<dds-projecth>` of this section, you can find the different commands and a list of their options.

How to test the `dds project` command functionality
----------------------------------------------------

.. note::

   When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there’s anything we need to improve on, including the documentation in this section.

From a *Unit Admin* or *Unit Personnel* account, you should be able to run all commands successfully. From a *Researcher* however, you will only be able to run the `dds project ls` and `dds status display` commands, unless you're a *Project Owner* for a specific project. In this case you should also be able to grant and revoke project access to other Project Owners and Researchers that are involved in the project you are set as Project Owner in. 

Although Project Owners and Researchers should not be able to successfully run most of these commands, we ask you to try these out anyway, and report back if anything unexpected happens.

* Researchers
   - ls
   - status 
      - display
* Unit Personnel / Admins 
   - all

Steps
~~~~~~

1. Run
   -- All --
   .. code-block::

      dds project --help

   Is there any information you're missing from this help text? 

2. Run the `ls` subcommand
   -- All -- 
   2.1. without any options
   2.2. try to sort the projects
   2.3. try to display the usage
   2.4. display the projects in json output 

3. Run the `create` subcommand
   -- Unit Admins and Unit Personnel --
   3.1. without any options
   3.2. without users
   3.3. with a researchuser
   3.4. with a project Owner
   3.5. with both researchuser and owner 
   -- there is a non-sensitive flag but it's not used for anything at the moment, all projects are by default sensitive -- 

4. Run the `status` subcommand
   -- For Unit Admins / Personnel we recommend to check this functionality by creating a project, displaying the status, attempting to change the status and then displaying again to see that it has taken affect. -- 
   4.1. display -- All --
      * Non existent project
      * Existing project 
      * show history 
      - information on what should be displayed - 
   4.2. try the different changes -- Unit Admins / Personnel --
      -- Image of possible status transactions -- 
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