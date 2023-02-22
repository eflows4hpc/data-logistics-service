[![DOI](https://zenodo.org/badge/447551112.svg)](https://zenodo.org/badge/latestdoi/447551112)

# Data Logistics Service

eFlows4HPC Data Logistics Service

This work has been supported by the eFlows4HPC project, contract #955558. This project has received funding from the European High-Performance Computing Joint Undertaking (JU) under grant agreement No 955558. The JU receives support from the European Union’s Horizon 2020 research and innovation programme and Spain, Germany, France, Italy, Poland, Switzerland, Norway.

The project has recieved funding from German Federal Ministry of Education and Research agreement no. 16GPC016K.
<img src="docs/images/BMBF.jpg" width="200">


## Architecture
Architecture document can be found in [arch](docs/datalogistics-arch.adoc) folder. 

## Install and run

```
git pull ...
mkdir ./logs ./tmp
echo -e "AIRFLOW_UID=$(id -u)" > .env
reqs=`cat requirements.txt | tr '\n' ' '`
echo "_PIP_ADDITIONAL_REQUIREMENTS=$reqs" >> .env

docker-compose -f dockers/docker-compose.yaml --project-directory . up airflow-init
```

```
docker-compose -f dockers/docker-compose.yaml --project-directory . up -d
```

## Setup connection

### B2Share connection 
Here we use testing instance (check hostname)

```
curl -X POST -u creds -H "Content-Type: application/json"  --data '{"connection_id": "default_b2share","conn_type":"https", "host": "b2share-testing.fz-juelich.de", "schema":""}' airflow:7001/api/v1/connections
```

### SSH 
Copy to target goes through scp (example with username/pass)

```
curl -X POST -u creds -H "Content-Type: application/json"  --data '{"connection_id": "default_ssh", "conn_type": "ssh", "host": "ssh", "login": "user", "port": 2222, "password": "pass"}' airflow:7001/api/v1/connections
```

Connections can also be added through env variables, like

```
AIRFLOW_CONN_MY_PROD_DATABASE=my-conn-type://login:password@host:port/schema?param1=val1&param2=val2
```

## CI/CD
The gitlab repository is set up to automatically build the customized airflow image and deploy to the production and testing environment. The pipeline and jobs for this are defined in the [.gitlab-ci.yml](.gitlab-ci.yml) file.
In general, pushes to the main branch update the testing deployment, and tags containing "stable" update the production deployment.

Since the airflow image is pretty large, the docker image is only built when starting the job manually, to keep the docker registry at a reasonable size.

To avoid unneeded downtime, the VMs hosting the deployments are usuallly not re-created, and instead only the updated airflow image, as well as updated airflow config is uploaded to the VM. After this, the docker containers are restarted.
If a "full-deployment" is required (i.e. the VMs shuld be newly created), the pipeline has to be started with a variable ```MANUAL_FULL_DEPLOY=true```. This can be done while starting the pipeline via the web interface.
