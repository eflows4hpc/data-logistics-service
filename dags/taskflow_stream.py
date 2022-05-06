from importlib.metadata import metadata
import os
import shutil
import requests

from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.utils.dates import days_ago
from datacat_integration.hooks import DataCatalogHook

import json


from b2shareoperator import (get_file_list, get_object_md)

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def taskflow_stream():
    @task(multiple_outputs=True)
    def get_flist(**kwargs):
        params = kwargs['params']
        if 'oid' not in params: 
            print("Missing object id in pipeline parameters. Please provide an id for b2share or data cat id")
            return -1
        oid = params['oid']

        hook = DataCatalogHook()
        try:
            entry = json.loads(hook.get_entry('dataset', oid))
            if entry and 'b2share' in entry['url']:
                print(f"Got data cat b2share entry: {entry}\nwith url: {entry['url']}")
                oid = entry['url'].split('/')[-1]
                print(f"Extracted oid {oid}")
            else:
                print('No entry in data cat or not a b2share entry')

        except:
            # falling back to b2share
            print("No entry found. Probably a b2share object")
    

        connection = Connection.get_connection_from_secrets('default_b2share')
        server = connection.get_uri()
        print(f"Rereiving data from {server}")
        

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
