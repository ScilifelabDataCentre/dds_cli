from setuptools import setup, find_packages

setup(
    name='cli_code',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        line.strip() for line in open("requirements.txt").readlines()
    ],
    entry_points={
        'console_scripts': [
            'dds = cli_code.dds:cli',
        ],
    },
)