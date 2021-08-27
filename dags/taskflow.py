
"Example of new taskflow api"

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from airflow.models.connection import Connection
import requests
import urllib.request
import tempfile
from b2shareoperator import get_file_list, download_file, get_object_md

default_args = {
    'owner': 'airflow',
}

@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['example'])
def taskflow_example():
    @task()
    def extract(oid: str):
        connection = Connection.get_connection_from_secrets('default_b2share')
        server = connection.get_uri()
        print(f"Rereiving data from {server}")
        obj = get_object_md(server=server, oid=oid)
        print(f"Object: {obj}")
        flist = get_file_list(obj)
        return flist

    @task(multiple_outputs=True)
    def transform(flist: dict):
        name_mappings = {}
        for fname, url in flist.items():
            print(f"Processing: {fname} --> {url}")
            tmpname = download_file(url=url, target_dir='/tmp/')
            name_mappings[fname]=tmpname
        return name_mappings

    @task()
    def load(files: dict):
        print(f"Total files downloaded: {len(files)}")

    data = extract(oid = 'b38609df2b334ea296ea1857e568dbea')
    summary = transform(data)
    load(summary["keys"])

dag = taskflow_example()
