import os
import shutil
import requests

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator

from decors import setup, get_connection, remove

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def transfer_image():

    @task
    def stream_upload(connection_id, **kwargs):
        params = kwargs['params']
        target = params.get('target', '/tmp/')
        image_id = params.get('image_id', 'wordcount_skylake.sif')
        url = f"https://bscgrid20.bsc.es/image_creation/images/download/{image_id}"

        print(f"Putting {url} --> {target} connection")
        ssh_hook = get_connection(conn_id=connection_id, **kwargs)

        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            ssh_client.exec_command(command=f"mkdir -p {target}")
            with requests.get(url, stream=True, verify=False) as r:
                with sftp_client.open(os.path.join(target, image_id), 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

    setup_task = PythonOperator(
        python_callable=setup, task_id='setup_connection')
    a_id = setup_task.output['return_value']
    cleanup_task = PythonOperator(python_callable=remove, op_kwargs={
                                  'conn_id': a_id}, task_id='cleanup')

    setup_task >> stream_upload(connection_id=a_id) >> cleanup_task


dag = transfer_image()
