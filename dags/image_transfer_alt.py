import os
import shutil
import requests

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from justreg import get_parameter
from decors import setup, get_connection, remove

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def transfer_image_alt():

    @task
    def im_download(connection_id, **kwargs):

        work_dir = Variable.get("working_dir", default_var='/tmp/')

        image_id = get_parameter(
            'image_id', default='wordcount_skylake.sif', **kwargs)
        url = f"https://bscgrid20.bsc.es/image_creation/images/download/{image_id}"

        print(f"Putting {url} --> {work_dir} connection")
        with requests.get(url, stream=True, verify=False) as r:
            with open(os.path.join(work_dir, image_id), 'wb') as f:
                shutil.copyfileobj(r.raw, f)

    @task
    def im_upload(connection_id, **kwargs):
        if not get_parameter('upload', False, **kwargs):
            print('Skipping upload')
            return 0
        work_dir = Variable.get("working_dir", default_var='/tmp/')
        target = get_parameter('target', default='/tmp/', **kwargs)
        image_id = get_parameter(
            'image_id', default='wordcount_skylake.sif', **kwargs)
        ssh_hook = get_connection(conn_id=connection_id, **kwargs)
        print(
            f"Copying local {os.path.join(work_dir, image_id)} -> {connection_id}:{target}")
        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            ssh_client.exec_command(command=f"mkdir -p {target}")
            with open(os.path.join(work_dir, image_id), 'rb') as r:
                with sftp_client.open(os.path.join(target, image_id), 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

        print('Removing local copy')
        os.unlink(os.path.join(work_dir, image_id))

    setup_task = PythonOperator(
        python_callable=setup, task_id='setup_connection')
    a_id = setup_task.output['return_value']

    cleanup_task = PythonOperator(python_callable=remove, op_kwargs={
                                  'conn_id': a_id}, task_id='cleanup')

    setup_task >> im_download(connection_id=a_id) >> im_upload(
        connection_id=a_id) >> cleanup_task


dag = transfer_image_alt()
