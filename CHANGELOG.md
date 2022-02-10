# Data Delivery System CLI: Changelog
* ([#](https://github.com/ScilifelabDataCentre/dds_cli/pull/))

* ([#](https://github.com/ScilifelabDataCentre/dds_cli/pull/))


## Sprint (2021-09-08 - 2021-09-22)
* Install `pytest` in github action ([#151](https://github.com/ScilifelabDataCentre/dds_cli/pull/151))
* `method` moved to base class ([#152](https://github.com/ScilifelabDataCentre/dds_cli/pull/152))
* Module used in testing ([#154](https://github.com/ScilifelabDataCentre/dds_cli/pull/154))
* Make error message readable ([#155](https://github.com/ScilifelabDataCentre/dds_cli/pull/155))
* Changed CLI to match the new authentication in the API ([#156](https://github.com/ScilifelabDataCentre/dds_cli/pull/156))

## Sprint (2021-09-22 - 2021-10-06)
* Added detection of Windows legacy versions ([#159](https://github.com/ScilifelabDataCentre/dds_cli/pull/159))
* Removed tests involving requests ([#166](https://github.com/ScilifelabDataCentre/dds_cli/pull/166))

## Sprint (2021-10-06 - 2021-10-20)
* Tests removed ([#169](https://github.com/ScilifelabDataCentre/dds_cli/pull/169))
* Project creation functionality ([#167](https://github.com/ScilifelabDataCentre/dds_cli/pull/167))
* `--is-sensitive` option added to project creation ([#171](https://github.com/ScilifelabDataCentre/dds_cli/pull/171))
* Changes to match the web changes regarding user inheritance and roles: [#627](https://github.com/ScilifelabDataCentre/dds_web/pull/627) ([#172](https://github.com/ScilifelabDataCentre/dds_cli/pull/172))
* Errors during upload logged directly instead of waiting for clean up at the end ([#173](https://github.com/ScilifelabDataCentre/dds_cli/pull/173))
* Changed from `resolve` to `abspath` ([#175](https://github.com/ScilifelabDataCentre/dds_cli/pull/175))
* Option to display users involved in projects: `dds ls --users` ([#174](https://github.com/ScilifelabDataCentre/dds_cli/pull/174))
* `invite` command ([#158](https://github.com/ScilifelabDataCentre/dds_cli/pull/158))

## Sprint (2021-10-20 - 2021-11-03)
* Refactoring of `dds rm` ([#179](https://github.com/ScilifelabDataCentre/dds_cli/pull/179))
* Formatting of the project lists moved to the CLI ([#184](https://github.com/ScilifelabDataCentre/dds_cli/pull/184))
* Removed the update of the project size after upload ([#185](https://github.com/ScilifelabDataCentre/dds_cli/pull/185))

## Sprint (2021-11-03 - 2021-11-17)
* Bug fix regarding usage values ([#189](https://github.com/ScilifelabDataCentre/dds_cli/pull/189))
* Functionality to associate users with projects ([#186](https://github.com/ScilifelabDataCentre/dds_cli/pull/186))
* Config option removed ([#190](https://github.com/ScilifelabDataCentre/dds_cli/pull/190))
* `expanduser` added since `os.path.abspath` does not expand the `~` symbol ([#191](https://github.com/ScilifelabDataCentre/dds_cli/pull/191))
* Save encrypted token after authentication and use for subsequent commands([#193](https://github.com/ScilifelabDataCentre/dds_cli/pull/193))

## Sprint (2021-11-17 - 2021-12-01)
* Username not required since sessions used ([#195](https://github.com/ScilifelabDataCentre/dds_cli/pull/195))
* Color in `pytest` ([#197](https://github.com/ScilifelabDataCentre/dds_cli/pull/197))
* Filename displayed in bucket replaced by UUID ([#196](https://github.com/ScilifelabDataCentre/dds_cli/pull/196))
* `--no-prompt` flag, `Session`->`Auth`, new `auth` subcommands: `login`, `logout`, `info` ([#198](https://github.com/ScilifelabDataCentre/dds_cli/pull/198))
* Tests for adding users and listing projects/files ([#199](https://github.com/ScilifelabDataCentre/dds_cli/pull/199))
* `--json` flag to `dds ls` to output list of project as json format ([#201](https://github.com/ScilifelabDataCentre/dds_cli/pull/201))

## Sprint (2021-12-01 - 2021-12-15)
* `sphinx` for automatic generation of documentation ([#202](https://github.com/ScilifelabDataCentre/dds_cli/pull/202))
* `status` command ([#204](https://github.com/ScilifelabDataCentre/dds_cli/pull/204))
* Removed all occurrences of `os.umask` ([#206](https://github.com/ScilifelabDataCentre/dds_cli/pull/206))
* Changed logging level back to `INFO` and output progress bars to stderr ([#207](https://github.com/ScilifelabDataCentre/dds_cli/pull/209))
* Changed download procedure from `boto3` to `requests` to handle presigned urls ([#203](https://github.com/ScilifelabDataCentre/dds_cli/pull/203))

## Sprint (2021-12-15 - 2021-12-29) _Christmas_
* Updated token expiration information ([#209](https://github.com/ScilifelabDataCentre/dds_cli/pull/209))
* Group command `user` ([#200](https://github.com/ScilifelabDataCentre/dds_cli/pull/200))
* `project` command and subcommands `grant`&`revoke` ([#210](https://github.com/ScilifelabDataCentre/dds_cli/pull/210))

## Sprint (2021-12-29 - 2022-01-12)
* Grouped commands into `auth`, `user`, `project` and `data`. Created common options and arguments. ([#213](https://github.com/ScilifelabDataCentre/dds_cli/pull/213))
* Command for displaying user info ([#214](https://github.com/ScilifelabDataCentre/dds_cli/pull/214))

## Sprint (2022-01-12 - 2022-01-26)
* Timestamps converted to local timezone when displaying ([#217](https://github.com/ScilifelabDataCentre/dds_cli/pull/217))
* Project ID always sent in request as `param` - consistency changes ([#220](https://github.com/ScilifelabDataCentre/dds_cli/pull/220))

## Sprint (2022-01-26 - 2022-02-09)
* File paths replaced by UUID to prevent sensitive information in Safespring storage ([#225](https://github.com/ScilifelabDataCentre/dds_cli/pull/225))
* Commands to activate and deactivate users ([#226](https://github.com/ScilifelabDataCentre/dds_cli/pull/226))
* Authentication with HOTP ([#222](https://github.com/ScilifelabDataCentre/dds_cli/pull/222))
* Handling of `ApiResponseError` to avoid huge error printout ([#228](https://github.com/ScilifelabDataCentre/dds_cli/pull/228))