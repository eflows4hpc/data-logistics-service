
import os
import tempfile

from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.utils.dates import days_ago

from b2shareoperator import (add_file, create_draft_record,
                             get_record_template, submit_draft)


default_args = {
    'owner': 'airflow',
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def upload_example():
    @task()
    def load(**kwargs):
        params = kwargs['params']
        target = params.get('target', '/tmp/')
        source = params.get('source', '/tmp/')
        connection_id = params.get('connection', 'default_ssh')
        
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
        print(f"Server: {server} + {token}")
        
        template = get_record_template()
        r = create_draft_record(server=server, token=token, record=template)
        print(r)
        print(f"Draft record created {r['id']} --> {r['links']['self']}")

        for [local, true_name] in files.items():
            print(f"Uploading {local} --> {true_name}")
            up = add_file(record=r, fname=local, token=token, remote=true_name)

        print("Submitting record for pubication")
        submitted = submit_draft(record=r, token=token)
        print(f"Record created {submitted['id']}")

    files = load()
    upload(files)


dag = upload_example()