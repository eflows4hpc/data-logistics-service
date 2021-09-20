from datetime import timedelta

from airflow import DAG
from airflow.providers.sftp.operators.sftp import SFTPOperator
from airflow.utils.dates import days_ago

from b2shareoperator import B2ShareOperator

def_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)

}

with DAG('firsto', default_args=def_args, description='first dag', schedule_interval=timedelta(days=1), start_date=days_ago(2)) as dag:

    get_b2obj = B2ShareOperator(task_id='task_b2sh',
                                dag=dag,
                                name='B2Share',
                                target_dir="{{ var.value.source_path}}")

    put_file = SFTPOperator(
        task_id="upload_scp",
        ssh_conn_id="default_ssh",
        local_filepath="{{ti.xcom_pull(task_ids='task_b2sh', key='local')}}",
        remote_filepath="{{ti.xcom_pull(task_ids='task_b2sh',key='remote')}}",
        operation="put",
        create_intermediate_dirs=True,
        dag=dag)

    get_b2obj >> put_file
