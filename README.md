# SciLifeLab Data Delivery System - Command line interface

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![install with PyPI](https://img.shields.io/badge/install%20with-PyPI-blue.svg)](https://pypi.org/project/dds_cli/)

> **A command line tool `dds` to manage data and projects in the SciLifeLab Data Delivery Service.**

This will be used for data delivery within larger projects and/or projects resulting in the production of large amounts of data, for example next-generation sequencing data and imaging.

This tool is written and maintained by the [SciLifeLab Data Centre](https://www.scilifelab.se/data).

## Table of contents

* [Installation](#installation)
* [Overview of commands](#overview-of-commands)

## Installation

### Python Package Index

> :warning: Only pre-releases so far.

The `dds-cli` package can be installed from [PyPI](https://pypi.python.org/pypi/dds_cli/) using pip as follows:

```bash
pip install dds-cli
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

* `get` - Download specified files from the cloud and restore the original format.
* `ls` - List the projects and the files within projects.
* `put` - Process and upload specified files to the cloud.
* `rm` - Delete files within a project.
