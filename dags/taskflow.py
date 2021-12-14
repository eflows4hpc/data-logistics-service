
from airflow import settings
from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.models import Variable
from airflow.utils.dates import days_ago
import os

from b2shareoperator import (download_file, get_file_list, get_object_md,
                             get_objects)

default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def taskflow_example():

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

    @task(multiple_outputs=True)
    def extract(conn_id, **kwargs):
        connection = Connection.get_connection_from_secrets('default_b2share')
        server = connection.get_uri()
        print(f"Rereiving data from {server}")

        params = kwargs['params']
        if 'oid' not in params:  # {"oid":"b38609df2b334ea296ea1857e568dbea"}
            print("Missing object id in pipeline parameters")
            lst = get_objects(server=server)
            flist = {o['id']: [f['key'] for f in o['files']] for o in lst}
            print(f"Objects on server: {flist}")
            return -1  # non zero exit code is a task failure

        oid = params['oid']

        obj = get_object_md(server=server, oid=oid)
        print(f"Retrieved object {oid}: {obj}")
        flist = get_file_list(obj)
        return flist

    @task(multiple_outputs=True)
    def transform(flist: dict):
        name_mappings = {}
        tmp_dir = Variable.get("working_dir", default_var='/tmp/')
        print(f"Local working dir is: {tmp_dir}")
        
        for fname, url in flist.items():
            print(f"Processing: {fname} --> {url}")
            tmpname = download_file(url=url, target_dir=tmp_dir)
            name_mappings[fname] = tmpname
        return name_mappings

    @task()
    def load(connection_id, files: dict, **kwargs):
        print(f"Total files downloaded: {len(files)}")
        params = kwargs['params']
        target = params.get('target', '/tmp/')
        
        print(f"Using {connection_id} connection")
        
        ssh_hook = SSHHook(ssh_conn_id=connection_id)
        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            for [truename, local] in files.items():
                print(f"Copying {local} --> {connection_id}:{os.path.join(target, truename)}")
                sftp_client.put(local, os.path.join(target, truename))
                # or separate cleanup task?
                os.unlink(local)

        return connection_id

    @task()
    def remove(conn_id):
        print(f"Removing conneciton {conn_id}")
        session = settings.Session()
        for con in session.query(Connection).all():
            print(con)

        session.query(Connection).filter(Connection.conn_id == conn_id).delete()
        session.commit()

    conn_id = setup()
    data = extract(conn_id)
    files = transform(data)
    ucid = load(connection_id = conn_id, files=files)
    remove(conn_id=ucid)

dag = taskflow_example()
