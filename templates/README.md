# Maintenance for customizations

### Footer
The DLS Service has a custom footer to contribute to the consortium image of the eFlows Project. The design of the custom footer is part of templates/main.html. This file is being injected as a volume in docker-compose.yaml, thus overriding the existing template from the public airflow image. For testing reasons, the path has been hard-coded in the docker-compose.yaml. 

### Updates
 Taking a hard-coded path approach means that with every update of the official airflow image, or an upgrade of the python version for the official image, the currect main.html file has to be pulled anew from the official airflow repository with the corresponding version. For Version 2.2.3 that would be -> https://github.com/apache/airflow/blob/2.2.3/airflow/www/templates/airflow/main.html
 You will also need the copy the script under ```<!-- CUSTOM FOOTER SCRIPT -->```, which assures the responsive display of the footer.
 
 *An example of how to locate the main.html file in a running docker webserver container:*

 ```docker exec airflow_airflow-webserver_1 find /home/airflow/ | grep main.html ```
 
 Copy this file into the local repository and substitute the ```<footer>``` section with the custom DLS ```%footer%``` block. In case of a new python version in the official airflow image (and container) you will need to adjust the new path in the volume section of the docker-compose.yaml. 