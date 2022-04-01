from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.operators.bash import BashOperator
from airflow.providers.http.hooks.http import HttpHook
from airflow.utils.dates import days_ago


default_args = {
    'owner': 'airflow',
}


def get_record(name, url):
    return {
        "name": name,
        "url": url,
        "metadata": {
            "author": "DLS on behalf of eFlows",
        }
    }

def get_parameter(parameter, default=False, **kwargs):
    params = kwargs['params']
    return params.get(parameter, default)

@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def datacat_registration_example():

    @task()
    def register(object_url, **kwargs):
        reg = get_parameter(parameter='register', default=False, **kwargs)
        if not reg:
            print("Skipping registration as 'register' parameter is not set")
            return 0

        connection = Connection.get_connection_from_secrets(
            'datacat_connection')
        server = connection.get_uri()
        print(f"Registring\n\t{object_url}\n with\n\t {server}")

        # auth_type empty to overwrite http basic auth
        hook = HttpHook(http_conn_id='datacat_connection', auth_type=lambda x, y: None)
        res = hook.run(endpoint='token',
                       data={'username': connection.login, 'password': connection.password}
                       )

        if res.status_code != 200:
            print("Unable to authenticate. Breaking. Check `datacat_conneciton` for creds")
            return -1

        token = res.json()['access_token']
        auth_header = {'Authorization': f"Bearer {token}"}

        r = hook.run(endpoint='dataset', headers=auth_header,
                    json=get_record(name=f"DLS results {kwargs['run_id']}", url=object_url)
                    )
        if r.status_code==200:
            d_id = r.json()[0]
            print(f"Registered sucesfully: {hook.base_url}/dataset/{d_id}")
            return d_id
        print(f"Registraton failed: {r.text}")
        return -1



    step1 = BashOperator(bash_command='ls', task_id='nothing')
    step2 = register(
        object_url='https://b2share-testing.fz-juelich.de/records/7a12fda26b2a4d248f96d012d54769b7')

    step1 >> step2


dag = datacat_registration_example()
