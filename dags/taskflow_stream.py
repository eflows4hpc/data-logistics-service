import os
import shutil
import requests

from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.utils.dates import days_ago


from b2shareoperator import (get_file_list, get_object_md,
                             get_objects)

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def taskflow_stream():
    @task(multiple_outputs=True)
    def get_flist(**kwargs):
        connection = Connection.get_connection_from_secrets('default_b2share')
        server = connection.get_uri()
        print(f"Rereiving data from {server}")

        params = kwargs['params']
        if 'oid' not in params:  # {"oid":"b38609df2b334ea296ea1857e568dbea"}
            print("Missing object id in pipeline parameters")
            lst = get_objects(server=server)
            flist = {o['id']: [f['key'] for f in o['files']] for o in lst}
            print(f"Objects on server: {flist}")
            return -1

        oid = params['oid']

        obj = get_object_md(server=server, oid=oid)
        print(f"Retrieved object {oid}: {obj}")
        flist = get_file_list(obj)
        return flist

    @task(multiple_outputs=True)
    def stream_upload(flist: dict, **kwargs):
        params = kwargs['params']
        target = params.get('target', '/tmp/')
        connection_id = params.get('connection', 'default_ssh')
        ssh_hook = SSHHook(ssh_conn_id=connection_id)
        mappings = dict()
        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()

            for fname, url in flist.items():
                print(f"Processing: {url} --> {fname}")
                with requests.get(url, stream=True) as r:
                    with sftp_client.open(os.path.join(target, fname), 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
                mappings[url] = os.path.join(target, fname)
        return mappings

    flist = get_flist()
    stats = stream_upload(flist)

dag = taskflow_stream()
