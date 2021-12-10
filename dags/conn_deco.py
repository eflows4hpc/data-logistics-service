from datetime import timedelta

from airflow import settings
from airflow.decorators import dag, task
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
    @task(multiple_outputs=True)
    def setup(**kwargs):
        print(f"Setting up the connection")
        session = settings.Session()
        params = kwargs['params']
        rrid = kwargs['run_id']
        oid = params.get('oid', '12121')
        key = params.get('key', "1JaqKIN1Jq+\\nf/HSoBpCCqmDPTQdT9Xq0AAAIIJKwpKCSsKSgAAAAH")
        user = params.get('user', 'eflows')

        conn_id = f"tmp_connection_{rrid}"
        extra = {"private_key": key}
        conn = Connection(
            conn_id=conn_id,
            conn_type='ssh',
            description='Automatically generated Connection',
            host='openssh-server',
            login=user,
            port=2222,
            extra=extra
        )

        session.add(conn)
        session.commit()
        return {'conn_id': conn_id, 'oid': oid}

    @task()
    def doing_nothing(oid, conn_id):
        print(f"Just doing nothing with {oid} and {conn_id}")
        return conn_id

    @task()
    def remove(conn_id):
        print(f"Removing conneciton {conn_id}")
        session = settings.Session()
        for con in session.query(Connection).all():
            print(con)

        session.remove(Connection.conn_id == conn_id)
        session.commit()

    res = setup()
    conn_id = doing_nothing(res['oid'], res['conn_id'])
    remove(conn_id)


dag = conn_decorator()
