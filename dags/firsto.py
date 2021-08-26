from datetime import timedelta

from airflow import DAG

from airflow.utils.dates import days_ago

from airflow.operators.bash import BashOperator

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
    t1 = BashOperator(task_id='print_date', bash_command='date')
    t2 = BashOperator(task_id='do_noting', bash_command='sleep 5')

    t3 = B2ShareOperator(task_id='task_b2sh', dag=dag, name='B2Share')

    t1 >> t2

