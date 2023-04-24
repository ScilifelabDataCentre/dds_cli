.. Information about how to securely store passwords

.. _password:

=================================
Securing your password
=================================

Your Data Delivery System (DDS) password will be used to protect your data from any unauthorized parties. Choosing a secure password is therefore essential since the password's complexity will determine how easy it is to guess the password and thereby gain access to your data. Remembering a number of different passwords for different services can be difficult, and many people resort to using the same or similar password for all, or saving them in insecure ways where they are easily lost or/and read by others.

Due to this, we highly recommend that you use a password manager to store your passwords. An example of this is `Bitwarden <https://bitwarden.com/>`_ which is also used by the SciLifeLab Data Centre team. 

How to use password managers, e.g. Bitwarden
=============================================

Using a password manager such as Bitwarden means that you need to keep track of a single password: Your password to the password manager. The rest are stored within the password manager, allowing you to have different complex ones for each service you use. Many of these tools have mobile apps and plugins for different browsers, which simplifies password management significantly. 

The following is an example of how to start using Bitwarden. 

1. Go to https://bitwarden.com/ 
2. Create an account. At the time of writing, this is done by clicking ``Get Started`` in the top right corner. Fill in your information and click Create account at the bottom. Remember to choose a complex password, that you can remember. Do not share this password with anyone.
3. Log in to Bitwarden: https://vault.bitwarden.com/#/login. 
4. Fill in the login information for the DDS and click ``Save`` 
    
    =========================== ================
    Field                       What to fill in
    =========================== ================
    What type of item is this?  Login
    Name                        SciLifeLab Data Delivery System
    Username                    *Your DDS username*
    Password                    *Your chosen DDS password or use the circle symbol to generate a secure enough password while registering for your DDS account*
    URI                         https://delivery.scilifelab.se/
    =========================== ================

5. When you want to log into the DDS - either with the command line interface or via the browser:
    
    1. Log in to Bitwarden
    2. Search your vault for “Data Delivery System”, your login item should show up in a list.
    3. Click the three dots on the side of the item and then ``Copy password``.
    4. Paste it in the password field where your are attempting to log in to the DDS. Remember that passwords are not visible in the command line interface; You will not be able to see if you have pasted or written it correctly.

What happens if I forget my DDS password?
==========================================

The DDS **does not** store the passwords in plain text; We **cannot see** what your password is or change it for you. 

If you have forgotten your password, you will need to reset it. Resetting the password will remove your access from all delivery projects within the system. If you’re interested in the details behind this, please read the information box in section ``2.6. Creating a Project`` in the `Technical Overview <https://delivery.scilifelab.se/technical>`_

The data **is not** deleted when you loose access to the data. The data is encrypted with a combination of encryption keys, and you will have lost access to use those keys. However, your access can be renewed:

======================= =============================================================================================================================================== ==============================================================================
Role                    What happens at password reset?                                                                                                                 What do I do? 
======================= =============================================================================================================================================== ==============================================================================
Researcher              Lost access to all data in the delivery projects that have been shared with you by one or more SciLifeLab units; You cannot download any data.  Contact all the units delivering your data and ask them to renew your access.
Unit Admin / Personnel  Lost access to all delivery projects that your unit has created.                                                                                Contact a Unit Personnel or Unit Admin. Note that the user can only renew your access to projects that they have access to themselves.
======================= =============================================================================================================================================== ==============================================================================
