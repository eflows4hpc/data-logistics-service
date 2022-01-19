
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from airflow.hooks.base import BaseHook

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def test_secrets_backend():
    @task()
    def get_print_and_return_conenction():
        conn = BaseHook.get_connection('860355e9-975f-4253-9421-1815e20c879b')
        print(conn.get_extra())

    get_print_and_return_conenction()


dag = test_secrets_backend()
