from airflow.models.baseoperator import BaseOperator
from airflow.models.connection import Connection
import requests

def get_objects(server):
    lst = requests.get(urljoin(server, 'api/records')).json()
    return lst['hits']['hits']


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

        print(self.connection.host)

        print(f"Retrieving info from {self.connection.host}")
        lst = get_objects(server=self.connection.schema+self.connection.host)
        print(f"GOT: {lst}")
        return message
