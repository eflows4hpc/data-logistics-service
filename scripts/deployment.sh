#!/bin/bash
# @author Maria Petrova & Christian Böttcher
## USAGE:
#
# deployment.sh <user_home_directory> <git_directory> [SERVER_DOMAIN] [AIRFLOW__SECRETS__BACKEND] [AIRFLOW__SECRETS__BACKEND_KWARGS]

OLD_DIR=`pwd`
GIT_REPO=$HOME/data-logistics-service

echo "DEBUG_1 $0 $1 $2 $3 $4 $5"

#if null (var + trim empty strings)
if [ -z ${1+x} ]; then ENTRYPOINT=`pwd`; else ENTRYPOINT=$1; fi
if [ -z ${2+x} ]; then echo "No user input for starting repository location. Default value: $GIT_REPO"; else GIT_REPO=$2; fi
if [ -z ${3+x} ]; then SERVER_DOMAIN=dls.fz-juelich.de; else SERVER_DOMAIN=$3; fi
if [ -z ${3+x} ]; then unset AIRFLOW__SECRETS__BACKEND; else AIRFLOW__SECRETS__BACKEND=$4; fi
if [ -z ${3+x} ]; then unset AIRFLOW__SECRETS__BACKEND_KWARGS; else AIRFLOW__SECRETS__BACKEND_KWARGS=$5; fi

echo "DEBUG_2 $0 $1 $2 $3 $4 $5"
echo "DEBUG values: OLD_DIR=$OLD_DIR, ENTRYPOINT_DIR=$ENTRYPOINT and GIT_REPO=$GIT_REPO"
echo "DEBUG using secrets backend: $4"

cd $ENTRYPOINT
mkdir -p eflows-airflow
cd eflows-airflow
AIRFLOW_DIR=`pwd`
#DEBUG prints
echo "Project dir is set to: $AIRFLOW_DIR"
echo "Proceeding as user $(whoami)"

# Make the necessary folders for the airflow artefacts and copy the corresponging content
mkdir -p ./dags ./logs ./plugins ./config ./templates
cd $GIT_REPO
cp dags/* $AIRFLOW_DIR/dags
cp -r plugins/* $AIRFLOW_DIR/plugins
cp config/* $AIRFLOW_DIR/config
cp templates/* $AIRFLOW_DIR/templates
# Setup environment variables and install requirements
echo -e "AIRFLOW_UID=$(id -u)" > $GIT_REPO/dockers/.env
export AIRFLOW_UID=$(id -u)
echo "Collecting requirements"
reqs=`cat $GIT_REPO/requirements.txt | tr '\n' ' '`
echo "Collected requirements: $reqs"
# sudo sh -c "echo \"_PIP_ADDITIONAL_REQUIREMENTS=\"$reqs\"\" >> $GIT_REPO/dockers/.env"
echo "_PIP_ADDITIONAL_REQUIREMENTS=\"$reqs\"" >> $GIT_REPO/dockers/.env
pip install -r $GIT_REPO/requirements.txt

# sed -i "s_datacatalog.fz-juelich.de_${SERVER_DOMAIN}_g" docker-compose.yml

# it is at this point assumed that ip and volume are correctly assigned, and that dns is working properly
echo "-----------Bringing up the docker containers-----------"
docker-compose -f $GIT_REPO/dockers/docker-compose.yaml pull #  pull changed images (e.g. new latest, or specific tag)

docker-compose -f $GIT_REPO/dockers/docker-compose.yaml --project-directory $AIRFLOW_DIR --verbose up airflow-init
docker-compose -f $GIT_REPO/dockers/docker-compose.yaml --project-directory $AIRFLOW_DIR up -d

# docker-compose up -d # should only restart changed images, which will also update nginx and reverse-proxy image if needed

# nohup docker-compose logs -f >/app/mnt/docker.log & # or similar to capture docker log TODO (seems to cause gitlab CI to hang)

cd $OLD_DIR