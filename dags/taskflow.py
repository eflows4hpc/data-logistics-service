
"Example of new taskflow api"

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
}
@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def taskflow_example():
    @task()
    def extract():
        return {'key': 'value', 'key2': 'value2'}

    @task(multiple_outputs=True)
    def transform(inps: dict):
        return {"keys": len(inps)}

    @task()
    def load(lengths: float):
        print(f"Total length value is: {lengths:.2f}")

    data = extract()
    summary = transform(data)
    load(summary["keys"])

dag = taskflow_example()
