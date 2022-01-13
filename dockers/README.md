# Maintenance for customizations

### Footer
The DLS Service has a custom footer to contribute to the consortium image of the eFlows Project. The design of the custom footer is part of templates/main.html. This file is being injected as a volume in docker-compose.yaml, thus overriding the existing template from the public airflow image. For testing reasons, the path has been hard-coded in the docker-compose.yaml. 

**NOTE** When upgrading the airflow docker image, you have to make sure to correct the main.html by extracting and adjuting the latest version of the file from the airflow official repository. *For more details, please refer to the README file in the folder ```/templates```*.