from setuptools import setup, find_packages

version = "0.0.4"

with open("README.md") as f:
    readme = f.read()

with open("requirements.txt") as f:
    requirements = [line.strip() for line in open("requirements.txt").readlines()]

setup(
    name="dds_cli",
    version=version,
    description="A command line tool to manage data and projects in the SciLifeLab Data Delivery System.",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/ScilifelabDataCentre/dds_cli",
    license="MIT",
    packages=find_packages(exclude=("docs")),
    include_package_data=True,
    install_requires=requirements,
    setup_requires=["twine>=1.11.0", "setuptools>=38.6."],
    entry_points={
        "console_scripts": [
            "dds = dds_cli.__main__:dds_main",
        ],
    },
    zip_safe=False,
)
