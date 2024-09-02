"""Setup of DDS CLI."""

# pylint: disable=unspecified-encoding, exec-used, consider-using-with, duplicate-code

from setuptools import setup, find_packages

version = {}
with open("./dds_cli/version.py") as fp:
    exec(fp.read(), version)
VERSION = version["__version__"]

with open("README.md") as f:
    readme = f.read()

with open("requirements.txt") as f:
    requirements = [line.strip() for line in open("requirements.txt").readlines()]

setup(
    name="dds_cli",
    version=VERSION,
    description="A command line tool to manage data and projects in the SciLifeLab Data Delivery System.",
    long_description=readme,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    url="https://github.com/ScilifelabDataCentre/dds_cli",
    author="SciLifeLab Data Centre",
    license="MIT",
    packages=find_packages(exclude="docs"),
    include_package_data=True,
    install_requires=requirements,
    setup_requires=["twine>=1.11.0", "setuptools>=38.6"],
    entry_points={
        "console_scripts": [
            "dds = dds_cli.__main__:dds_main",
        ],
    },
    zip_safe=False,
)
