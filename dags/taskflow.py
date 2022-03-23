
from airflow.operators.python import PythonOperator
from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.models import Variable
from airflow.utils.dates import days_ago
import os

from decors import get_connection, remove, setup
from b2shareoperator import (download_file, get_file_list, get_object_md,
                             get_objects)

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def taskflow_example():

    @task(multiple_outputs=True)
    def extract(conn_id, **kwargs):
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
