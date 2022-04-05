
from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.operators.bash import BashOperator
from airflow.providers.http.hooks.http import HttpHook
from airflow.utils.dates import days_ago
from datacat_integration.hooks import DataCatalogHook
from datacat_integration.connection import DataCatalogEntry


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

def create_template(hrespo):
    return {
        "titles": [{"title": hrespo['title']}],
        "creators": [{"creator_name": hrespo['creator_name']}],
        "descriptions": [
            {
                "description": hrespo['description'],
                "description_type": "Abstract"
            }
        ],
        "community": "2d58eb08-af65-4cad-bd25-92f1a17d325b",
        "community_specific": {
            "90942261-4637-4ac0-97b8-12e1edb38739": {"helmholtz centre": ["Forschungszentrum Jülich"]}
        },
        "open_access": hrespo['open_access'] == "True"
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

        hook = DataCatalogHook()
        print("Connected to datacat via hook", hook.list_type('dataset'))
    
        entry = DataCatalogEntry(name=f"DLS results {kwargs['run_id']}",
                                 url=object_url, 
                                 metadata= {
                                    "author": "DLS on behalf of eFlows",
                                    "access": "hook-based"}
                                    )
        try:
            r = hook.create_entry(datacat_type='dataset', entry=entry)
            print("Hook registration returned: ", r)
            return r 
        except ConnectionError as e:
            print('Registration failed', e)
            return -1

    @task
    def get_template():
        hook = DataCatalogHook()
        print("Connected to datacat via hook", hook.list_type('dataset'))

        mid = '71e863ac-aee6-4680-a57c-de318530b71e'
        entry = hook.get_entry(datacat_type='storage_target', oid=mid)
        print(entry)
        print(entry.metadata)
        print('---')
        print(get_template(entry.metadata))




    step1 = BashOperator(bash_command='ls', task_id='nothing')
    step2 = register(
        object_url='https://b2share-testing.fz-juelich.de/records/7a12fda26b2a4d248f96d012d54769b7')

    step3 = get_template()
    step1 >> step2 >> step3


dag = datacat_registration_example()
