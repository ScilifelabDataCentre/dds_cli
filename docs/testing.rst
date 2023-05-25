.. Information for users which have been invited to the development / test instance of the DDS.

.. _testing:

======================
The DDS Test instance
======================

**Welcome, and thank you for your interest in testing the Data Delivery System.**

This page will give you information on: 

.. contents::
   :local:

.. admonition:: Target audience 

    This page targets any users invited to the development / testing instance of the Data Delivery System. If you have an account on the production instead (https://delivery.scilifelab.se), please read the documentation here :ref:`here<start>`.

.. _test-important:

1. Important information for SciLifeLab Units
==============================================

.. note:: 

    If your testing account has the role "Researcher", you can skip this section. 

* First and foremost, **no sensitive data** is allowed to be delivered within this test instance. 
* In order to create projects, which is required in order to test the upload / download functionality: 
    * You must have the account role "Unit Admin" or "Unit Personnel"
    * Your unit must have at least two "Unit Admins" 
* When listing your projects you will see your projects, and yours only. However, in order to not create a large number of separate storage locations for testing purposes, the actual storage location is shared by all units in the test setup. Since the data is always encrypted and another unit would need to hack the DDS and also crack the encryption, there should be no risk of anyone else accessing your data. In the production instance, there's always a separate storage location per SciLifeLab unit.
* The storage quota (maximum data volume that can be uploaded in total by all units) for the testing instance is currently set to 5 TB. However, if you receive an error message indicating that the quota is met, contact delivery@scilifelab.se and we will solve this for you. 
* Within the test instance of the DDS, all units have the following settings:
    * ``days_in_available``: 7 days. 
    
        **Explanation:** When data has been uploaded to a project, and the data has been released (the project status has been set to "Available"), the data will be available for download for 7 days. After this, the project will automatically transition to the status "Expired".

    * ``days_in_expired``: 3 days

        **Explanation:** When a project has transitioned to the status "Expired", the project data will be kept for 3 days. During this time you can release the project data again (checkout the ``dds project status`` command) and transition the status to "Available" again. If you do not, your project will be automatically archived (project status will be changed to "Archived"), and your data will be permanently deleted.

    .. note:: 

        * These statuses are described in the technical overview, located on the DDS test web page mentioned above.
        * The short number of days is only for the test instance, making it easier for you (and us) to test that the statuses work as they should.

* Keep in mind that the test instance is where we try out new features etc. There may be some unexpected redeployments and there may be bugs in new features.

.. _test-where:

2. Where the DDS Test Instance is located
============================================

* The test instance is located at https://dds-dev.dckube3.scilifelab.se/
* Just like on the production site, you can find the following information on that page:
    * *Documentation*, which points to the ``Welcome page`` in the navigation field to the left.
    * *Technical overview* 
    * *Troubleshooting guide*

.. _test-install:

3. How to install the test version of the CLI
================================================

You need to install the test version of the CLI from TestPyPi. Run this command in the terminal.

.. code-block:: bash

    pip install -i https://test.pypi.org/simple/ dds-cli

.. note::
    
    This is **not** the same command as shown in the installation guide.
    
    You can install the released version of the CLI by following the installation guide, however you will not have the latest version or any of the features that are currently being implemented. There may also be unexpected errors since the released CLI and the DDS test instance may not be completely compatible.

.. _test-config:

4. How to configure the test version of the CLI
==================================================

After installing the CLI, you need to complete the following steps before you can start using it: 

1. Set the CLI to point to the test instance by running the following command in the terminal / command prompt / PowerShell (depending on your OS, see below)

    .. code-block:: bash
        
        # Linux / MacOS
        export DDS_CLI_ENV="test-instance"

        # Windows Command Prompt
        set DDS_CLI_ENV=test-instance

        # Windows PowerShell
        $env:DDS_CLI_ENV = 'test-instance'

2. Verify that the output of the following command contains ``https://dds-dev.dckube3.scilifelab.se/`` and **not** ``https://delivery.scilifelab.se/``

    .. code-block:: bash
        
        dds --version


Experiencing issues? Contact us!
==================================

Email us at delivery@scilifelab.se if you need help or have any questions or feature requests. Start the email subject with ``DDS Testing``.  