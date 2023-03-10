Changelog
==========

.. _2.2.63:

2.2.63 - 2023-02-13
~~~~~~~~~~~~~~~~~~~~

- Added this version changelog to the documentation.
- Reduced debug-level logging.
- Fixed bugs:
    - Errors during upload makes client return exit code 1.
    - UnicodeEncodeError is caught and displays an understandable message if an invalid special character is used during authentication. **Note** that the original issue lies in that the registration allows the 'invalid' characters; This is being fixed on the API side as we speak.
- Clarified error / warning messages printed out after upload issues: The ``dds_failed_delivery.json`` file should be created and should not be deleted.

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