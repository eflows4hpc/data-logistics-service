from datetime import timedelta

from airflow.decorators import dag, task
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from decors import get_connection, remove, setup

def_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}


@dag(default_args=def_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def conn_decorator():

    @task()
    def doing_nothing(conn_id, **kwargs):
        print(f"Using connection {conn_id}")

        ssh_hook = get_connection(conn_id=conn_id, **kwargs)
        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            print("Connected")
            lst = sftp_client.listdir(path='/tmp/')
            for f in lst:
                print(f)

        return conn_id

    conn_id = PythonOperator(python_callable=setup, task_id='setup_connection')
    # another way of mixing taskflow and classical api:
    a_id = conn_id.output['return_value']
    dno = doing_nothing(conn_id=a_id)
    en = PythonOperator(python_callable=remove, op_kwargs={
                        'conn_id': dno}, task_id='cleanup')

    conn_id >> dno >> en


dag = conn_decorator()
