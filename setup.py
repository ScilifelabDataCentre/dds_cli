from setuptools import setup, find_packages

setup(
    name='cli_code',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'CouchDB',
        'filetype', 
        'cryptography', 
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'ds_deliver = cli_code.ds_deliver:cli',
        ],
    },
)