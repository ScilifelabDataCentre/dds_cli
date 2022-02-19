.. _dds-main:

=====================
DDS main CLI command 
=====================

How to test the functionality of the main `dds` command
-------------------------------------------------------

.. note:: 

   When running the commands, remember to make a note of whether or not any information or error messages are understandable and if there’s anything we need to improve on, including the documentation on this page.
   
Steps
~~~~~~

#. Run the *dds* command without any options or additional commands. Simply run:

   .. code-block:: bash

      $ dds

   .. note:: 
      Please let us know whether there is any additional information that you would like to see added to the help text.

#. When running other subcommands, please try out the different flags and options listed below. To see the instructions on how to use these commands, go to :ref:`dds auth<dds-auth>`, :ref:`dds user<dds-user>`, :ref:`dds project<dds-project>`, :ref:`dds data<dds-data>` or :ref:`dds ls<dds-ls>`.

-----

.. click:: dds_cli.__main__:dds_main
   :prog: dds
   :nested: short
