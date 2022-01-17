
from typing import Dict
from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.utils.dates import days_ago
from airflow import  settings
import logging
from sqlalchemy.orm.session import Session as SASession
from datacat_integration.secrets import DataCatConnectionWithSecrets

from datacat_integration.hooks import DataCatalogHook

default_args = {
    'owner': 'airflow',
}

connections_type = "airflow_connections"
substring_start = len(connections_type) + 1
substring_end = substring_start + 36 # length of a UUID4

log = logging.getLogger(__name__)

def get_conn_name(datacat_type: str, oid: str):
    return "{}/{}-connection".format(datacat_type, oid)

def get_normal_or_secret_property(key: str, props: Dict[str,str], secrets: Dict[str, str], default_value = None):
    return props.get(key, secrets.get(key, default_value))


def get_connection(hook: DataCatalogHook, datacat_type: str, oid: str):
    conn_id = get_conn_name(datacat_type, oid)
    secrets_connection = DataCatConnectionWithSecrets(hook.connection.url, hook.connection.user, hook.connection._password)
    datacat_entry: Dict[str,str] = secrets_connection.get_object(datacat_type, oid)['metadata']
    datacat_entry_secrets = secrets_connection.get_all_secret_key_value(datacat_type, oid)
    extra={}
    predefined_keys = ['conn_type', 'description', 'host', 'login', 'password', 'schema', 'port']
    # build extra from non-predefined keys
    for key in datacat_entry:
        if key not in predefined_keys:
            extra[key] = datacat_entry[key]
    
    for key in datacat_entry_secrets:
        if key not in predefined_keys:
            extra[key] = datacat_entry_secrets[key]

    
    return Connection(
        conn_id=conn_id,
        conn_type=get_normal_or_secret_property('conn_type', datacat_entry, datacat_entry_secrets),
        description=get_normal_or_secret_property('description', datacat_entry, datacat_entry_secrets, 'Automatically generated Connection from the datacatalog object {}/{}'.format(connections_type, oid)),
        host=get_normal_or_secret_property('host', datacat_entry, datacat_entry_secrets),
        login=get_normal_or_secret_property('login', datacat_entry, datacat_entry_secrets),
        password=get_normal_or_secret_property('password', datacat_entry, datacat_entry_secrets),
        schema=get_normal_or_secret_property('schema', datacat_entry, datacat_entry_secrets),
        port=int(get_normal_or_secret_property('port', datacat_entry, datacat_entry_secrets)),
        extra=extra
    )


@dag(default_args=default_args, schedule_interval='@hourly', start_date=days_ago(1), tags=['dls-service-dag'])
def sync_connections():

    @task
    def list_catalog_connections(**kwargs):
        hook = DataCatalogHook("datacatalog")
        objects = hook.list_type(connections_type)
        oid_list = [element[1] for element in objects]
        return oid_list

    @task
    def list_airflow_connections(**kwargs):
        session : SASession = settings.Session()
        conns = session.query(Connection).filter(Connection.conn_id.like("{}/%-connection".format(connections_type)))
        oid_list = [conn.conn_id[substring_start:substring_end] for conn in conns]
        return oid_list

    @task 
    def get_add_list(catalog_connections, airflow_connections, **kwargs):
        return list(set(catalog_connections).difference(airflow_connections))
    
    @task 
    def get_remove_list(catalog_connections, airflow_connections, **kwargs):
        return list(set(airflow_connections).difference(catalog_connections))

    @task
    def remove_connections(oid_list, **kwargs):
        log.info("Going to remove from conections: " + ','.join(oid_list))
        session : SASession = settings.Session()
        for oid in oid_list:
            session.query(Connection).filter(Connection.conn_id == get_conn_name(connections_type, oid)).delete()
        session.commit()
    
    @task
    def add_connections(oid_list, **kwargs):
        log.info("Going to add to conections: " + ','.join(oid_list))
        hook = DataCatalogHook("datacatalog")
        connections = []
        for oid in oid_list:
            connections.append(get_connection(hook, connections_type, oid))
        
        session = settings.Session()
        # no check for existsnce necessary, since it is handled by get_add_list()
        for conn in connections: 
            session.add(conn)

        session.commit()

    cat_conn = list_catalog_connections()
    air_conn = list_airflow_connections()

    add_list = get_add_list(cat_conn, air_conn)
    remove_list = get_remove_list(cat_conn, air_conn)

    add_connections(add_list)

    remove_connections(remove_list)


dag = sync_connections()
