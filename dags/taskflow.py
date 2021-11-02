
from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.utils.dates import days_ago
import os

from b2shareoperator import (download_file, get_file_list, get_object_md,
                             get_objects)

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def taskflow_example():
    @task(multiple_outputs=True)
    def extract(**kwargs):
        connection = Connection.get_connection_from_secrets('default_b2share')
        server = connection.get_uri()
        print(f"Rereiving data from {server}")

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
        for fname, url in flist.items():
            print(f"Processing: {fname} --> {url}")
            tmpname = download_file(url=url, target_dir='/tmp/')
            name_mappings[fname] = tmpname
        return name_mappings

    @task()
    def load(files: dict, **kwargs):
        print(f"Total files downloaded: {len(files)}")
        params = kwargs['params']
        target = params.get('target', '/tmp/')
        connection_id = params.get('connection', 'default_ssh')
        
        ssh_hook = SSHHook(ssh_conn_id=connection_id)
        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            for [truename, local] in files.items():
                print(f"Copying {local} --> {connection_id}:{os.path.join(target, truename)}")
                sftp_client.put(local, os.path.join(target, truename))
                # or separate cleanup task?
                os.unlink(local)

    data = extract()
    files = transform(data)
    load(files)


dag = taskflow_example()
