.. _windows:

======================================
How to install the DDS CLI on Windows
======================================

1. Download and install Python > 3.7
======================================

a. Go to https://www.python.org/downloads/windows/

.. image:: _static/windows/python_install.png
    :align: center

b. In the left column, locate the **Windows installer** of a suitable version e.g. the **Python 3.9.10 - Jan. 14, 2022** release and download the associated .exe file. 

.. image:: _static/windows/python_exe.png
    :align: center

.. note:: 

    For most systems, the `Windows installer (64-bit) <https://www.python.org/ftp/python/3.9.10/python-3.9.10-amd64.exe>`_ will be the correct version. If your computer is older than a decade, chances are that you might need to select *32-bit binary* or a slightly older version of Python.  

c. Click the downloaded **python-3.9.10-amd64.exe**. This will open the Python Installer.

.. image:: _static/windows/python_install-0.png
    :align: center

d. Make sure the **Add Python 3.9 to PATH** box is checked and proceed with the installation.

.. image:: _static/windows/python_install-1.png
    :align: center

.. image:: _static/windows/python_install-2.png
    :align: center

.. note:: 
    
    For most users, the default installation options will work. On a shared or office computer, you might need to uncheck the Install launcher for all users, if you lack administrative privileges on the system. To do so, select the Customize installation option.

e. Click **Install Now** and follow the installer steps. You should be able to click next/continue on all steps. Python will be installed.

.. image:: _static/windows/python_install-3.png
    :align: center

.. image:: _static/windows/python_install-5.png
    :align: center

2. Proceed with a command line application / terminal
=======================================================

a. From the start menu, launch the default command line application cmd or any other like the PowerShell. 

.. image:: _static/windows/powershell_top-0.png
    :align: center

b. Verify that Python was installed successfully:

.. image:: _static/windows/powershell_top-1.png
    :align: center

.. note:: 
    
    Upon entering ``python --version``  the version of the previously installed Python distribution should be shown. If a version number < 3.7 is shown or Python is not found, please consult the :ref:`Troubleshooting<troubleshooting>` section below.

c. Python ships with a helper program called **pip** to install additional packages. In the next step, this software should be upgraded to its current version. 

.. image:: _static/windows/powershell-4.png
    :align: center

To upgrade pip, enter the command **python -m pip install --upgrade pip** to the terminal. 

d. After pip was successfully upgraded, the Data Delivery System Command Line Interface can be installed:

.. image:: _static/windows/powershell_top-7.png
    :align: center
    
Enter **python -m pip install dds_cli** to start the install. Because several requirements will be automatically installed with the command line interface, several packages will be automatically downloaded:

.. image:: _static/windows/powershell-9.png
    :align: center

e. After the installation procedure has completed, the Data Delivery System Command Line Interface can be launched from the command line by entering **dds**. Please consult the general manual, how to interact with the CLI. 

.. image:: _static/windows/powershell_top-10.png
    :align: center

.. _troubleshooting:

3. Troubleshooting
====================

a. **Python not found or only in a wrong version.**

The most likely reason for this is an issue with the PATH variable, e.g. when the box Add Python 3.9 to Path was not checked during installation.

This can be manually checked and corrected via the Environment Variables. 

.. image:: _static/windows/path-0.png
    :align: center

.. image:: _static/windows/path-1.png
    :align: center

Open the Environment Variables dialogue via the **Advanced** Tab in the **System Properties**. 

.. image:: _static/windows/path-2.png
    :align: center

Select **Path** from the list of variables and click edit. Mind that there is a set of variables specific to the user on the top and a system-wide set of variables at the bottom. Both contain a **Path** and depending on the mode of installation, Python might be added to both or just one of them. 

.. image:: _static/windows/path-4.png
    :align: center

Verify that the directories associated with the installation are present in the Path. If not, add the respective directories manually. 

Use the search function first to verify where the Python installation has been added.  Typically, all installation paths will contain your username and thus need to be customized. Change the paths shown in the example to: `C:\User\username\AppData ….`

b. **Security privileges required.**

It may be possible, that you will need to approve changes to your system explicitly during the install:

.. image:: _static/windows/windows_security.png
    :align: center

.. image:: _static/windows/python_install-4.png
    :align: center

In the latter case - depending on the installation directory - the combined length of all directories in PATH may exceed the length limit. Extending the allowed length should not negatively impact your system.
