from setuptools import setup, find_packages

setup(
    name='cli_api',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
    ],
    entry_points={
        'console_scripts': [
            'dp_cli = cli_api.dp_cli:cli',
        ],
    },
)