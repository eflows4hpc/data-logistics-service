# Data Logistics Service

eFlows4HPC Data Logistics Service


```
mkdir ./logs ./plugins
echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > .env
echo "_PIP_ADDITIONAL_REQUIREMENTS=urllib3==1.26.6" >> .env

docker-compose -f dockers/docker-compose.yaml --project-directory . up airflow-init
```

```
docker-compose -f dockers/docker-compose.yaml --project-directory . up -d
```

## Setup connection
curl -X POST -u creds -H "Content-Type: application/json"  --data '{"connection_id": "default_b2share","conn_type":"https", "host": "b2share-testing.fz-juelich.de", "schema":""}' localhost:7001/api/v1/connections

