import unittest
from airflow.utils.state import State
from airflow.utils.dates import days_ago
from dags.b2shareoperator import B2ShareOperator
from airflow import DAG
from airflow.models.taskinstance import TaskInstance

DEFAULT_DATE = '2019-10-03'
TEST_DAG_ID = 'test_my_custom_operator'

class B2ShareOperatorTest(unittest.TestCase):
   def setUp(self):
       self.dag = DAG(TEST_DAG_ID, schedule_interval='@daily', default_args={'start_date' : days_ago(2)})
       self.op = B2ShareOperator(
           dag=self.dag,
           task_id='test',
           name='test_name'
       )
       self.ti = TaskInstance(task=self.op, execution_date=days_ago(1))

   def test_execute_no_trigger(self):
       self.ti.run(ignore_ti_state=True)
       print(self.ti.state)
       self.assertEqual(State.SUCCESS, self.ti.state)
       # Assert something related to tasks results