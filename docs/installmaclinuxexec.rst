:orphan:

.. _installation_mac_linux_exec:

MacOS / Linux executable
========================

1. Download the executable from the GitHub release page:

   * Executable for Linux (Ubuntu latest): `Download Linux Executable <https://github.com/ScilifelabDataCentre/dds_cli/releases/latest/download/dds_cli_ubuntu-latest_x86_64>`_

      You can find executables for other versions on the GitHub releases page linked at the top of this page.

   * Executable for MacOS: `Download MacOS Executable <https://github.com/ScilifelabDataCentre/dds_cli/releases/latest/download/dds_cli_macos_arm64>`_

2. Open the terminal, go to the directory where the downloaded file is located, and make the file executable by running the following command:

   * On Linux:

      .. code-block:: bash

         $ chmod +x dds_cli_ubuntu_x86_64

   * On MacOS:

      .. code-block:: bash

         $ chmod +x dds_cli_macos_arm64

3. Test that the ``dds-cli`` command works by running the following:

   .. code-block:: bash

      $ ./<name-of-executable-file>

   **Example:**

   .. image:: ../img/mac-executable-help.svg


   .. admonition:: Information to MacOS users

      On MacOS, you may need to allow your Mac to trust the software. Please, refer to the following sources for more information: https://support.apple.com/en-us/HT202491 and https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unidentified-developer-mh40616/mac

4. When reading through the rest of the documentation and running the commands, replace ``dds`` with the path to the executable. For example:

   .. code-block:: bash

      $ ./dds_cli_macos_arm64 auth login
      $ ./dds_cli_macos_arm64 user info
      $ ./dds_cli_macos_arm64 ls
      ...


