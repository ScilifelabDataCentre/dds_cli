# dp_api
API to access Scilifelab Data Centre's delivery portal. Built to handle data upload/download to/from Safespring S3.

**WIP** 

---
## Usage
```bash
dp_cli --file "/directory/of/file/to/upload.xxx"
```
## Setup
### CLI setup
```bash
pip3 install --editable .
```
Depends on a working database setup. 
### Database setup
#### Alternative 1: 
Fork the [Delivery Portal](https://github.com/ScilifelabDataCentre/delivery_portal.git) and follow the instructions. 

#### Alternative 2: 
Follow the [instructions](https://github.com/ScilifelabDataCentre/delivery_portal.git) without setting up the Delivery Portal: 

1. Install Docker if you don't already have it.

Mac:  
https://docs.docker.com/v17.12/docker-for-mac/install

Ubuntu:  
https://docs.docker.com/install/linux/docker-ce/ubuntu/

2. Build and run containers

```bash
cp dportal.yaml.sample dportal.yaml
docker-compose up
```

**To use terminal after starting services, use the `-d` option.**
```bash 
cp dportal.yaml.sample dportal.yaml
docker-compose up -d 
```

**To stop service** (if `-d` option used or in new terminal tab):
```bash 
docker-compose down
```

3. Go to http://localhost:5984/_utils/#setup

4. Create the databases. 
```bash
curl -X PUT http://delport:delport@127.0.0.1:5984/projects_db
curl -X PUT http://delport:delport@127.0.0.1:5984/user_db
```

5. Import the database contents. 
```bash
curl -d @dbfiles/project_db.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/project_db/_bulk_docs
curl -d @dbfiles/user_db.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/user_db/_bulk_docs
```
