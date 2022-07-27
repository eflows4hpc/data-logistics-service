import imp
from importlib.resources import path

import unittest
#from unittest.mock import Mock, patch
from dags.uploadflow import ssh2local_copy
#from airflow.providers.ssh.hooks.ssh import SSHHook
from unittest.mock import MagicMock, patch
#from paramiko.client import SSHClient
#from paramiko.sftp_client import SFTPClient



"""
def ssh2local_copy(ssh_hook, source: str, target: str):
    with ssh_hook.get_conn() as ssh_client:
            sftp_client = ssh_client.open_sftp()
            lst = sftp_client.listdir(path=source)
            
            print(f"{len(lst)} objects in {source}")
            mappings = dict()
            for fname in lst:
                local = tempfile.mktemp(prefix='dls', dir=target)
                full_name = os.path.join(source, fname)
                sts = sftp_client.stat(full_name)
                if str(sts).startswith('d'):
                    print(f"{full_name} is a directory. Skipping")
                    continue

                print(f"Copying {full_name} --> {local}")
                sftp_client.get(full_name, local)
                mappings[local] = fname

    return mappings


"""
class TestSSH(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @patch('dags.uploadflow.tempfile.mktemp')
    def test_copy_files(self, tmp):
        tmp.side_effect = ['tmpA', 'tmpB']

        my_hook = MagicMock()
        a = MagicMock()
        a.return_value = ['a', 'c']
        stat = MagicMock(side_effect=['elo', 'elo'])
        cpy = MagicMock(return_value='')
        my_hook.get_conn().__enter__().open_sftp().listdir = a
        my_hook.get_conn().__enter__().open_sftp().stat = stat
        my_hook.get_conn().__enter__().open_sftp().get = cpy

        mapps = ssh2local_copy(ssh_hook=my_hook, source='srcZ', target='trg')
        my_hook.get_conn.assert_any_call()
        a.assert_called_once_with(path='srcZ')
        cpy.assert_any_call('srcZ/a', 'tmpA')
        cpy.assert_any_call('srcZ/c', 'tmpB')

        print(mapps)
        self.assertEqual(len(mapps), 2)
        
        

        