from setuptools import setup, find_packages

setup(
    name='code_api',
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
    dependency_links=[
        'git+https://github.com/EGA-archive/crypt4gh.git', 
    ],
    entry_points={
        'console_scripts': [
            'dp_cli = code_api.dp_cli:put',
        ],
    },
)