#!/bin/bash
# From Christian B.
## USAGE:
#
# deployment.sh <git_directory> [API_URL] [SERVER_DOMAIN]

OLD_DIR=`pwd`

echo "DEBUG_1 $0 $1 $2 $3"

if [ -z ${1+x} ]; then NEW_DIR=`pwd`; else NEW_DIR=$1; fi
# if [ -z ${2+x} ]; then API_URL=https://datacatalog.fz-juelich.de/; else API_URL=$2; fi
# if [ -z ${3+x} ]; then SERVER_DOMAIN=datacatalog.fz-juelich.de; else SERVER_DOMAIN=$3; fi

echo "DEBUG_2 $0 $1 $2 $3"

cd $NEW_DIR

# pip install -r requirements.txt

# sed -i "s_datacatalog.fz-juelich.de_${SERVER_DOMAIN}_g" docker-compose.yml

# it is at this point assumed that ip and volume are correctly assigned, and that dns is working properly

docker-compose pull #  pull changed images (e.g. new latest, or specific tag)
TIME=`date +%Y-%m-%d-%H-%M`
mv /app/mnt/docker.log "/app/mnt/docker.log.${TIME}"
docker-compose -f ../data-logistics-service/dockers/docker-compose.yaml --project-directory . up airflow-init
docker-compose -f ../data-logistics-service/dockers/docker-compose.yaml --project-directory . up -d
# docker-compose up -d # should only restart changed images, which will also update nginx and reverse-proxy image if needed

# nohup docker-compose logs -f >/app/mnt/docker.log & # or similar to capture docker log TODO (seems to cause gitlab CI to hang)

cd $OLD_DIR