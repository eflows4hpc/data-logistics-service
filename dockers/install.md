## Setup instance
Based on Christians cloud-init file:
`
#cloud-config

# upgrade packages
package_upgrade: true

# install relevant packages
packages:
  - python3
  - python3-pip
  - docker.io
  - docker-compose

runcmd:
  - usermod -aG docker ubuntu

`

Think about the security group for the isntance (e.g. to enable access to webgut 7001 port should be open). There is airflows group in HDF. 

## Prepare env

`
mkdir ./dags ./logs ./plugins
echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > .env
docker-compose up airflow-init
`

## Start-up
`
docker-compose up -d
`
