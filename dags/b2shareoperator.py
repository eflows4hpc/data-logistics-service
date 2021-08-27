from airflow.models.baseoperator import BaseOperator
from airflow.models.connection import Connection
import requests
from urllib.parse import urljoin

def get_objects(server):
    lst = requests.get(urljoin(server, 'api/records')).json()
    return lst['hits']['hits']

server='https://b2share-testing.fz-juelich.de/'

class B2ShareOperator(BaseOperator):

    def __init__(
            self,
            name: str,
            conn_id: str = 'default_b2share',
            **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.connection = Connection.get_connection_from_secrets(conn_id)

    def execute(self, context):
        message = "Hello {}".format(self.name)
        print(message)

        print(self.connection.get_uri())

        #print(f"Retrieving info from {self.connection.host}")
        lst = get_objects(server=server)
        print(f"GOT: {lst}")
        print(self.params)
        return message
