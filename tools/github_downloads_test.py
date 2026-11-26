import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from github_downloads import snapshot, update, notify


def release(count,ident=1):
    return {'draft':False,'assets':[{'name':'fejes.mover.monitor.plg','id':ident,'download_count':count}, {'name':'SHA256SUMS','id':500,'download_count':100}]}


class CounterTests(unittest.TestCase):
    def test_only_installers_count(self):
        self.assertEqual(snapshot(lambda p:[release(3),release(4,2)])['total'],7)

    def test_repeated_asset_not_counted_twice(self):
        self.assertEqual(snapshot(lambda p:[release(3),release(3)])['total'],3)

    def test_bad_api_does_not_become_zero(self):
        with self.assertRaises(ValueError):
            snapshot(lambda p:{'message':'rate limited'})

    def test_telegram_mask_excludes_email_browser(self):
        run=Mock()
        notify(12,1,run=run)
        self.assertEqual(run.call_args.args[0][-1],'normal 4')
        self.assertIn('Összes telepítőletöltés: 12',run.call_args.args[0][-3])

    def test_baseline_increase_and_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.json'
            send=Mock()
            update(path,lambda p:[release(4)],send)
            send.assert_not_called()
            self.assertEqual(json.loads((Path(directory)/'github-download-history.json').read_text()),
                             [{'date':__import__('time').strftime('%Y-%m-%d',__import__('time').gmtime()),'total':4}])
            update(path,lambda p:[release(6)],send)
            send.assert_called_once_with(6,2,test=False)
            send.reset_mock()
            update(path,lambda p:[release(6)],send)
            send.assert_not_called()
            send.side_effect=OSError()
            with self.assertRaises(OSError):
                update(path,lambda p:[release(7)],send)
            self.assertEqual(json.loads(path.read_text())['total'],6)

    def test_daily_history_replaces_same_day_and_appends_next_day(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.json'; history=Path(directory)/'history.json'; send=Mock()
            update(path,lambda p:[release(4)],send,history_path=history,now=0)
            update(path,lambda p:[release(5)],send,history_path=history,now=1)
            update(path,lambda p:[release(7)],send,history_path=history,now=86400)
            self.assertEqual(json.loads(history.read_text()),[
                {'date':'1970-01-01','total':5},{'date':'1970-01-02','total':7}])


if __name__=='__main__':
    unittest.main()
