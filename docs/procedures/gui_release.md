# DDS GUI Release Procedure

## Overview
The graphical interface (GUI) follows the same release rhythm as the CLI. Releasing a new version involves preparing the version and changelog, building cross‑platform executables, and attaching the binaries to a GitHub release.

## Pre-release checklist
1. **Announce the upcoming release** at least a week in advance (e.g. via "Message of the Day" and Slack).
2. **Review the automatic release draft** created after merges to `dev` or `master` and ensure the suggested version is correct.
3. **Branch for the new version** from `dev` and update `dds_cli/version.py` and `CHANGELOG.rst`.
4. **Run documentation/image generation (`rich-codex`)** and re‑sign commits if needed. Open a PR `new-version_*` → `dev` and verify assets.
5. **Merge to `master` and publish the release draft** after a brief review, similar to the CLI procedure.

## Building the GUI executable
- The helper script installs dependencies and invokes PyInstaller with required hidden imports to create a standalone binary.
- The standalone entry point launches the `DDSApp` GUI.

### Cross-platform build commands
The existing CI workflow builds GUI binaries for macOS, Linux and Windows using PyInstaller; each command includes hidden imports for `textual.widgets._tab_pane` and `cgi` to ensure the GUI works across platforms. For Windows, the workflow installs `windows-curses` before running PyInstaller.

## Release workflow
1. **Adapt the existing `gui-executable` workflow** to trigger on `release.published`, mirroring the CLI's `release-cli.yml`.
2. **Within the workflow**:
   - Check out the source and build the wheel (`setup.py sdist bdist_wheel`).
   - For each OS matrix entry (macOS, Ubuntu, Windows), install dependencies and run the appropriate PyInstaller command.
   - Test each artifact (e.g. `./dist/dds_gui_* --version`).
   - Upload the executables as GitHub release assets.
3. **Optionally package the GUI** for distribution channels used by the CLI (e.g. attach a PDF manual if appropriate).

## Post-release
- Inform users and relevant infrastructure teams of the new GUI release, matching the notification steps used for CLI releases.
- Monitor downloads and user feedback.

