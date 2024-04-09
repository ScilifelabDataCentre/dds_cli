Changelog
==========

.. _2.6.4:

2.6.4 - 2024-04-09
~~~~~~~~~~~~~~~~~~~

- Dependencies: 
    - `jwcrypto` from `1.5.1` to `1.5.6`

.. _2.6.3:

2.6.3 - 2023-02-27
~~~~~~~~~~~~~~~~~~~

- Dependencies: 
    - `Criptography` from `41.0.6` to `42.0.4`

.. _2.6.2:

2.6.2 - 2023-02-13
~~~~~~~~~~~~~~~~~~~

- Dependencies:
    - `jwcrypto` from `1.4.2` to `1.5.1`

.. _2.6.1:

2.6.1 - 2023-12-20
~~~~~~~~~~~~~~~~~~~

- Dependencies:
    - `cryptography` from `41.0.3` to `41.0.6`

.. _2.6.0:

2.6.0 - 2023-10-25
~~~~~~~~~~~~~~~~~~~

- `dds data put` updated: If files uploaded successfully, but there are issues with saving the info to the database, the system performs a final bulk attempt.

.. _2.5.2:

2.5.2 - 2023-10-25
~~~~~~~~~~~~~~~~~~~

- Updated command: `dds project status delete/archive` now prints project information and asks for confirmation from user.
- "Checksum verification successful" is not printed when file integrity is verified (unless `-v` option is used); Only prints if there is an error.
- New command `dds project status extend`: Unit Admins / Personnel can extend the project deadline prior to the project expiring.

.. _2.5.1:

2.5.1 - 2023-09-25
~~~~~~~~~~~~~~~~~~~

- Super Admins only:
    - New command: `dds maintenance status` to check if maintenance mode is on or off
    - Updated command: `dds stats` now prints two separate tables with the stats collected from the API
- Dependencies: 
    - `requests` from `2.28.1` to `2.31.0`
- Documentation:
    - Generation of PDF format fixed

.. _2.5.0:

2.5.0 - 2023-08-29
~~~~~~~~~~~~~~~~~~

- Dependencies:
    - `cryptography` from `38.0.3` to `41.0.3`
        - Removed use of `peer_public_key` keyword argument in `exchange` (generation of shared key)
    - `PyYAML` from `6.0` to `6.0.1`
    - `Werkzeug` (tests) from `2.1.2` to `2.2.3`
- New message when invalid response from API
- **BACKWARDS INCOMPATIBLE (will return 404):** New option in command `dds user ls`:  `--save-emails`. Only available to Super Admins to allow them to easily email users with account roles 'Unit Admin' and 'Unit Personnel'.

.. _2.2.65:

2.2.65 - 2023-05-26
~~~~~~~~~~~~~~~~~~~~

- New URL for the testing instance: https://dds-dev.dckube3.scilifelab.se/api/v1

.. _2.2.64:

2.2.64 - 2023-04-26
~~~~~~~~~~~~~~~~~~~~

- New command for checking a few statistics in the DDS.
- Removed debug-level logging.
- New documentation:
    - How to set environment variables in Windows.
    - Recommendations regarding password management.

.. _2.2.63:

2.2.63 - 2023-03-13
~~~~~~~~~~~~~~~~~~~~

- Added this version changelog to the documentation.
- Reduced debug-level logging.
- Fixed bugs:
    - Errors during upload makes client return exit code 1.
    - UnicodeEncodeError is caught and displays an understandable message if an invalid special character is used during authentication. **Note** that the original issue lies in that the registration allows the 'invalid' characters; This is being fixed on the API side as we speak.
- Clarified error / warning messages printed out after upload issues: The ``dds_failed_delivery.json`` file should not be deleted.

.. _2.2.62:

2.2.62 - 2023-02-10
~~~~~~~~~~~~~~~~~~~~~

- Fixed an error in generation of executable for Windows.

.. _2.2.61:

2.2.61 - 2023-02-10
~~~~~~~~~~~~~~~~~~~~

- New executable for Ubuntu 20.04. Latest Ubuntu is 22.04.
- Updated security scanning.

.. _2.2.6:

2.2.6 - 2023-02-01
~~~~~~~~~~~~~~~~~~~~

- Add security scanning of code. 
- Publish CLI to TestPyPi during development: `dds-cli <https://test.pypi.org/project/dds-cli/>`_
- Added `new instructions <https://scilifelabdatacentre.github.io/dds_cli/testing/>`_ for testing instance of the DDS.

.. _2.2.5:

2.2.5 - 2023-01-05
~~~~~~~~~~~~~~~~~~~~

- Updated documentation and added examples.

.. _2.2.4:

2.2.4 - 2022-12-15
~~~~~~~~~~~~~~~~~~~~

- **Vulnerability:** ``jwcrypto`` bumped from ``1.4`` to ``1.4.2``
- Changed command: ``dds project info`` to ``dds project info display``
- New command to allow changes to project title, description and PI: ``dds project info change``.

.. _2.2.3:

2.2.3 - 2022-11-29
~~~~~~~~~~~~~~~~~~~

- Fixed bug (Windows): Backslashes were causing issues with listing and downloading project contents.

.. _2.2.2:

2.2.2 - 2022-11-17
~~~~~~~~~~~~~~~~~~~

- New ``--destination`` option for upload command: ``dds data put --destination [destination]`` will upload data to remote directory called "[destination]"
- New command for displaying project information: ``dds project info``
- Fixed bug: Requests taking too long and timing out should display an understandable message.
- Added check in download command: User must use either ``--get-all`` to download all project contents or ``--source`` to specify specific data paths. 
- **Vulnerability:** ``cryptography`` bumped from ``38.0.1`` to ``38.0.3``.
- Clarified "How do I get my user account" section in documentation.
- Included automatically generated code examples by ``rich-codex``

.. _earlier-versions:

Earlier versions
~~~~~~~~~~~~~~~~~

Please see `the release page on GitHub <https://github.com/ScilifelabDataCentre/dds_cli/releases>`_ for detailed information about the changes in each release.
