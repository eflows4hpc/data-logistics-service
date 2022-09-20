from airflow.decorators import dag, task
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.utils.dates import days_ago
from airflow.models.connection import Connection
from airflow.models import Variable
from airflow.operators.python import get_current_context

from datacat_integration.hooks import DataCatalogHook
from datacat_integration.connection import DataCatalogEntry

from b2shareoperator import (download_file, get_file_list, get_object_md,
                             get_record_template, create_draft_record, add_file, submit_draft)
from decors import get_connection
import docker_cmd as doc
from docker_cmd import WORKER_DATA_LOCATION
import os
import uuid
import tempfile

"""This piplines is a test case for starting a clusterting algorithm with HeAT, running in a Docker environment.
A test set of parameters with a HeAT example:
Data Catalog Integration example: {"oid": "e13bcab6-3664-4090-bebb-defdb58483e0", "image": "ghcr.io/helmholtz-analytics/heat:1.1.1-alpha", "entrypoint": "/bin/bash", "command": "python demo_knn.py iris.h5 calc_res.txt", "register":"True"}
Data Catalog Integration example: {"oid": "e13bcab6-3664-4090-bebb-defdb58483e0", "image":"hello-world", "register":"True"} 
Params:
    oid (str): oid of the data (e.g, from data catalog)
    image (str): a docker contianer image
    job_args (str): 
        Optional: a string of further arguments which might be needed for the task execution
    entrypoint (str):
        Optional: you can specify or overwrite the docker entrypoint
    command (str):
        Optional: you can specify or override the command to be executed
    args_to_dockerrun (str):
        Optional: docker run additional arguments
    register (True, False):
        Optional, default is False: register the resulsts in the data catalog
"""

default_args = {
    'owner': 'airflow',
}

