
from airflow import settings
from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.models import Variable
from airflow.utils.dates import days_ago
import os

from b2shareoperator import (download_file, get_file_list, get_object_md,
                             get_objects)

default_args = {
    'owner': 'airflow'
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example', 'datacat_integration'])
def taskflow_datacat_integration():

    @task(multiple_outputs=True)
    def extract(conn_id, **kwargs):
        connection = Connection.get_connection_from_secrets(conn_id)
        server = connection.get_uri()
        print(f"Retreiving data from {server}")

        params = kwargs['params']
        if 'oid' not in params:  # {"oid":"b38609df2b334ea296ea1857e568dbea"}
            print("Missing object id in pipeline parameters")
            lst = get_objects(server=server)
            flist = {o['id']: [f['key'] for f in o['files']] for o in lst}
            print(f"Objects on server: {flist}")
            return -1  # non zero exit code is a task failure

        oid = params['oid']

        obj = get_object_md(server=server, oid=oid)
        print(f"Retrieved object {oid}: {obj}")
        flist = get_file_list(obj)
        return flist

    @task(multiple_outputs=True)
    def transform(flist: dict):
        name_mappings = {}
        tmp_dir = Variable.get("working_dir", default_var='/tmp/')
        print(f"Local working dir is: {tmp_dir}")
        
        for fname, url in flist.items():
            print(f"Processing: {fname} --> {url}")
            tmpname = download_file(url=url, target_dir=tmp_dir)
            name_mappings[fname] = tmpname
        return name_mappings

    @task()
    def load(connection_id, files: dict, **kwargs):
        print(f"Total files downloaded: {len(files)}")
        params = kwargs['params']
        target = params.get('target', '/tmp/')
        
        print(f"Using {connection_id} connection")
        
        ssh_hook = SSHHook(ssh_conn_id=connection_id)
        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            for [truename, local] in files.items():
                print(f"Copying {local} --> {connection_id}:{os.path.join(target, truename)}")
                sftp_client.put(local, os.path.join(target, truename))
                # or separate cleanup task?
                os.unlink(local)


    conn_id = "e3710075-9f8f-4ae0-a1c3-7d92c0182d19" # created as copy of default_b2share
    data = extract(conn_id)
    files = transform(data)
    load(connection_id = conn_id, files=files)

dag = taskflow_datacat_integration()
