from datetime import timedelta

from airflow import settings
from airflow.decorators import dag, task
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.models.connection import Connection
from airflow.utils.dates import days_ago

def_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)

}

@dag(default_args=def_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def conn_decorator():
    @task
    def setup(**kwargs):
        print(f"Setting up the connection")
        
        params = kwargs['params']
        rrid = kwargs['run_id']
        host = params.get('host')
        port = params.get('port', 2222)
        key = params.get('key')
        user = params.get('login', 'eflows')

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
    def doing_nothing(conn_id, **kwargs):
        print(f"Just doing nothing with {conn_id}")
        params = kwargs['params']
        print(f"This task recieved following kwargs: {params}")

        ssh_hook = SSHHook(ssh_conn_id=conn_id)
        with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            print("Connected")

        return conn_id

    @task()
    def remove(conn_id):
        print(f"Removing conneciton {conn_id}")
        session = settings.Session()
        for con in session.query(Connection).all():
            print(con)

        session.query(Connection).filter(Connection.conn_id == conn_id).delete()
        session.commit()

    conn_id = setup()
    conn_id = doing_nothing(conn_id=conn_id)
    remove(conn_id)


dag = conn_decorator()
