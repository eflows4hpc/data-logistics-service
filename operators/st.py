#!/usr/bin/env python3

import argparse
import getpass
import json
from urllib.parse import urljoin
import sys

import requests
import urllib.request
import tempfile

server='https://b2share-testing.fz-juelich.de/'

def get_objects():
    lst = requests.get(urljoin(server, 'api/records')).json()
    return lst['hits']['hits']


def get_object_md(oid):
    obj= requests.get(urljoin(server, f"api/records/{oid}")).json()
    return obj

def get_file_list(obj):
    file_url = obj['links']['files']
    fls = requests.get(file_url).json()

    return {it['key']: it['links']['self'] for it in fls['contents']}

def download_file(url: str, target_dir: str):
    _, fname = tempfile.mkstemp(dir=target_dir)
    urllib.request.urlretrieve(url=url, filename=fname)
    return fname

if __name__=="__main__":
    oid = 'b38609df2b334ea296ea1857e568dbea'
    obj = get_object_md(oid=oid)
    flist = get_file_list(obj=obj)
    print(flist) 
