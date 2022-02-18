
import os
import tempfile

from airflow import settings
from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.utils.dates import days_ago

from b2shareoperator import (add_file, create_draft_record,
                             get_record_template, submit_draft)

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def upload_example():
    @task
    def setup(**kwargs):
        print(f"Setting up the connection")
        
        params = kwargs['params']
        rrid = kwargs['run_id']
        host = params.get('host')
        port = params.get('port', 2222)
        user = params.get('login', 'eflows')
        key = params.get('key')

        conn_id = f"tmp_connection_{rrid}"
        extra = {"private_key": key}
        conn = Connection(
            conn_id=conn_id,
            conn_type='ssh',
            description='Automatically generated Connection',
            host=host,
            login=user,
            port=port,
            extra=extra
        )

        session = settings.Session()
        session.add(conn)
        session.commit()
        print(f"Connection {conn_id} created")
        return conn_id

    @task()
    def load(connection_id, **kwargs):
        params = kwargs['params']
        target = params.get('target', '/tmp/')
        source = params.get('source', '/tmp/')
        
        ssh_hook = SSHHook(ssh_conn_id=connection_id)
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
        
        template = {
            "titles" : [{"title":hrespo['title']}],
            "creators" : [{"creator_name": hrespo['creator_name']}],
            "descriptions" :[
                {
                    "description": hrespo['description'], 
                    "description_type": "Abstract"
                }
                ],
            "community" : "2d58eb08-af65-4cad-bd25-92f1a17d325b",
            "community_specific" :{
                "90942261-4637-4ac0-97b8-12e1edb38739": {"helmholtz centre": ["Forschungszentrum Jülich"]}
                },
            "open_access": hrespo['open_access']=="True"
            }
        r = create_draft_record(server=server, token=token, record=template)
        print(r)
        print(f"Draft record created {r['id']} --> {r['links']['self']}")

        for [local, true_name] in files.items():
            print(f"Uploading {local} --> {true_name}")
            up = add_file(record=r, fname=local, token=token, remote=true_name)

        print("Submitting record for pubication")
        submitted = submit_draft(record=r, token=token)
        print(f"Record created {submitted['id']}")
        return submitted['id']

    @task()
    def remove(conn_id, uid):
        print(f"Upload {uid} completed. Removing conneciton {conn_id}")
        session = settings.Session()
        for con in session.query(Connection).all():
            print(con)

        session.query(Connection).filter(Connection.conn_id == conn_id).delete()
        session.commit()

    conn_id = setup()
    files = load(connection_id=conn_id)
    uid = upload(files)
    remove(conn_id=conn_id, uid=uid)


dag = upload_example()
