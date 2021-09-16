# Data Logistics Service

eFlows4HPC Data Logistics Service


```
mkdir ./logs ./plugins
echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > .env
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