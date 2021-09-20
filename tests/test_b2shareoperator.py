import unittest
from unittest.mock import Mock, patch

from airflow import DAG
from airflow.models.taskinstance import TaskInstance
from airflow.utils.dates import days_ago
from airflow.utils.state import State

from dags.b2shareoperator import (B2ShareOperator, download_file,
                                  get_file_list, get_object_md, get_objects)

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

        self.ti.run(ignore_ti_state=True, test_mode=True)
        print(self.ti.state)

        self.assertEqual(State.SUCCESS, self.ti.state)

        # return value
        ret = self.ti.xcom_pull()
        self.assertEqual(ret, 1, f"{ret}")

        lcl = self.ti.xcom_pull(key='local')
        rmt = self.ti.xcom_pull(key='remote')
        mps = self.ti.xcom_pull(key='mappings')
        self.assertEqual(len(mps), 1, f"{mps}")
        self.assertDictEqual(
            mps, {'ooo.txt': 'tmp_name'}, f"unexpecting mappings: {mps}")
        self.assertEqual(lcl, 'tmp_name', f"unexpecting local name: {lcl}")
        self.assertEqual(rmt, 'ooo.txt', f"unexpected remote name: {rmt}")

    def test_get_files(self):
        with patch('dags.b2shareoperator.requests.get') as get:
            m = Mock()
            m.json.return_value = {'contents': [
                {'key': 'veryimportant.txt', 'links': {'self': 'http://foo.bar'}}]}
            get.return_value = m
            ret = get_file_list(obj={'links': {'files': ['bla']}})
            self.assertEqual(len(ret), 1)

    def test_download_file(self):
        with patch('dags.b2shareoperator.urllib.request.urlretrieve') as rr:
            with patch('dags.b2shareoperator.tempfile.mktemp') as mt:
                mt.return_value = '/tmp/val'
                fname = download_file(
                    url='http://foo.bar', target_dir='/no/tmp/')
                self.assertEqual(fname, '/tmp/val')

    def test_get_md(self):
        with patch('dags.b2shareoperator.requests.get') as get:
            m = Mock()
            rval = {'links': {'files': ['a', 'b']}}
            m.json.return_value = rval
            get.return_value = m
            r = get_object_md(server='foo', oid='bar')
            self.assertDictEqual(rval, r)

    def test_get_objects(self):
        with patch('dags.b2shareoperator.requests.get') as get:
            m = Mock()
            rval = {'hits': {'hits': ['a', 'b']}}
            m.json.return_value = rval
            get.return_value = m
            r = get_objects(server='foo')
            self.assertListEqual(['a', 'b'], r)
