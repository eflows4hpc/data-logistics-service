import json
import os
import tempfile
import urllib
from urllib.parse import urljoin

import requests
from airflow.models.baseoperator import BaseOperator
from airflow.providers.http.hooks.http import HttpHook


def get_objects(server):
    lst = requests.get(urljoin(server, 'api/records')).json()
    return lst['hits']['hits']


def get_file_list(obj):
    file_url = obj['links']['files']
    fls = requests.get(file_url).json()

    return {it['key']: it['links']['self'] for it in fls['contents']}


def get_object_md(server, oid):
    obj = requests.get(urljoin(server, f"api/records/{oid}")).json()
    return obj


def download_file(url: str, target_dir: str):
    fname = tempfile.mktemp(dir=target_dir)
    urllib.request.urlretrieve(url=url, filename=fname)
    return fname

def get_record_template():
    return {"titles":[{"title":"DLS dataset record"}],
            "creators":[{"creator_name": "eflows4HPC"}],
            "descriptions":
              [{"description": "Output of eflows4HPC DLS", "description_type": "Abstract"}],
            "community" : "2d58eb08-af65-4cad-bd25-92f1a17d325b",
            "community_specific" :{
                "90942261-4637-4ac0-97b8-12e1edb38739": {"helmholtz centre": ["Forschungszentrum Jülich"]}
                },
            "open_access": True}

def get_schema(url):
    r = requests.get(url)
    return r.json()

def get_community(server, community_id):
    response = requests.get( url=urljoin(server, f"api/communities/{community_id}"),
                            headers={'Content-Type':'application/json'}).json()
    if 'status' in response:
        return None
    schema = get_schema(url=response['links']['schema'])
    return response['id'], schema['json_schema']['allOf'][0]['required']


def create_draft_record(server: str, token: str, record):
    response = requests.post( url=urljoin(server, 'api/records/'),
                      headers={'Content-Type':'application/json'},
                      data=json.dumps(record), params={'access_token': token})
    return response.json()

# the simplest version, target should be chunked
def add_file(record, fname: str, token: str, remote:str):
    jf = os.path.split(remote)[-1]
    return requests.put(url=f"{record['links']['files']}/{jf}",
                         params={'access_token': token},
                         headers={"Content-Type":"application/octet-stream"},
                         data=open(fname, 'rb'))

def submit_draft(record, token):
    pub = [{"op": "add", "path":"/publication_state", "value": "submitted"}]
    response = requests.patch(record['links']['self'],
                       headers={"Content-Type":"application/json-patch+json"},
                       data=json.dumps(pub), params={'access_token': token})
    return response.json()


class B2ShareOperator(BaseOperator):
    template_fields = ('target_dir',)

    def __init__(
            self,
            name: str,
            conn_id: str = 'default_b2share',  # 'https://b2share-testing.fz-juelich.de/',
            target_dir: str = '/tmp/',
            **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.conn_id = conn_id
        self.target_dir = target_dir

    def execute(self, **kwargs):
        hook = HttpHook(http_conn_id=self.conn_id, method='GET')
        params = kwargs['context']['params']
        oid = params['oid']

        hrespo = hook.run(endpoint=f"/api/records/{oid}")
        print(hrespo)

        flist = get_file_list(hrespo.json())

        ti = kwargs['context']['ti']
        name_mappings = {}
        for fname, url in flist.items():
            tmpname = download_file(url=url, target_dir=self.target_dir)
            print(f"Processing: {fname} --> {url} --> {tmpname}")

            name_mappings[fname] = tmpname
            ti.xcom_push(key='local', value=tmpname)
            ti.xcom_push(key='remote', value=fname)
            break  # for now only one file

        ti.xcom_push(key='mappings', value=name_mappings)
        return len(name_mappings)
