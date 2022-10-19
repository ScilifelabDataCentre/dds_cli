# Changelog

Please add a _short_ line describing the PR you make, if the PR implements a specific feature or functionality, or refactor. Not needed if you add very small and unnoticable changes. Not needed when PR includes _only_ tests for already existing feature.

## Sprint (2021-08-11 - 2021-08-25)

- Progress bar glitch fixed by creating console object in utils.py ([#130](https://github.com/ScilifelabDataCentre/dds_cli/pull/130))
- Log messages about successful checksum verification ([#131](https://github.com/ScilifelabDataCentre/dds_cli/pull/131))
- Removed reduntant message in `dds ls` ([#132](https://github.com/ScilifelabDataCentre/dds_cli/pull/132))
- Pagination of tables if too long ([#133](https://github.com/ScilifelabDataCentre/dds_cli/pull/133))
- Warning about non existent files when using `--source-path-file` option in `dds put` ([#134](https://github.com/ScilifelabDataCentre/dds_cli/pull/134))
- `--tree` option for `dds ls` - display whole file tree ([#136](https://github.com/ScilifelabDataCentre/dds_cli/pull/136))

## Sprint (2021-08-25 - 2021-09-08)

- Custom exceptions and code cleanup ([#143](https://github.com/ScilifelabDataCentre/dds_cli/pull/143))

## Sprint (2021-09-08 - 2021-09-22)

- Install `pytest` in github action ([#151](https://github.com/ScilifelabDataCentre/dds_cli/pull/151))
- `method` moved to base class ([#152](https://github.com/ScilifelabDataCentre/dds_cli/pull/152))
- Module used in testing ([#154](https://github.com/ScilifelabDataCentre/dds_cli/pull/154))
- Make error message readable ([#155](https://github.com/ScilifelabDataCentre/dds_cli/pull/155))
- Changed CLI to match the new authentication in the API ([#156](https://github.com/ScilifelabDataCentre/dds_cli/pull/156))

## Sprint (2021-09-22 - 2021-10-06)

- Added detection of Windows legacy versions ([#159](https://github.com/ScilifelabDataCentre/dds_cli/pull/159))
- Removed tests involving requests ([#166](https://github.com/ScilifelabDataCentre/dds_cli/pull/166))

## Sprint (2021-10-06 - 2021-10-20)

- Tests removed ([#169](https://github.com/ScilifelabDataCentre/dds_cli/pull/169))
- Project creation functionality ([#167](https://github.com/ScilifelabDataCentre/dds_cli/pull/167))
- `--is-sensitive` option added to project creation ([#171](https://github.com/ScilifelabDataCentre/dds_cli/pull/171))
- Changes to match the web changes regarding user inheritance and roles: [#627](https://github.com/ScilifelabDataCentre/dds_web/pull/627) ([#172](https://github.com/ScilifelabDataCentre/dds_cli/pull/172))
- Errors during upload logged directly instead of waiting for clean up at the end ([#173](https://github.com/ScilifelabDataCentre/dds_cli/pull/173))
- Changed from `resolve` to `abspath` ([#175](https://github.com/ScilifelabDataCentre/dds_cli/pull/175))
- Option to display users involved in projects: `dds ls --users` ([#174](https://github.com/ScilifelabDataCentre/dds_cli/pull/174))
- `invite` command ([#158](https://github.com/ScilifelabDataCentre/dds_cli/pull/158))

## Sprint (2021-10-20 - 2021-11-03)

- Refactoring of `dds rm` ([#179](https://github.com/ScilifelabDataCentre/dds_cli/pull/179))
- Formatting of the project lists moved to the CLI ([#184](https://github.com/ScilifelabDataCentre/dds_cli/pull/184))
- Removed the update of the project size after upload ([#185](https://github.com/ScilifelabDataCentre/dds_cli/pull/185))

## Sprint (2021-11-03 - 2021-11-17)

- Bug fix regarding usage values ([#189](https://github.com/ScilifelabDataCentre/dds_cli/pull/189))
- Functionality to associate users with projects ([#186](https://github.com/ScilifelabDataCentre/dds_cli/pull/186))
- Config option removed ([#190](https://github.com/ScilifelabDataCentre/dds_cli/pull/190))
- `expanduser` added since `os.path.abspath` does not expand the `~` symbol ([#191](https://github.com/ScilifelabDataCentre/dds_cli/pull/191))
- Save encrypted token after authentication and use for subsequent commands([#193](https://github.com/ScilifelabDataCentre/dds_cli/pull/193))

## Sprint (2021-11-17 - 2021-12-01)

- Username not required since sessions used ([#195](https://github.com/ScilifelabDataCentre/dds_cli/pull/195))
- Color in `pytest` ([#197](https://github.com/ScilifelabDataCentre/dds_cli/pull/197))
- Filename displayed in bucket replaced by UUID ([#196](https://github.com/ScilifelabDataCentre/dds_cli/pull/196))
- `--no-prompt` flag, `Session`->`Auth`, new `auth` subcommands: `login`, `logout`, `info` ([#198](https://github.com/ScilifelabDataCentre/dds_cli/pull/198))
- Tests for adding users and listing projects/files ([#199](https://github.com/ScilifelabDataCentre/dds_cli/pull/199))
- `--json` flag to `dds ls` to output list of project as json format ([#201](https://github.com/ScilifelabDataCentre/dds_cli/pull/201))

## Sprint (2021-12-01 - 2021-12-15)

- `sphinx` for automatic generation of documentation ([#202](https://github.com/ScilifelabDataCentre/dds_cli/pull/202))
- `status` command ([#204](https://github.com/ScilifelabDataCentre/dds_cli/pull/204))
- Removed all occurrences of `os.umask` ([#206](https://github.com/ScilifelabDataCentre/dds_cli/pull/206))
- Changed logging level back to `INFO` and output progress bars to stderr ([#207](https://github.com/ScilifelabDataCentre/dds_cli/pull/209))
- Changed download procedure from `boto3` to `requests` to handle presigned urls ([#203](https://github.com/ScilifelabDataCentre/dds_cli/pull/203))

## Sprint (2021-12-15 - 2021-12-29) _Christmas_

- Updated token expiration information ([#209](https://github.com/ScilifelabDataCentre/dds_cli/pull/209))
- Group command `user` ([#200](https://github.com/ScilifelabDataCentre/dds_cli/pull/200))
- `project` command and subcommands `grant`&`revoke` ([#210](https://github.com/ScilifelabDataCentre/dds_cli/pull/210))

## Sprint (2021-12-29 - 2022-01-12)

- Grouped commands into `auth`, `user`, `project` and `data`. Created common options and arguments. ([#213](https://github.com/ScilifelabDataCentre/dds_cli/pull/213))
- Command for displaying user info ([#214](https://github.com/ScilifelabDataCentre/dds_cli/pull/214))

## Sprint (2022-01-12 - 2022-01-26)

- Timestamps converted to local timezone when displaying ([#217](https://github.com/ScilifelabDataCentre/dds_cli/pull/217))
- Project ID always sent in request as `param` - consistency changes ([#220](https://github.com/ScilifelabDataCentre/dds_cli/pull/220))

## Sprint (2022-01-26 - 2022-02-09)

- File paths replaced by UUID to prevent sensitive information in Safespring storage ([#225](https://github.com/ScilifelabDataCentre/dds_cli/pull/225))
- Commands to activate and deactivate users ([#226](https://github.com/ScilifelabDataCentre/dds_cli/pull/226))
- Authentication with HOTP ([#222](https://github.com/ScilifelabDataCentre/dds_cli/pull/222))
- Handling of `ApiResponseError` to avoid huge error printout ([#228](https://github.com/ScilifelabDataCentre/dds_cli/pull/228))

## Sprint (2022-02-09 - 2022-02-23)

- Add `dds project access fix` command for reseting user access when reset password ([#236](https://github.com/ScilifelabDataCentre/dds_cli/pull/236))
- Save failed files to log and print out help message after ([#237](https://github.com/ScilifelabDataCentre/dds_cli/pull/237))
- Change `--is_sensitive` to `--non-sensitive` ([#246](https://github.com/ScilifelabDataCentre/dds_cli/pull/246))
- Display logged in user in header ([#244](https://github.com/ScilifelabDataCentre/dds_cli/pull/244))
- Updated token expiration information ([#245](https://github.com/scilifelabdatacentre/dds_cli/issues/245))

## Sprint (2022-02-23 - 2022-03-09)

- Introduced a `--no-mail` flag in the CLI respectively a `send_email: True/False` json parameter to fix [issue 924](https://github.com/scilifelabdatacentre/dds_web/issues/924) ([#253](https://github.com/ScilifelabDataCentre/dds_cli/pull/253))
- Added documentation and test protocol ([#252](https://github.com/ScilifelabDataCentre/dds_cli/pull/252))
- Temporary unit option when adding user ([#261](https://github.com/ScilifelabDataCentre/dds_cli/pull/261))
- Added windows docs (by Matthias Zepper) ([#276](https://github.com/ScilifelabDataCentre/dds_cli/pull/276))
- Removed pinned package versions and bumped rick-click, should work for Python 3.7 up to 3.10 ([#288](https://github.com/ScilifelabDataCentre/dds_cli/pull/288))
- Remove local token when requesting deletion of own account ([297](https://github.com/ScilifelabDataCentre/dds_cli/pull/297)/[303](https://github.com/ScilifelabDataCentre/dds_cli/pull/303))
- Add Role when listing project users ([#316](https://github.com/ScilifelabDataCentre/dds_cli/pull/316))
- Pin rich-click `>=1.2.1` to solve exception handling errors ([#327](https://github.com/ScilifelabDataCentre/dds_cli/pull/327))
- Add a `--token-path` argument to tell where the token should be saved and which token to be used. ([#329](https://github.com/ScilifelabDataCentre/dds_cli/pull/329))
- Remove `--username` option ([#331](https://github.com/ScilifelabDataCentre/dds_cli/pull/331))
- Add support for the zero-conf environment in dds_web ([#337](https://github.com/ScilifelabDataCentre/dds_cli/pull/337))
- Increase request timeout to 30 ([#344](https://github.com/ScilifelabDataCentre/dds_cli/pull/344))
- Make sure "already uploaded" does not give an error output ([#341](https://github.com/ScilifelabDataCentre/dds_cli/pull/341))
- URL in the logo changing with DDS_CLI_ENV ([#349](https://github.com/ScilifelabDataCentre/dds_cli/pull/349))
- Show message "Any users with errors were not added to the project" when emails failed to validate during project creation ([#356](https://github.com/ScilifelabDataCentre/dds_cli/pull/356))
- Ask user confirmation for project abort, archive and delete([#357](https://github.com/ScilifelabDataCentre/dds_cli/pull/357))
- Replaced the default help messages of Click for the `--version` and `--help` options as requested in [issue 338](https://github.com/scilifelabdatacentre/dds_web/issues/338).
- Explicit error message for `--destination` when the path exists ([#371](https://github.com/ScilifelabDataCentre/dds_cli/pull/371))
- Escape variables that are printed in the cli (avoiding e.g. hidden text and bad coloring) ([#364](https://github.com/ScilifelabDataCentre/dds_cli/pull/364))

## Sprint (2022-03-09 - 2022-03-23)

- New `dds user ls` command for listing unit users ([#384](https://github.com/ScilifelabDataCentre/dds_cli/pull/384))
- When using `dds project access fix`, list the projects which where not possible to update access in ([#379](https://github.com/ScilifelabDataCentre/dds_cli/pull/379))
- Add `Access` column to show user if they have access or not ([#383](https://github.com/ScilifelabDataCentre/dds_cli/pull/383))
- New `--mount-dir` option for `dds data put` where the `DataDelivery...` folders will be created if specified ([#393](https://github.com/ScilifelabDataCentre/dds_cli/pull/393))
- File permission fixing for the token on Windows ([#395](https://github.com/ScilifelabDataCentre/dds_cli/pull/395))
- New unit group command unit module ([#398](https://github.com/ScilifelabDataCentre/dds_cli/pull/398))
- `--unit` option for Super Admins to list unit users ([#397](https://github.com/ScilifelabDataCentre/dds_cli/pull/397))
- Removed `dds project status abort` and added `--abort` flag to `dds project status archive` ([#404](https://github.com/ScilifelabDataCentre/dds_cli/pull/404))
- Delete temporary folder before `DownloadError` and `UploadError` ([#407](https://github.com/ScilifelabDataCentre/dds_cli/pull/407)).
- Allow delete of both folder and files ([#411](https://github.com/ScilifelabDataCentre/dds_cli/pull/411))
- Report number of files deleted for "rm folder" ([#408](https://github.com/ScilifelabDataCentre/dds_cli/pull/408))
- Change log to correct json ([#426](https://github.com/ScilifelabDataCentre/dds_cli/pull/426))
- `--is-invite` option in `dds user delete` to allow delete of invites (temporary) ([#415](https://github.com/ScilifelabDataCentre/dds_cli/pull/415))
- Github Action to automatically build the executables (with help from @zishanmirza) and the documentations with Sphinx.([#419](https://github.com/ScilifelabDataCentre/dds_cli/pull/419),[#423](https://github.com/ScilifelabDataCentre/dds_cli/pull/423))
- Github Action to automatically deploy the documentation to Github Pages. ([#436](https://github.com/ScilifelabDataCentre/dds_cli/pull/436))
- Refactor version handling to allow PyInstaller builds. ([#439](https://github.com/ScilifelabDataCentre/dds_cli/pull/439))

## Sprint (2022-03-23 - 2022-04-06)

- Patch: Add a message when the project access would be fixed for a user. ([#446](https://github.com/ScilifelabDataCentre/dds_cli/pull/446))

## Sprint (2022-04-06 - 2022-04-20)

- `motd` command to add new message of the day via new endpoint ([#449](https://github.com/ScilifelabDataCentre/dds_cli/pull/449))
- Patch: Message in docstrings to urge users to reauthenticate before upload and download ([#450](https://github.com/ScilifelabDataCentre/dds_cli/pull/450))
- Pin versions in `requirements-dev.txt`: New version of `sphinx-click` makes `:nested: full` not work anymore (direct commit: https://github.com/ScilifelabDataCentre/dds_cli/commit/b91332b43e9cdee40a8132eab15e2fea3201bab6)

## Sprint (2022-04-20 - 2022-05-04)

- Patch: Update help message about `--principal-investigator` option ([#465](https://github.com/ScilifelabDataCentre/dds_cli/pull/465))
- Removed all CLI tests because needs redo ([#469](https://github.com/ScilifelabDataCentre/dds_cli/pull/469))
- (Re)Added parsing of project specific errors for `dds project access fix` and `dds user add -p` ([#491](https://github.com/ScilifelabDataCentre/dds_cli/pull/491))

## Sprint (2022-05-04 - 2022-05-18)

- Enable use of app for second factor authentication instead of email. ([#259](https://github.com/ScilifelabDataCentre/dds_cli/pull/259))

## Sprint (2022-06-15 - 2022-06-29)

- Display message of the day at top before output ([#498](https://github.com/ScilifelabDataCentre/dds_cli/pull/498))
- Change token check message for Windows to more user friendly ([#500](https://github.com/ScilifelabDataCentre/dds_cli/pull/500))
- New command: List all users as Super Admin and find existing users ([#504](https://github.com/ScilifelabDataCentre/dds_cli/pull/504))
- Add possibility of allowing group access to authenticated session ([#502](https://github.com/ScilifelabDataCentre/dds_cli/pull/502))

## Summer 2022

- Check for DDS_CLI_ENV = "test-instance" in order to allow testing of features before production ([#506](https://github.com/ScilifelabDataCentre/dds_cli/pull/506))
- List all active motds instead of latest and new command for deactivating motds ([#505](https://github.com/ScilifelabDataCentre/dds_cli/pull/505))
- New spinner when getting project private ([#510](https://github.com/ScilifelabDataCentre/dds_cli/pull/510))

## Sprint (2022-08-18 - 2022-09-02)

- Change in command: twofactor - activate and deactivate ([#519](https://github.com/ScilifelabDataCentre/dds_cli/pull/519))

## Sprint (2022-09-02 - 2022-09-16)

- Add storage usage information in the Units listing table for Super Admin ([#523](https://github.com/ScilifelabDataCentre/dds_cli/pull/523))
- Set project as busy / not busy when starting / finishing a upload ([#525](https://github.com/ScilifelabDataCentre/dds_cli/pull/525))
- Set project as busy / not busy when starting / finishing a download ([#526](https://github.com/ScilifelabDataCentre/dds_cli/pull/526))
- Set project as busy / not busy when starting / finishing a deletion ([#527](https://github.com/ScilifelabDataCentre/dds_cli/pull/527))

## Sprint (2022-09-16 - 2022-09-30)

- New command: `dds motd send [id]` to send MOTds to users ([#532](https://github.com/ScilifelabDataCentre/dds_cli/pull/532))
- Add project public_id to the temporary DDS directory to allow deliveries initiated at the same time ([#533](https://github.com/ScilifelabDataCentre/dds_cli/pull/533))
- New command: `dds maintenance [setting]` to set maintenance mode ([#535](https://github.com/ScilifelabDataCentre/dds_cli/pull/535))
- New command: `dds project status busy [OPTIONS]` to check for / list busy projects as Super Admin ([#536](https://github.com/ScilifelabDataCentre/dds_cli/pull/536))

## Sprint (2022-09-30 - 2022-10-14)

- Improved message displayed to user when data already uploaded ([#541](https://github.com/ScilifelabDataCentre/dds_cli/pull/541))
- New message displayed when KeyboardInterrupt used during upload / download ([#542](https://github.com/ScilifelabDataCentre/dds_cli/pull/542))
- Do not set projects as busy when uploading/downloading/deleting ([#549](https://github.com/ScilifelabDataCentre/dds_cli/pull/549))
- Command for listing invites ([#547](https://github.com/ScilifelabDataCentre/dds_cli/pull/547))

## Sprint (2022-10-14 - 2022-10-28)

- Limit projects listing to active projects only; a `--show-all` flag can be used for listing all projects, active and inactive ([#556](https://github.com/ScilifelabDataCentre/dds_cli/pull/556))
- Display name of creator when listing projects ([#557](https://github.com/ScilifelabDataCentre/dds_cli/pull/557))
