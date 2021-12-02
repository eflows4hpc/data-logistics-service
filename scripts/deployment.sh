#!/bin/bash
# From Christian B.
## USAGE:
#
# deployment.sh <git_directory> [API_URL] [SERVER_DOMAIN]

OLD_DIR=`pwd`
GIT_REPO=$OLD_DIR/data-logistics-service

echo "DEBUG_1 $0 $1 $2 $3"

if [ -z ${1+x} ]; then NEW_DIR=`pwd`; else NEW_DIR=$1; fi
if [ -z ${2+x} ]; then GIT_REPO else GIT_REPO=$2; fi
# if [ -z ${2+x} ]; then API_URL=https://datacatalog.fz-juelich.de/; else API_URL=$2; fi
# if [ -z ${3+x} ]; then SERVER_DOMAIN=datacatalog.fz-juelich.de; else SERVER_DOMAIN=$3; fi

echo "DEBUG_2 $0 $1 $2 $3"

cd $NEW_DIR
`mkdir airflow`
cd airflow
AIRFLOW_DIR =`pwd`
`mkdir -p ./dags ./logs ./plugins ./config ./templates`
cd $GIT_REPO
`cp dags/* $AIRFLOW_DIR/dags`
`cp -r plugins/* $AIRFLOW_DIR/plugins`
`cp config/* $AIRFLOW_DIR/config`
`cp templates/* $AIRFLOW_DIR/templates`
echo -e "AIRFLOW_UID=$(id -u)" > $GIT_REPO/dockers/.env
export AIRFLOW_UID=$(id -u)
echo "Collecting requirements"
reqs=`cat requirements.txt | tr '\n' ' '`
echo "Collected - $reqs"
sudo sh -c "echo \"_PIP_ADDITIONAL_REQUIREMENTS=$reqs\" >> $GIT_REPO/dockers/.env"
pip install -r $GIT_REPO/requirements.txt
echo "Bringing up the docker containers"


# sed -i "s_datacatalog.fz-juelich.de_${SERVER_DOMAIN}_g" docker-compose.yml

# it is at this point assumed that ip and volume are correctly assigned, and that dns is working properly

docker-compose pull #  pull changed images (e.g. new latest, or specific tag)

docker-compose -f $GIT_REPO/docker-compose.yaml --project-directory $AIRFLOW_DIR --verbose up airflow-init
docker-compose -f $GIT_REPO/docker-compose.yaml --project-directory $AIRFLOW_DIR up -d

# docker-compose up -d # should only restart changed images, which will also update nginx and reverse-proxy image if needed

# nohup docker-compose logs -f >/app/mnt/docker.log & # or similar to capture docker log TODO (seems to cause gitlab CI to hang)

cd $OLD_DIR