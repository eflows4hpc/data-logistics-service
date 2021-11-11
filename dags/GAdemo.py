from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator

def_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)

}

def train_model():
    print('Will start model training')

with DAG('GAtest', default_args=def_args, description='testing GA', schedule_interval=timedelta(days=1), start_date=days_ago(2)) as dag:
    s1 = FileSensor(task_id='file_sensor', filepath='/work/afile.txt')
    t1 = BashOperator(task_id='move_data', bash_command='date')
    t2 = PythonOperator(task_id='train_model', python_callable=train_model)
    t3 = BashOperator(task_id='eval_model', bash_command='echo "evaluating"')
    t4 = DummyOperator(task_id='upload_model_to_repo')
    t5 = DummyOperator(task_id='publish_results')
    
    s1 >> t1 >> t2 >> t4 
    t2 >> t3 >> t5 
