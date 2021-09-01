from airflow.models import DagBag
import unittest

class TestADag(unittest.TestCase):
   @classmethod
   def setUpClass(cls):
       cls.dagbag = DagBag()

   def test_dag_loaded(self):
       dag = self.dagbag.get_dag(dag_id='firsto')
       assert self.dagbag.import_errors == {}
       assert dag is not None
       assert len(dag.tasks) == 4