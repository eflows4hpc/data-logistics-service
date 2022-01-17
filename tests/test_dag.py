import unittest

from airflow.models import DagBag


class TestADag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dagbag = DagBag()

    def test_dag_loaded(self):
        dag = self.dagbag.get_dag(dag_id='firsto')
        assert self.dagbag.import_errors == {}
        assert dag is not None
        self.assertEqual(len(dag.tasks), 2, f"Actually: {len(dag.tasks)}")

    def test_tf_loaded(self):
        dag = self.dagbag.get_dag(dag_id='taskflow_example')
        assert self.dagbag.import_errors == {}
        assert dag is not None
        self.assertEqual(len(dag.tasks), 5, f"Actually: {len(dag.tasks)}")
