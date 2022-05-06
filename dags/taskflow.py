
from airflow.operators.python import PythonOperator
from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.models import Variable
from airflow.utils.dates import days_ago
import os
from datacat_integration.hooks import DataCatalogHook
import json


from decors import get_connection, remove, setup
from b2shareoperator import (download_file, get_file_list, get_object_md)

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def taskflow_example():

    @task(multiple_outputs=True)
    def extract(conn_id, **kwargs):
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
        # check status?
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
        ssh_hook = get_connection(conn_id=connection_id, **kwargs)

        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            # check dir?
            ssh_client.exec_command(command=f"mkdir -p {target}")
            for [truename, local] in files.items():
                print(
                    f"Copying {local} --> {connection_id}:{os.path.join(target, truename)}")
                sftp_client.put(local, os.path.join(target, truename))
                # or separate cleanup task?
                os.unlink(local)

        return connection_id

    conn_id = PythonOperator(python_callable=setup, task_id='setup_connection')
    # another way of mixing taskflow and classical api:
    a_id = conn_id.output['return_value']

    data = extract(conn_id=a_id)
    files = transform(flist=data)
    ucid = load(connection_id=a_id, files=files)

    #b_id = ucid.output['return_value']
    en = PythonOperator(python_callable=remove, op_kwargs={
                        'conn_id': ucid}, task_id='cleanup')

    conn_id >> data >> files >> ucid >> en


dag = taskflow_example()
