#!/bin/bash
# @author Maria Petrova & Christian Böttcher
## USAGE:
#
# deployment.sh <user_home_directory> <git_directory> [SERVER_DOMAIN] [AIRFLOW__SECRETS__BACKEND] [AIRFLOW__SECRETS__BACKEND_KWARGS] [AIRFLOW__CORE__FERNET_KEY] [DAG_GIT_URL] [SSO_CLIENT_ID] [SSO_CLIENT_SECRET] [SSO_METADATA_URL]

OLD_DIR=`pwd`
GIT_REPO=$HOME/data-logistics-service


#if null (var + trim empty strings)
if [ -z ${1+x} ]; then ENTRYPOINT=`pwd`; else ENTRYPOINT=$1; fi
if [ -z ${2+x} ]; then echo "No user input for starting repository location. Default value: $GIT_REPO"; else GIT_REPO=$2; fi
if [ -z ${3+x} ]; then export SERVER_DOMAIN=dls.fz-juelich.de; else export SERVER_DOMAIN=$3; fi
if [ -z ${4+x} ]; then unset AIRFLOW__SECRETS__BACKEND; else export AIRFLOW__SECRETS__BACKEND=$4; fi
if [ -z ${5+x} ]; then unset AIRFLOW__SECRETS__BACKEND_KWARGS; else export AIRFLOW__SECRETS__BACKEND_KWARGS=$5; fi
if [ -z ${6+x} ]; then unset AIRFLOW__CORE__FERNET_KEY; else export AIRFLOW__CORE__FERNET_KEY=$6; fi
if [ -z ${7+x} ]; then unset DAG_GIT_URL; else export DAG_GIT_URL=$7; fi
if [ -z ${8+x} ]; then unset OAUTH_CLIENT_ID; else export OAUTH_CLIENT_ID=$8; fi
if [ -z ${9+x} ]; then unset OAUTH_CLIENT_SECRET; else export OAUTH_CLIENT_SECRET=$9; fi
if [ -z ${10+x} ]; then unset OAUTH_METADATA_URL; else export OAUTH_METADATA_URL=$10; fi



echo "DEBUG values: OLD_DIR=$OLD_DIR, ENTRYPOINT_DIR=$ENTRYPOINT and GIT_REPO=$GIT_REPO"
echo "DEBUG using secrets backend: $AIRFLOW__SECRETS__BACKEND"
echo "DEBUG backend args length: ${#AIRFLOW__SECRETS__BACKEND_KWARGS}"
#echo "DEBUG fernet key: ${AIRFLOW__CORE__FERNET_KEY}"
echo "DEBUG DAG git dir: $DAG_GIT_URL"


cd $ENTRYPOINT
mkdir -p eflows-airflow
cd eflows-airflow
AIRFLOW_DIR=`pwd`
#DEBUG prints
echo "Project dir is set to: $AIRFLOW_DIR"
echo "Proceeding as user $(whoami)"

# clean out the target directory to ensure only new stuff is there
# rm -rf $AIRFLOW_DIR/*

# Make the necessary folders for the airflow artefacts and copy the corresponging content
mkdir -p ./dags ./logs ./plugins ./config ./templates
cd $GIT_REPO
rm -rf $AIRFLOW_DIR/dags && mkdir $AIRFLOW_DIR/dags && git clone $DAG_GIT_URL $AIRFLOW_DIR/dags
cp -r plugins/* $AIRFLOW_DIR/plugins
cp config/* $AIRFLOW_DIR/config/
cp -r templates/* $AIRFLOW_DIR/templates
cp client_secrets.json $AIRFLOW_DIR/client_secrets.json
# Setup environment variables and install requirements
echo -e "AIRFLOW_UID=$(id -u)" > $GIT_REPO/dockers/.env
export AIRFLOW_UID=$(id -u)

pip install -r $GIT_REPO/requirements.txt

sed -i "s_datalogistics.eflows4hpc.eu_${SERVER_DOMAIN}_g" $GIT_REPO/dockers/docker-compose.yaml
sed -i "s/SSO_CLIENT_SECRET/${SSO_CLIENT_SECRET}/g" $AIRFLOW_DIR/client_secrets.json

# it is at this point assumed that ip and volume are correctly assigned, and that dns is working properly
echo "-----------Bringing up the docker containers-----------"
docker-compose -f $GIT_REPO/dockers/docker-compose.yaml pull #  pull changed images (e.g. new latest, or specific tag)

# no init for persistent database & dirs
#docker-compose -f $GIT_REPO/dockers/docker-compose.yaml --project-directory $AIRFLOW_DIR --verbose up airflow-init
docker-compose -f $GIT_REPO/dockers/docker-compose.yaml --project-directory $AIRFLOW_DIR up -d

cd $OLD_DIR
