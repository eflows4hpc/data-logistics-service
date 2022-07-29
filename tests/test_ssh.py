import tempfile
import unittest
from unittest.mock import MagicMock, patch
import os

from dags.uploadflow import ssh2local_copy, copy_streams

class TestSSH(unittest.TestCase):

    @patch('dags.uploadflow.tempfile.mktemp')
    def test_copy_files(self, tmp):
        tmp.side_effect = ['tmpA', 'tmpB']

        my_hook = MagicMock()
        a = MagicMock()
        a.return_value = ['a', 'c']
        stat = MagicMock(side_effect=['elo', 'elo'])
        cpy = MagicMock(return_value=False)
        my_hook.get_conn().__enter__().open_sftp().listdir = a
        my_hook.get_conn().__enter__().open_sftp().stat = stat
        my_hook.get_conn().__enter__().open_sftp().open().__enter__().raw.read = cpy

        mapps = ssh2local_copy(ssh_hook=my_hook, source='srcZ', target='trg')
        my_hook.get_conn.assert_any_call()
        a.assert_called_once_with(path='srcZ')
        cpy.assert_called()

        print(mapps)
        self.assertEqual(len(mapps), 2)


    @patch('dags.uploadflow.tempfile.mktemp')
    def test_skipdir_files(self, tmp):
        tmp.side_effect = ['tmpA', 'tmpB']

        my_hook = MagicMock()
        a = MagicMock()
        a.return_value = ['a', 'c']
        stat = MagicMock(side_effect=['elo', 'd elo'])
        cpy = MagicMock(return_value=False)
        my_hook.get_conn().__enter__().open_sftp().listdir = a
        my_hook.get_conn().__enter__().open_sftp().stat = stat
        my_hook.get_conn().__enter__().open_sftp().open().__enter__().raw.read = cpy

        mapps = ssh2local_copy(ssh_hook=my_hook, source='srcZ', target='trg')
        my_hook.get_conn.assert_any_call()
        a.assert_called_once_with(path='srcZ')
        cpy.assert_called()
        
        print(mapps)
        
        self.assertEqual(len(mapps), 1)


    def test_copy_streams(self):
        """
        def copy_streams(input, output):
        """
        with tempfile.TemporaryDirectory() as dir:
            text = 'Some input text'
            input_name = os.path.join(dir,'input.txt')
            output_name = os.path.join(dir, 'output')
            with open(input_name, 'w') as fln:
                fln.write(text)

            with open(input_name, 'rb') as input:
                with open(output_name, 'wb') as output:
                    copy_streams(input=input, output=output)

            with open(output_name, 'r') as f:
                txt = f.read()
                print("Read following: ", txt)

                self.assertEqual(text, txt)
