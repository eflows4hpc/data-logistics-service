from airflow.models.baseoperator import BaseOperator
from airflow.models.connection import Connection
from airflow.providers.http.hooks.http import HttpHook
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
    fname = tempfile.mktemp(dir=target_dir)
    urllib.request.urlretrieve(url=url, filename=fname)
    return fname



class B2ShareOperator(BaseOperator):
    template_fields = ('target_dir',)

    def __init__(
            self,
            name: str,
            conn_id: str = 'default_b2share', # 'https://b2share-testing.fz-juelich.de/',
            target_dir: str = '/tmp/', 
            **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.conn_id = conn_id
        self.target_dir = target_dir
        print(self.target_dir)

    def execute(self, **kwargs):
        hook = HttpHook(http_conn_id=self.conn_id, method='GET')
        print(kwargs)
        params = kwargs['context']['params']
        oid = params['oid']
        hrespo = hook.run(endpoint=f"/api/records/{oid}")
        print(hrespo)

        flist = get_file_list(hrespo.json())
        print(flist)
        ti = kwargs['context']['ti']
        name_mappings = {}
        for fname, url in flist.items():
            tmpname = download_file(url=url, target_dir=self.target_dir)
            print(f"Processing: {fname} --> {url} --> {tmpname}")

            name_mappings[fname]=tmpname
            ti.xcom_push(key='local', value=tmpname)
            ti.xcom_push(key='remote', value=fname)
            break # for now only one file

        ti.xcom_push(key='mappins', value=name_mappings)
        return len(name_mappings)
