.. _web:

=======================
How to test the DDS web
=======================

The DDS web interface is currently very minimal. This will be improved on later. At this time the available functionalities within the web interface are

1. Register account
2. Login
3. MFA Authentication
4. Reset forgotten password
5. Change password

Steps
~~~~~~~ 

1. Register an account
""""""""""""""""""""""""
When another user invites you to the DDS, you will get an email (currently from the email *dsw@scilifelab.se*). To test the registration functionality, we suggest that you perform the following steps.

1.1. Go to your email inbox and open the email with a subject with the structure: "<Unit name> invites you to the SciLifeLab Data Delivery System". The email contents should look something like this:

    .. image:: _static/invite.png
        :align: center

1.2. Click on the **Sign Up** button. You should reach the *Registration* page. 

    If you have been invited to the DDS as a Researcher, the registration page should look something like this: 

    .. image:: _static/registration_researcher.png
        :align: center
    
    If you have invited to the DDS as a Unit Admin or Personnel, the registration page should look something like this:

    .. image:: _static/registration_unit.png
        :align: center

    1.2.1. Fill in your information. You cannot choose a different email than the one you got the invitation email to (but try it out), and the `Unit` field (if visible) cannot be changed. 

        * Fill in your full name. 
        * Try to choose a username shorter than 8 and one longer than 20 characters.
            
            .. admonition:: Expected result

                An error message should be displayed, notifying you that the username is required to be between 8 and 20 characters long. 

        * Try to choose an invalid password:
            - Less than 10 characters
            - With only upper case letters
            - With only lower case letters

            .. admonition:: Expected result

                A message should be displayed, notifying you that the password needs to meet the following requirements:
                
                - At least 10 characters
                - At most 64 characters
                - Contain at least one digit OR a special character
                - Contain at least one lower case letter
                - Contain at least one upper case letter
       
1.3. Finally, fill in valid information and create an account. You should be redirected to the following page:

    .. image:: _static/registration_completed.png
        :align: center


1. Login
""""""""""

2.1. Go to https://delivery.scilifelab.se/. You should see the following page.

    .. image:: _static/login.png
        :align: center

2.2. Attempt to log in with

    * Incorrect username
    * Incorrect password
    * Correct username and password 

    .. admonition:: Expected result

        When the username and/or password is correct, a message should be displayed notifying you of the specific error. 


1. MFA Authentication
""""""""""""""""""""""
3.1. When filling in the correct user credentials and clicking `Login`, you should be met with the following page:

    .. image:: _static/hotp.png
        :align: center

3.2. Go to your email inbox and open the email with the subject line "DDS One-Time Authentication Code". The email should contain a 8-digit code.

    3.2.1. Go back to the DDS page and try to input 

        * An incorrect value for the one-time code. You can try one that is not 8 characters and one that is simply incorrect.
        * The correct code that you received in the email

        .. admonition:: Expected result

            If the code is invalid, an understandable message should be displayed.

    3.2.2. When inputting the correct one-time code, you should be redirected to a very simple page with a logout button, and a link with the text "Change Password".

1. Change Password
""""""""""""""""""""
4.1. Log in to the DDS web interface and click on the "Change Password" link. You should be redirected to the following page:

    .. image:: _static/password_change.png
        :align: center

4.2. Attempt to change password with

    * The incorrect current password 
    * Invalid new password and non-matching fields
    * Correct current password and valid new password

4.3. The following message should be displayed after successfully changing your password:

    .. image:: _static/password_change_success.png
        :align: center
  

1. Reset forgotten password
"""""""""""""""""""""""""""""
5.1. Go to https://delivery.scilifelab.se/ and click on "Forgot Password?". You should be redirected to the following page:

    .. image:: _static/password_forgot.png
        :align: center

5.2. Fill in your email address and click on the "Request Password Reset" button. Only the used when registering should work. The following message should be displayed:

    .. image:: _static/password_forgot_email.png
        :align: center

5.3. Go to your email inbox (or spam if you cannot find it in inbox) and open the email with the subject line "WARNING! Password Reset Request for SciLifeLab Data Delivery System". **Read the information in the email.** 

5.4. Click the "Reset Password" button in the email. The following page should open:
    
    .. image:: _static/password_reset.png
        :align: center

5.5. Fill in a new password. Test both invalid and valid passwords, as in section 1. and 2. above. 

5.6. When submitting the form, you should be redirected to the following page:

    .. image:: _static/password_reset_success.png
        :align: center






