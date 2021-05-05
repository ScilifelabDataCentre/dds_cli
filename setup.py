from setuptools import setup, find_packages

version = "0.1.0"

with open("README.md") as f:
    readme = f.read()

with open("requirements.txt") as f:
    requirements = [line.strip() for line in open("requirements.txt").readlines()]

setup(
    name="dds-cli",
    version=version,
    description="Data Delivery Service - Command line tool",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/ScilifelabDataCentre/DS_CLI",
    license="MIT",
    packages=find_packages(exclude=("docs")),
    include_package_data=True,
    install_requires=requirements,
    setup_requires=["twine>=1.11.0", "setuptools>=38.6."],
    entry_points={
        "console_scripts": [
            "dds = dds_cli.__main__:dds_cli",
        ],
    },
    zip_safe=False,
)
