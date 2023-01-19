.. Information for users which have been invited to the development / test instance of the DDS.

======================
The DDS Test instance
======================

.. admonition:: Target audience 

    This page targets any users invited to the development / testing instance of the Data Delivery System. If you have an account on the production instead (https://delivery.scilifelab.se), please read the documentation at https://scilifelabdatacentre.github.io/dds_cli/.

Hi, welcome, and thank you for your interest in testing the Data Delivery System. This page will give you information on: 

.. contents::
   :local:

.. _test-where:

1. Where the DDS Test Instance is located
============================================

* https://dds-dev.dckube.scilifelab.se/
*  you can also find the documentation (containing installation instructions etc etc), technical overview and troubleshooting guide.

.. _test-install:

2. How to install the test version of the CLI
================================================

* Only available with pip
* Local or rackham - should be able to install with the same command 
* Not the same command as in the documentation
* pip install -i https://test.pypi.org/simple/ dds-cli

.. _test-config:

3. How to configure the test version of the CLI
==================================================

* When using the DDS test instance, you'll need to first run export DDS_CLI_ENV="test-instance"  in the terminal, and then verify with dds --version  that it says the following (this is very important).

.. _test-important:

4. Important information before starting
==========================================

* First and foremost, *no sensitive data* is allowed to be delivered within this test instance. 
* Create projects 
    * unit admin / Personnel
    * at least two unit admins 
* When listing your projects you will see your projects, and yours only. However, in order to not create a large number of separate storage locations for testing purposes, the actual storage location is shared by all units in the test setup. Since the data is always encrypted and another unit would need to hack the DDS and also crack the encryption, there should be no risk of anyone else accessing your data. In the production instance, there's always a separate storage location per unit.
* The storage quota for the testing is currently set to 5 TB. This is a total volume for all units using the test instance. However, if you receive and error message indicating that the quota is met, contact delivery@scilifelab.se and we will solve this for you. 
* Within the test instance of the DDS, all units get the following settings:
    * ``days_in_available``: 7 days. 
    
        This means that, when data has been uploaded to a project, and the data has been released (the project status has been set to "Available"), the data will be available for download for 7 days. After this, the project will automatically transition to the status "Expired"

    * ``days_in_expired``: 3 days

        This means that when a project has transitioned to the status "Expired", the project data will be kept for 3 days. During this time you can release the project data again (checkout the `dds project status` command) and transition the status to "Available" again. If you do not, your project will be automatically archived (project status will be changed to "Archived"), and your data will be permanently deleted.

    .. note:: 

        * These statuses are described in the technical overview, located on the DDS test web page mentioned above.
        * The short number of days is only for the test instance, making it easier for you to test that the statuses work as they should.

* Keep in mind that the test instance is where we try out new features etc. Therefore, there may be some unexpected redeployments and there may be bugs in new features.
