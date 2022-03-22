from airflow import settings
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.models.connection import Connection
from airflow.providers.hashicorp.hooks.vault import VaultHook


def create_temp_connection(rrid, params):
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


def get_connection(conn_id):
    if conn_id.startswith('vault'):
        vault_hook = VaultHook(vault_conn_id='my_vault')
        con = vault_hook.get_secret(
            secret_path=f"/ssh-credentials/{conn_id[6:]}")
        print(f"Got some values from vault {list(con.keys())}")

        # for now SSH is hardcoded
        host = con.get('host', 'bsc')
        port = int(con.get('port', 22))
        hook = SSHHook(remote_host=host, port=port, username=con['userName'])
        # key in vault should be in form of formated string:
        # -----BEGIN OPENSSH PRIVATE KEY-----
        # b3BlbnNzaC1rZXktdjEAAAAA
        # ....
        hook.pkey = hook._pkey_from_private_key(private_key=con['privateKey'])
        return hook

    # otherwise use previously created temp connection
    return SSHHook(ssh_conn_id=conn_id)


def setup(**kwargs):
    params = kwargs['params']
    print("Setting up the connection")

    if 'vault_id' in params:
        print('Retrieving connection details from vault')
        return f"vault_{params['vault_id']}"

    # otherwise use creds provided in request
    return create_temp_connection(rrid=kwargs['run_id'], params=params)


def remove(conn_id):
    if conn_id.startswith('vault'):
        return

    print(f"Removing conneciton {conn_id}")
    session = settings.Session()
    for con in session.query(Connection).all():
        print(con)

    session.query(Connection).filter(Connection.conn_id == conn_id).delete()
    session.commit()


def get_conn_id(**kwargs):
    ti = kwargs['ti']
    conn_id = ti.xcom_pull(key='return_value', task_ids='setup_connection')
    return conn_id
