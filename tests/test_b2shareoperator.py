import unittest
from airflow.utils.state import State
from dags.b2shareoperator import B2ShareOperator
from airflow import DAG
from airflow.models.taskinstance import TaskInstance

DEFAULT_DATE = '2019-10-03'
TEST_DAG_ID = 'test_my_custom_operator'

class B2ShareOperatorTest(unittest.TestCase):
   def setUp(self):
       self.dag = DAG(TEST_DAG_ID, schedule_interval='@daily', default_args={'start_date' : DEFAULT_DATE})
       self.op = B2ShareOperator(
           dag=self.dag,
           task_id='test',
           name='test_name'
       )
       self.ti = TaskInstance(task=self.op, execution_date=DEFAULT_DATE)

   def test_execute_no_trigger(self):
       self.ti.run(ignore_ti_state=True)
       assert self.ti.state == State.SUCCESS
       # Assert something related to tasks results