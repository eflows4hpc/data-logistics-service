import unittest
from unittest.mock import patch, Mock

from airflow import DAG
from airflow.models.taskinstance import TaskInstance
from airflow.utils.dates import days_ago
from airflow.utils.state import State

from dags.b2shareoperator import B2ShareOperator, get_file_list

DEFAULT_DATE = '2019-10-03'
TEST_DAG_ID = 'test_my_custom_operator'


class B2ShareOperatorTest(unittest.TestCase):
    def setUp(self):
       self.dag = DAG(TEST_DAG_ID, schedule_interval='@daily',
                      default_args={'start_date': days_ago(2)}, params={"oid": "111"})
       self.op = B2ShareOperator(
           dag=self.dag,
           task_id='test',
           name='test_name'
       )
       self.ti = TaskInstance(task=self.op, execution_date=days_ago(1))


    @patch('dags.b2shareoperator.HttpHook')
    @patch('dags.b2shareoperator.get_file_list')
    @patch('dags.b2shareoperator.download_file')
    def test_alt_execute_no_trigger(self, down, gfl, ht):
        gfl.return_value = {'ooo.txt': 'htt://file/to/download'}
        down.return_value = 'tmp_name'

        self.ti.run(ignore_ti_state=False)
        print(self.ti.state)
        self.assertEqual(State.SUCCESS, self.ti.state)
        # Assert something related to tasks results

    def test_get_files(self):
        with patch('dags.b2shareoperator.requests.get') as get:
            m = Mock()
            m.json.return_value = {'contents': [{'key': 'veryimportant.txt', 'links':{'self': 'http://foo.bar'}}]}
            get.return_value = m
            ret = get_file_list(obj={'links': {'files': ['bla']}})
            self.assertEqual(len(ret), 1)
    
