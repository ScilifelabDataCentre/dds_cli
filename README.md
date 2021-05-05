# SciLifeLab Data Delivery Service - Command line interface

This tool adds a new terminal command `dds` which you can use to manage data and projects in the SciLifeLab Data Delivery Service over the command line.

This will be used for data delivery within larger projects and/or projects resulting in the production of large amounts of data, for example next-generation sequencing data.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![install with PyPI](https://img.shields.io/badge/install%20with-PyPI-blue.svg)](https://pypi.org/project/dds-cli/)

## Table of contents

* [Installation](#installation)
* [Overview of commands](#overview-of-commands)

## Installation

### Python Package Index

> :warning: Coming soon after first release

The `dds-cli` package can be installed from [PyPI](https://pypi.python.org/pypi/dds-cli/) using pip as follows:

```bash
pip install dds-cli
```

### Development version

If you would like the latest development version of tools, the command is:

```bash
pip install --upgrade --force-reinstall git+https://github.com/nScilifelabDataCentre/DS_CLI.git@dev
```

If you intend to make edits to the code, first make a fork of the repository and then clone it locally.
Go to the cloned directory and install with pip (also installs development requirements):

```bash
pip install --upgrade -r requirements-dev.txt -e .
```

## Overview of commands

This package adds a tool `dds` on the command line which has the following subcommands:

* `get` - Download specified files from the cloud and restore the original format.
* `ls` - List the projects and the files within projects.
* `put` - Process and upload specified files to the cloud.
* `rm` - Delete files within a project.
