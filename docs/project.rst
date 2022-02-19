==============
`dds project`
==============

How to test the `dds project` command functionality
----------------------------------------------------

* Researchers
   - ls
   - status 
      - display
* Unit Personnel / Admins 
   - all

* access
   * grant
   * revoke
   * fix
* create 
   * without users
   * with users
   * sensitive (at the moment no difference, sensitive is default)
   * not sensitive 
* ls
   * sort
   * usage
   * json
* status - create -> display -> try to change -> display 
   * abort
   * archive
   * delete
   * display
   * release
   * retract

2. create 




----------

.. _dds-project:

The command
~~~~~~~~~~~~

.. click:: dds_cli.__main__:project_group_command
   :prog: dds project
   :nested: full