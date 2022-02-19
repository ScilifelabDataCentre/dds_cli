==============
`dds auth`
==============

How to test the `dds auth` command functionality
----------------------------------------------------

.. note::

   When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there’s anything we need to improve on, including the documentation on this page.

Steps
~~~~~~~

#. Run 
   
   .. code-block:: 

      dds auth --help 
   
   Is there any information you're missing from this help text?

#. Run the `login` subcommand

   #. With incorrect credentials

      .. note::
         You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.

   #. Using the correct characters in the credentials but exchanging them to lower case or upper case depending on the correct format

      .. note::
         You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.

   #. With correct credentials. You should be prompted for a one-time code sent to your email address.

      #. Fill in an incorrect one-time code. 

         .. note:: 
            You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.
      
      #. Fill in the valid one-time code sent in the previous email.

         .. note:: 
            The system should not accept an old one-time code. You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.
         
      #. Fill in the valid one-time code

         .. note::
            You should be granted access, a message should be displayed, and there should be a `.dds_cli_token` in your home directory.

      #. Open the `.dds_cli_token` file or (in Unix systems) run 
         
         .. code-block::
         
            cat ~/.dds_cli_token 
         
         Are the contents/output readble?
      
         .. note::
            **They should not be**, inform the SciLifeLab Data Centre *immediately* if you can discern any information from the file contents.

#. Run the `info` subcommand.
   The information printed out should contain:

   * If the token is about to expire soon or not 
   * Token age
   * Token expiration time

   Is the information understandable?

#. Run the `logout` subcommand. A success message should be displayed.

#. Continue with any of the other commands: :ref:`user<user-info>`, :ref:`project<project-info>`, :ref:`data<data-info>` and :ref:`ls<ls-info>`.

----

.. _dds-auth:

.. click:: dds_cli.__main__:auth_group_command
   :prog: dds auth
   :nested: full