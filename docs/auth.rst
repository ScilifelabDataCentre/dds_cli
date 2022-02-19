==============
`dds auth`
==============

This section begins with a description and step-by-step guide to how you could test this command. At the :ref:`bottom<dds-auth>` of this section, you can find the different commands and a list of their options.

How to test the `dds auth` command functionality
----------------------------------------------------

.. note::

   When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there’s anything we need to improve on, including the documentation on this page.

Steps
~~~~~~~

1. Run 
   
   .. code-block:: 

      dds auth --help 
   
   Is there any information you're missing from this help text?

2. Run the `login` subcommand

   2.1. With incorrect credentials

      .. note::
         You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.

   2.2. Using the correct characters in the credentials but exchanging them to lower case or upper case depending on the correct format

      .. note::
         You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.

   2.3. With correct credentials. You should be prompted for a one-time code sent to your email address.

      (i) Fill in an incorrect one-time code. 

         .. note:: 
            You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.
      
      (ii) Fill in the valid one-time code sent in the previous email.

         .. note:: 
            The system should not accept an old one-time code. You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.
         
      (iii) Fill in the valid one-time code

         .. note::
            You should be granted access, a message should be displayed, and there should be a `.dds_cli_token` in your home directory.

      (iv) Open the `.dds_cli_token` file or (in Unix systems) run 
         
         .. code-block::
         
            cat ~/.dds_cli_token 
         
         Are the contents/output readble?
      
         .. note::
            **They should not be**, inform the SciLifeLab Data Centre *immediately* if you can discern any information from the file contents.

3. Run the `info` subcommand.
   The information printed out should contain:

   * If the token is about to expire soon or not 
   * Token age
   * Token expiration time

   Is the information understandable?

4. Run the `logout` subcommand. A success message should be displayed.

5. Continue with any of the other commands: :ref:`user<user-info>`, :ref:`project<project-info>`, :ref:`data<data-info>` and :ref:`ls<ls-info>`.

----

.. _dds-auth:

The command
~~~~~~~~~~~~

.. click:: dds_cli.__main__:auth_group_command
   :prog: dds auth
   :nested: full