@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example', 'docker', 'datacat'])
def docker_in_worker():
    DW_CONNECTION_ID = "docker_worker"


    @task()
    def stagein(**kwargs):
        """ stage in task
        This task gets the 'datacat_oid' or 'oid' from the DAG params to retreive a connection from it (b2share for now).
        It then downloads all data from the b2share entry to the local disk, and returns a mapping of these files to the local download location,
        which can be used by the following tasks.
        """
        params = kwargs['params']
        datacat_hook = DataCatalogHook()
        
        if 'oid' not in params:  # {"oid": "b143bf73efd24d149bba4c081964b459"}
            if 'datacat_oid' not in params:
                print("Missing object id in pipeline parameters")
                return -1  # non zero exit code is a task failure
            else:
                params['oid'] = params['datacat_oid']
        oid_split = params['oid'].split("/")
        type = 'dataset'
        oid = 'placeholder_text'
        if len(oid_split) is 2:
            type = oid_split[0]
            oid = oid_split[1]
        elif len(oid_split) is 1:
            oid = oid_split[0]
        else:
            print("Malformed oid passed as parameter.")
            return -1

        entry = DataCatalogEntry.from_json(datacat_hook.get_entry(type, oid))

        print(f"using entry: {entry}")
        b2share_server_uri = entry.url
        # TODO general stage in based on type metadata
        # using only b2share for now
        b2share_oid = entry.metadata['b2share_oid']

        obj = get_object_md(server=b2share_server_uri, oid=b2share_oid)
        print(f"Retrieved object {oid}: {obj}")
        flist = get_file_list(obj)
        
        name_mappings = {}
        tmp_dir = Variable.get("working_dir", default_var='/tmp/')
        print(f"Local working dir is: {tmp_dir}")
        
        for fname, url in flist.items():
            print(f"Processing: {fname} --> {url}")
            tmpname = download_file(url=url, target_dir=tmp_dir)
            name_mappings[fname] = tmpname
            
        return name_mappings   
   
    @task()
    def move_to_docker_host(files: dict, **kwargs):
        """This task copies the data onto the remote docker worker, 
        which will enable the following tasks an access to the data

        Args:
            files (dict): the files that will be stored on the docker worker
        Returns:
            target_dir: the location of the files on the docker worker
        """
        print(f"Using {DW_CONNECTION_ID} connection")
        ssh_hook = get_connection(conn_id=DW_CONNECTION_ID)
        user_dir_name = str(uuid.uuid4())
        target_dir = os.path.join(WORKER_DATA_LOCATION, user_dir_name)
        
        with ssh_hook.get_conn() as ssh_client:
            
            sftp_client = ssh_client.open_sftp()

            sftp_client.mkdir(target_dir, mode=0o755)
            for [truename, local] in files.items():
                print(
                    f"Copying {local} --> {DW_CONNECTION_ID}:{os.path.join(target_dir, truename)}")
                sftp_client.put(local, os.path.join(target_dir, truename))
                # or separate cleanup task?
                os.unlink(local)

        return target_dir

    @task
    def run_container(data_location, **kwargs):
        """A task which runs in the docker worker and spins up a docker container with the an image and giver parameters.

        Args:
            image (str): a docker contianer image
            job_args (str): 
                Optional: a string of further arguments which might be needed for the task execution
            entrypoint (str):
                Optional: you can specify or overwrite the docker entrypoint
            command (str):
                Optional: you can specify or override the command to be executed
            args_to_dockerrun (str):
                Optional: docker run additional arguments
        """    
        params = kwargs['params']
        
        cmd = doc.get_dockercmd(params, data_location)
        print(f"Executing docker command {cmd}")
        
        print(f"Using {DW_CONNECTION_ID} connection")
        hook = get_connection(conn_id=DW_CONNECTION_ID)
        
        task_calculate = SSHOperator(
            task_id="calculate",
            ssh_hook=hook,
            command=cmd
        )
        
        context = get_current_context()
        task_calculate.execute(context)
        
        return data_location

    @task
    def ls_results(output_dir):
        if not output_dir:
            return "No output to stage out. Nothing more to do."
        hook = get_connection(conn_id=DW_CONNECTION_ID)
        
        cmd = f"ls -al {output_dir}"
        process = SSHOperator(
            task_id="print_results",
            ssh_hook=hook,
            command=cmd
        )
        context = get_current_context()
        process.execute(context)    
    
    @task()
    def retrieve_res(output_dir: str, input_files: dict, **kwargs):
        """This task copies the data from the remote docker worker back to airflow workspace

        Args:
            output_dir (str): the folder containing all the user files for the executed task, located on the docker worker 
        Returns:
            local_fpath (list): the path of the files copied back to the airflow host
        """
        working_dir = Variable.get("working_dir", default_var='/tmp/')
        name_mappings = {}
        print(f"Using {DW_CONNECTION_ID} connection")
        ssh_hook = get_connection(conn_id=DW_CONNECTION_ID)

        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            
            for fname in sftp_client.listdir(output_dir):
                if fname not in input_files.keys():
                    
                    tmpname = tempfile.mktemp(dir=working_dir)
                    local = os.path.join(working_dir, tmpname)
                    print(f"Copying {os.path.join(output_dir, fname)} to {local}")
                    sftp_client.get(os.path.join(output_dir, fname), local)
                    name_mappings[fname] = local
        
        return name_mappings
    
    @task()
    def cleanup_doc_worker(res_fpaths_local, data_on_worker, **kwargs):
        """This task deletes all the files from the docker worker

          Args:
              res_fpaths_local: used only to define the order of tasks within the DAG, i.e. wait for previos task to complete before cleaning the worker space  
              data_on_worker (str): delete the folder with the user data from the docker worker
        """

        print(f"Using {DW_CONNECTION_ID} connection")
        ssh_hook = get_connection(conn_id=DW_CONNECTION_ID)

        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            d = os.path.join(WORKER_DATA_LOCATION, data_on_worker)
           
            for f in sftp_client.listdir(d):
                print(f"Deleting file {f}")
                sftp_client.remove(os.path.join(d, f))
            print(f"Deleting directory {DW_CONNECTION_ID}:{d}")
            sftp_client.rmdir(d)
        
                
    @task
    def stageout_results(output_mappings: dict):
        """This task transfers the output files to b2share

        Args:
            output_mappings (dict): {true_filename, local_path} a dictionary of the output files to be submitted to the remote storage, e.g., b2share 
        Returns:
            a b2share record
        """
        if not output_mappings:
            print("No output to stage out. Nothing more to do.")
            return -1
        connection = Connection.get_connection_from_secrets('default_b2share')
        
        server = "https://" + connection.host
        token = ''
        if 'access_token' in connection.extra_dejson.keys():
            token = connection.extra_dejson['access_token']
        print(f"Registering data to {server}")
        template = get_record_template()
        
        r = create_draft_record(server=server, token=token, record=template)
        print(f"record {r}")
        if 'id' in r:
            print(f"Draft record created {r['id']} --> {r['links']['self']}")
        else:
            print('Something went wrong with registration', r, r.text)
            return -1
        
        for [truename, local] in output_mappings.items():
            print(f"Uploading {truename}")
            _ = add_file(record=r, fname=local, token=token, remote=truename)
            # delete local
            os.unlink(local)
        
        print("Submitting record for pubication")
        submitted = submit_draft(record=r, token=token)
        print(f"Record created {submitted}")

        return submitted['links']['publication']
   
        

    @task()
    def register(object_url, additional_metadata = {}, **kwargs):
        """This task registers the b2share record into the data catalog

        Args:
            object_url: from b2share
            additional_metadata 
        """
        params = kwargs['params']
        reg = params.get('register', False)
        if not reg:
            print("Skipping registration as 'register' parameter is not set")
            return 0

        hook = DataCatalogHook()
        print("Connected to datacat via hook")

        if not additional_metadata.get('author', False):
            additional_metadata['author'] = "DLS on behalft of eFlows"
        
        if not additional_metadata.get('access', False):
            additional_metadata['access'] = "hook-based"
    
        entry = DataCatalogEntry(name=f"DLS results {kwargs['run_id']}",
                                 url=object_url,
                                 metadata=additional_metadata
                                )
        try:
            r = hook.create_entry(datacat_type='dataset', entry=entry)
            print("Hook registration returned: ", r)
            return f"{hook.base_url}/dataset/{r}" 
        except ConnectionError as e:
            print('Registration failed', e)
            return -1
            
    input_files = stagein()
    data_location = move_to_docker_host(input_files)
    data_on_worker = run_container(data_location)
    ls_results(data_on_worker)
    res_fpaths = retrieve_res(data_on_worker, input_files)
    cleanup_doc_worker(res_fpaths, data_on_worker)
    url_or_errcode = stageout_results(res_fpaths)
    register(url_or_errcode)

    # files >> data_locations >> output_fnames >> ls_results(output_fnames) >> files >> stageout_results(files) >> cleanup()
    
dag = docker_in_worker()

