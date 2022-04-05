
import os
import tempfile

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.models.connection import Connection
from airflow.operators.python import PythonOperator
from airflow.providers.http.hooks.http import HttpHook
from airflow.utils.dates import days_ago

from b2shareoperator import (add_file, create_draft_record, get_community,
                             submit_draft)
from decors import get_connection, remove, setup
from just_reg import get_parameter, get_record

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

        hook = HttpHook(http_conn_id='datacat', method='GET')
        hrespo = hook.run(endpoint=f"storage_target/{mid}").json()['metadata']
        print(hrespo)
        template = create_template(hrespo=hrespo)
        community = get_community(
            server=server, community_id=template['community'])
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

        for [local, true_name] in files.items():
            print(f"Uploading {local} --> {true_name}")
            _ = add_file(record=r, fname=local, token=token, remote=true_name)
            # delete local
            os.unlink(local)

        print("Submitting record for pubication")
        submitted = submit_draft(record=r, token=token)
        print(f"Record created {submitted}")

        return submitted['links']['self']

    @task()
    def register(object_url, **kwargs):
        reg = get_parameter(parameter='register', default=False, **kwargs)
        if not reg:
            print("Skipping registration as 'register' parameter is not set")
            return 0

        connection = Connection.get_connection_from_secrets(
            'datacat')
        server = connection.get_uri()
        print(f"Registring\n\t{object_url}\n with\n\t {server}")

        # auth_type empty to overwrite http basic auth
        hook = HttpHook(http_conn_id='datacat', auth_type=lambda x, y: None)
        res = hook.run(endpoint='token',
                       data={'username': connection.login, 'password': connection.password}
                       )

        if res.status_code != 200:
            print("Unable to authenticate. Breaking. Check `datacat` for creds")
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



    setup_task = PythonOperator(python_callable=setup, task_id='setup_connection')
    a_id = setup_task.output['return_value']

    files = load(connection_id=a_id)
    uid = upload(files)

    en = PythonOperator(python_callable=remove, op_kwargs={
                        'conn_id': a_id}, task_id='cleanup')

    reg = register(object_url=uid)

    setup_task >> files >> uid >> en


dag = upload_example()
