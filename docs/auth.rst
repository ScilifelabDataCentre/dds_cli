==============
`dds auth`
==============

.. admonition:: Section structure 
   
   This section begins with a description and step-by-step guide to how you could test this command. You can find the different commands and their options at the :ref:`bottom<dds-auth>` of the section. 


How to test the `dds auth` command functionality
----------------------------------------------------

.. note::

   When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there’s anything we need to improve on, including the documentation on this page.

Steps
~~~~~~~

1. Help: ``--help``
""""""""""""""""""""
Run
   
.. code-block:: 

   dds auth --help 

.. note::
   Please let us know whether there is any additional information that you would like to see added to the help text.

2. Start authenticated session: ``login``
"""""""""""""""""""""""""""""""""""""""""""
.. code-block::

   dds auth login 

2.1. With incorrect credentials

   .. note::
      You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.

2.2. Using the correct characters in the credentials but exchanging them to lower case or upper case depending on the correct format

   .. note::

      **Username:** The username should be case *insensitive*. If your username is ``username`` you should also be able to login with ``USERNAME`` or ``uSeRnAmE`` etc.

      **Password:** The password should be case *senstive*. Only the exact characters in your password, including whether or not they are upper case or lower case, should give you access to the system.
      
      If either the username or password is incorrect, you **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory.

2.3. With correct credentials. You should receive an email containing a one-time code and be prompted by the command line to enter this code.

   (i) Fill in an incorrect one-time code. 

      .. note:: 
         You **should not** be granted access and you **should not** have a `.dds_cli_token` file in your home directory. You should be asked by the command line if you want to try again. If you choose to try again, you should not recieve a new one-time code. If you cancel the current command and run `dds auth login` again, you should also not receive a new one-time code. However, if you wait 15 minutes and then try again, you should receive a new one-time code via email. This setup is due to security reasons.
   
   (ii) Wait 15 minutes and run the `dds auth login` command again. You should receive a new email with a new one-time code. Fill in the one-time code sent in the previous email.

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

1. Get session information: `info`
"""""""""""""""""""""""""""""""""""
.. code-block::

   dds auth info 

The information printed out should contain:

* Whether the token will expire
* When the token will expire

Is the information understandable?

1. End the authenticated session: ``logout``
"""""""""""""""""""""""""""""""""""""""""""""
.. code-block::

   dds auth logout 

.. admonition:: Expected result

   A success message should be displayed and the file ``.dds-cli-token`` file in your home directory should be deleted.

5. Continue with other commands
""""""""""""""""""""""""""""""""
Continue using the DDS CLI: 

* Manage users: :ref:`dds user<user-info>`

* Manage projects: :ref:`dds project<project-info>`

* Upload, download, list and remove data: :ref:`dds data<data-info>` 

* List projects and data: :ref:`dds ls<ls-info>`.

----

.. _dds-auth:

The command
~~~~~~~~~~~~

.. click:: dds_cli.__main__:auth_group_command
   :prog: dds auth
   :nested: full