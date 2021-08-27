from airflow.models.baseoperator import BaseOperator
from airflow.models.connection import Connection
import requests
from urllib.parse import urljoin
import tempfile
import urllib

def get_objects(server):
    lst = requests.get(urljoin(server, 'api/records')).json()
    return lst['hits']['hits']

def get_file_list(obj):
    file_url = obj['links']['files']
    fls = requests.get(file_url).json()

    return {it['key']: it['links']['self'] for it in fls['contents']}

def get_object_md(server, oid):
    obj= requests.get(urljoin(server, f"api/records/{oid}")).json()
    return obj

def download_file(url: str, target_dir: str):
    
    fname = tempfile.mkstemp(dir=target_dir)
    urllib.request.urlretrieve(url=url, filename=fname)
    return fname


server='https://b2share-testing.fz-juelich.de/'

class B2ShareOperator(BaseOperator):

    def __init__(
            self,
            name: str,
            conn_id: str = 'default_b2share',
            **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.conn_id = conn_id
        print(kwargs)

    def execute(self, context):

        connection = Connection.get_connection_from_secrets(self.conn_id)
        print(f"Rereiving data from {connection.get_uri()}")

        lst = get_objects(server=connection.get_uri())
        flist = {o['id']: [f['key'] for f in o['files']] for o in lst}
        print(f"GOT: {flist}")
        print(self.params)
        return len(flist)
