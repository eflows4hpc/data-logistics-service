
import os
import tempfile
import json

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.models.connection import Connection
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from b2shareoperator import (add_file, create_draft_record, get_community,
                             submit_draft)
from decors import get_connection, remove, setup
from justreg import get_parameter
from datacat_integration.hooks import DataCatalogHook
from datacat_integration.connection import DataCatalogEntry

default_args = {
    'owner': 'airflow',
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


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def upload_example():

    @task()
    def load(connection_id, **kwargs):
        params = kwargs['params']
        target = Variable.get("working_dir", default_var='/tmp/')
        source = params.get('source', '/tmp/')

        ssh_hook = get_connection(conn_id=connection_id, **kwargs)
        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            lst = sftp_client.listdir(path=source)
            mappings = dict()
            for fname in lst:
                local = tempfile.mktemp(prefix='dls', dir=target)
                full_name = os.path.join(source, fname)
                sts = sftp_client.stat(full_name)
                if str(sts).startswith('d'):
                    print(f"{full_name} is a directory. Skipping")
                    continue

                print(f"Copying {connection_id}:{full_name} --> {local}")
                sftp_client.get(os.path.join(source, fname), local)
                mappings[local] = fname

        return mappings

    @task()
    def upload(files: dict, **kwargs):
        connection = Connection.get_connection_from_secrets('default_b2share')
        # hate such hacks:
        server = "https://" + connection.host
        token = connection.extra_dejson['access_token']

        params = kwargs['params']
        mid = params['mid']


        hook = DataCatalogHook()
        print("Connected to datacat via hook")
        entry = json.loads(hook.get_entry(datacat_type='storage_target', oid=mid))
        print('Got following metadata', entry)

        template = create_template(hrespo=entry['metadata'])
        community = get_community(server=server, community_id=template['community'])
        if not community:
            print("Not existing community")
            return -1
        cid, required = community
        missing = [r for r in required if r not in template]
        if any(missing):
            print(f"Community {cid} required field {missing} are missing. This could pose some problems")

        r = create_draft_record(server=server, token=token, record=template)
        if 'id' in r:
            print(f"Draft record created {r['id']} --> {r['links']['self']}")
        else:
            print('Something went wrong with registration', r, r.text)
            return -1

        for [local, true_name] in files.items():
            print(f"Uploading {local} --> {true_name}")
            _ = add_file(record=r, fname=local, token=token, remote=true_name)
            # delete local
            os.unlink(local)

        print("Submitting record for pubication")
        submitted = submit_draft(record=r, token=token)
        print(f"Record created {submitted}")

        return submitted['links']['publication']

    @task()
    def register(object_url, **kwargs):
        reg = get_parameter(parameter='register', default=False, **kwargs)
        if not reg:
            print("Skipping registration as 'register' parameter is not set")
            return 0

        hook = DataCatalogHook()
        print("Connected to datacat via hook")
    
        entry = DataCatalogEntry(name=f"DLS results {kwargs['run_id']}",
                                 url=object_url,
                                 metadata= {
                                    "author": "DLS on behalf of eFlows",
                                    "access": "hook-based"}
                                )
        try:
            r = hook.create_entry(datacat_type='dataset', entry=entry)
            print("Hook registration returned: ", r)
            return f"{hook.base_url}/dataset/{r}" 
        except ConnectionError as e:
            print('Registration failed', e)
            return -1

    setup_task = PythonOperator(python_callable=setup, task_id='setup_connection')
    a_id = setup_task.output['return_value']

    files = load(connection_id=a_id)
    uid = upload(files)

    en = PythonOperator(python_callable=remove, op_kwargs={
                        'conn_id': a_id}, task_id='cleanup')

    reg = register(object_url=uid)

    setup_task >> files >> uid >> reg >> en


dag = upload_example()
