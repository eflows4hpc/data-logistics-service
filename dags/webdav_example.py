import os

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.models.connection import Connection
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from webdav3.client import Client

from uploadflow import ssh2local_copy
from decors import get_connection, remove, setup

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def webdav_upload():

    @task()
    def download(connection_id, **kwargs):
        
        params = kwargs['params']
        target = Variable.get("working_dir", default_var='/tmp/')
        source = params.get('source', '/tmp/')
        ssh_hook = get_connection(conn_id=connection_id, **kwargs)

        mappings = ssh2local_copy(ssh_hook=ssh_hook, source=source, target=target)
        
        return mappings

    @task()
    def load(mappings, **kwargs):
        params = kwargs['params']
        target = params.get('target', '/airflow-test')
        connection = Connection.get_connection_from_secrets('b2drop_webdav')
        options = {'webdav_hostname': f"https://{connection.host}{connection.schema}",
                   'webdav_login': connection.login,
                   'webdav_password': connection.get_password()
                   }
        print(f"Translated http to webdav: {options}")
        client = Client(options)
        res = client.mkdir(target)
        print(f"Creating {target}: {'ok' if res else 'failed'}")

        print(f"Starting upload -> {target}")
        for [local, true_name] in mappings.items():
            full_name = full_name = os.path.join(target, true_name)
            print(f"Processing {local} --> {full_name}")
            client.upload_sync(remote_path=full_name, local_path=local)

            # delete local
            os.unlink(local)

        return True

    @task
    def print_stats(res):
        print('Finished')

    setup_task = PythonOperator(
        python_callable=setup, task_id='setup_connection')
    a_id = setup_task.output['return_value']

    mappings = download(connection_id=a_id)
    res = load(mappings=mappings)
    
    en = PythonOperator(python_callable=remove, op_kwargs={
                        'conn_id': a_id}, task_id='cleanup')
    res >> en


dag = webdav_upload()
