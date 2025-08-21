<p>
   <h1 align="center">Data Delivery System: CLI</h1>
</p>

<p align="center">
    <b>A command line tool `dds` to manage projects and data in the SciLifeLab Data Delivery System.</b>
</p>
<br />

<p align="center">
<img alt="Release" src="https://img.shields.io/github/v/release/SciLifeLabDataCentre/dds_cli">
<a href="https://pypi.org/project/dds-cli/">
    <img alt="Install from PyPi" src="https://img.shields.io/badge/install%20with-PyPI-blue.svg?logo=pypi">
</a>
<a href="https://opensource.org/licenses/MIT">
    <img alt="Licence: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg">
</a>
<a href="https://github.com/psf/black">
    <img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg">
</a>
<a href="https://prettier.io/">
    <img alt="Code style: prettier" src="https://img.shields.io/badge/code_style-prettier-ff69b4.svg">
</a>
<br />
<a href="https://github.com/ScilifelabDataCentre/dds_cli/actions/workflows/lint-black-cli.yml">
    <img alt="Formatter: black" src="https://github.com/ScilifelabDataCentre/dds_cli/actions/workflows/lint-black-cli.yml/badge.svg?event=push">
</a>
<img alt="CodeQL" src="https://github.com/ScilifelabDataCentre/dds_cli/actions/workflows/codeql-cli.yml/badge.svg">
<a href="https://codecov.io/github/ScilifelabDataCentre/dds_cli" > 
 <img src="https://codecov.io/github/ScilifelabDataCentre/dds_cli/graph/badge.svg?token=zsrDpNqs6v"/> 
 </a>
<img alt="Tests" src="https://github.com/ScilifelabDataCentre/dds_cli/actions/workflows/pytest-cli.yml/badge.svg">
</p>

<p align="center">
<b>Links</b>
<br />
<a href="https://scilifelabdatacentre.github.io/dds_cli/">
    <img alt="Documentation" src="https://img.shields.io/badge/-Documentation-222222?logo=github-pages">
</a>
<a href="https://github.com/ScilifelabDataCentre/dds_web/blob/master/doc/Technical-Overview.pdf">
    <img alt="Technical Overview" src="https://img.shields.io/badge/-Technical%20Overview-informational?logo=github">
</a>
<a href="https://github.com/ScilifelabDataCentre/dds_web/wiki/Architecture-Decision-Record,-ADR">
    <img alt="Architecture Decision Record" src="https://img.shields.io/badge/-ADR-000000?logo=github">
</a>
<a href="https://github.com/ScilifelabDataCentre/dds_web/blob/master/doc/Troubleshooting.pdf">
    <img alt="Troubleshooting" src="https://img.shields.io/badge/-Troubleshooting%20Guide-red?logo=github">
</a>
<a href="https://github.com/ScilifelabDataCentre/dds_web">
    <img alt="CLI" src="https://img.shields.io/badge/-Web / API-yellow?logo=github">
</a>
</p>

## About

**The Data Delivery System (DDS) is a cloud-based system for all SciLifeLab platforms where data generated throughout each project can be delivered to the research groups in a fast, secure and simple way. The CLI makes requests to the API (see badge below for link) in order to use the API functionality.**

> _The Data Delivery System is developed and maintained by the SciLifeLab Data Centre. National Genomics Infrastructure (NGI) Stockholm has been a part of the development team during 2021 and early 2022._

---

## Table of contents

- [Installation](#installation)
- [Overview of commands](#overview-of-commands)

## Installation

### Python Package Index

The `dds-cli` package can be installed from [PyPI](https://pypi.python.org/pypi/dds_cli/) using pip as follows:

```bash
pip install --upgrade dds-cli
```

After installing, run `dds` (or `dds --help`) and verify that the output looks like this:

![dds help command](img/dds-help-1.svg)

### Executables

Executables are available for Windows, MacOS and Linux. These allow you to run the CLI without needing to install it (and the pip / Python requirements) yourself. Download them from the (bottom of the) latest release page: [Latest Release](https://github.com/ScilifelabDataCentre/dds_cli/releases/latest/)

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
