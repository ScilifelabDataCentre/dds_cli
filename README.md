# SciLifeLab Data Delivery System - Command line interface

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![install with PyPI](https://img.shields.io/badge/install%20with-PyPI-blue.svg)](https://pypi.org/project/dds-cli/)

> **A command line tool `dds` to manage data and projects in the SciLifeLab Data Delivery Service.**

This will be used for data delivery within larger projects and/or projects resulting in the production of large amounts of data, for example next-generation sequencing data and imaging.

This tool is written and maintained by the [SciLifeLab Data Centre](https://www.scilifelab.se/data).

## Table of contents

- [Installation](#installation)
- [Overview of commands](#overview-of-commands)

## Installation

### Python Package Index

> :warning: Only pre-releases so far.

The `dds-cli` package can be installed from [PyPI](https://pypi.python.org/pypi/dds_cli/) using pip as follows:

```bash
pip install dds-cli
```

After installing, run `dds` and verify that the output looks like this:

```bash
$ dds
     ︵
 ︵ (  )   ︵
(  ) ) (  (  )   SciLifeLab Data Delivery System
 ︶  (  ) ) (    https://delivery.scilifelab.se/
      ︶ (  )    Version 1.0.0
          ︶

 Usage: dds [OPTIONS] COMMAND [ARGS]...

 SciLifeLab Data Delivery System (DDS) command line interface.
 Access token is saved in a .dds_cli_token file in the home directory.

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
│  --verbose     -v               Print verbose output to the console.                             │
│  --log-file    -l   <filename>  Save a log to a file.                                            │
│  --no-prompt                    Run without any interactive features.                            │
│  --token-path  -tp  TEXT        The path where the authentication token will be stored. For a    │
│                                 normal use-case, this should not be needed.                      │
│  --version                      Display the version of this software.                            │
│  --help                         List the options of any DDS subcommand and its default           │
│                                 settings.                                                        │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────╮
│  auth     Group command for creating and managing authenticated sessions.                        │
│  data     Group command for uploading, downloading and managing project data.                    │
│  ls       List the projects you have access to or the project contents.                          │
│  project  Group command for creating and managing projects within the DDS.                       │
│  unit     Group command for managing units.                                                      │
│  user     Group command for managing user accounts, including your own.                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Development version

If you would like the latest development version of tools, the command is:

```bash
pip install --upgrade --force-reinstall git+https://github.com/ScilifelabDataCentre/dds_cli.git@dev
```

If you intend to make edits to the code, first make a fork of the repository and then clone it locally.
Go to the cloned directory and install with pip (also installs development requirements):

```bash
pip install --upgrade -r requirements-dev.txt -e .
```

## Overview of commands

Once installed you can use the command `dds` in a terminal session. This has the following subcommands:

- `auth`: Create and manage authenticated sessions.
- `user`: Create and manage user accounts, including your own.
- `project`: Create and manage projects.
- `data`: Upload, download and manage project data.
- `ls`: List projects and project contents.
