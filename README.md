# Data Delivery System CLI -- **WIP**
This will be used for data delivery within larger projects
and/or projects resulting in the production of large amounts of data, e.g. sequence data.

---
## Setup docker environment:

**1. Docker installation**

	Mac:
	https://docs.docker.com/v17.12/docker-for-mac/install

	Ubuntu:
	https://docs.docker.com/install/linux/docker-ce/ubuntu/

**2. In _DS_CLI_ folder**
* Setup CLI: `pip3 install --editable .`

**3. In root (Data-Delivery-System)** 
* Build and run containers
	In the root folder (Data-Delivery-System/), run: 
	```bash
	docker-compose up
	```

	* To use terminal after starting services, use the `-d` option.

		```
		docker-compose up -d 
		```

	* To stop service: 
		```bash 
		docker-compose down
		```

**4. After changing DB**
To rebuild the database after a change, you need to: 
1. Delete the `db-data` folder
2. Run 
	```
	docker rm $(docker ps -a -q) -f
	docker volume prune
	```
3. Run 
	```
	docker-compose build --no-cache
	```
4. Run `docker-compose up` as described above.
5. If there are still issues, try deleting the pycache folders and repeat the steps. 
