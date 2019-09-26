# Delivery Dortal CLI
**WIP**

The CLI for the SciLifeLab Delivery Portal, build to handle data upload from SciLifeLab facilities to Safespring S3 and download by the order-placing entities.

## Installation

1. Follow the instructions in [project root]('https://github.com/inaod568/delivery_portal') folder. 

2. Create and activate virtual environment. 

```bash 
sudo pip3 install virtualenv

virtualenv my_virtual_env_name
. venv/bin/acivate
```

3. Install `cli_api` package.
```bash
pip3 install --editable .
```
4. Run the Delivery Portal CLI.
```bash 
dp_cli --file "/directory/of/file/to/upload"
```