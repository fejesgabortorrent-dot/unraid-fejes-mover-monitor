import io
import unittest
from unittest.mock import patch

from test_support import install
install()
import completed_seed_service as service


class CompletedSeedWorker(unittest.TestCase):
    def test_manual_and_scheduled_dispatch_honor_the_same_explicit_mode(self):
        with patch.object(service.n, 'read_json', return_value={'completed_seed_mode': True}), \
             patch.object(service, 'run', return_value={'state': 'completed_seed_ready'}) as completed, \
             patch.object(service.n, 'run') as legacy:
            self.assertEqual(service.n.run_configured()['state'], 'completed_seed_ready')
        completed.assert_called_once()
        legacy.assert_not_called()
        with patch.object(service.n, 'read_json', return_value={}), \
             patch.object(service, 'run') as completed, \
             patch.object(service.n, 'run', return_value={'state': 'nothing_eligible'}) as legacy:
            self.assertEqual(service.n.run_configured()['state'], 'nothing_eligible')
        legacy.assert_called_once()
        completed.assert_not_called()

    def test_completed_preview_does_not_publish_old_age_or_ratio_blockers(self):
        report = {'forecast': {'rows': [{'file': 'a.mkv', 'reason': 'ratio_not_met',
            'age_ready_at': 99999, 'ratio_target_met': True},
            {'file': 'b.mkv', 'reason': 'too_young', 'age_ready_at': 99999}]}}
        unit = {'paths': [service.n.ROOT + '/a.mkv'], 'bytes': 100, 'files': 1}
        with patch.object(service.n, 'read_json', return_value={'completed_seed_mode': True, 'batch_gib': 16}), \
             patch.object(service.pilot, 'plan', return_value=[unit]), \
             patch.object(service.n, 'atomic_json') as write:
            out = service.preview(report, update=True)
        self.assertEqual(out['candidate_count'], 1)
        self.assertEqual([r['reason'] for r in out['forecast']['rows']], ['ready', 'completed_seed_unverified'])
        self.assertTrue(all(r['age_ready_at'] is None for r in out['forecast']['rows']))
        self.assertFalse(out['forecast']['rows'][0]['ratio_target_met'])
        write.assert_called_once()

    def invoke(self, settings, units=None, latch=False, guard='pass'):
        units = units if units is not None else [{'unit_digest': 'a', 'bytes': 1024}]
        configured = {'version': 1, 'batch_gib': 16, **settings}
        with patch.object(service.n, 'read_json', side_effect=lambda path, default: configured if path == service.n.CONFIG else {}), \
             patch.object(service.n.PID.__class__, 'exists', return_value=False), \
             patch.object(service.n, 'needs_inspection', return_value=latch), \
             patch.object(service.n, 'guards', return_value={'backup': guard}), \
             patch.object(service.n, 'collect') as collect, \
             patch.object(service.n, 'atomic_json') as cooldown, \
             patch.object(service.pilot, 'environment') as environment, \
             patch.object(service.pilot, 'plan', return_value=units), \
             patch.object(service.pilot, 'prepare', return_value={'authorization': '/private/authorization.json'}) as prepare, \
             patch.object(service.pilot, 'run', return_value={'state': 'completed_seed_ready'}) as run, \
             patch.object(service, 'open', return_value=io.StringIO(), create=True), \
             patch.object(service.fcntl, 'flock'):
            result = service.run()
        return result, collect, cooldown, environment, prepare, run

    def test_mode_is_explicit_and_wrong_types_are_not_truthy_opt_in(self):
        result, collect, cooldown, environment, prepare, run = self.invoke({})
        self.assertEqual(result['state'], 'blocked')
        for method in (collect, cooldown, environment, prepare, run): method.assert_not_called()
        for value in (1, 'true', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                service.configured({'completed_seed_mode': value})

    def test_existing_inspection_or_guard_blocks_before_backup_and_movement(self):
        for kwargs in ({'latch': True}, {'guard': 'wait'}):
            result, collect, cooldown, environment, prepare, run = self.invoke({'completed_seed_mode': True}, **kwargs)
            for method in (collect, cooldown, prepare, run): method.assert_not_called()

    def test_configured_batch_limit_does_not_split_an_oversized_unit(self):
        result, collect, cooldown, environment, prepare, run = self.invoke(
            {'completed_seed_mode': True}, units=[{'unit_digest': 'a', 'bytes': 17 * 1024**3}])
        self.assertEqual(result['state'], 'nothing_eligible')
        prepare.assert_not_called()
        run.assert_not_called()
        cooldown.assert_not_called()

    def test_worker_prepares_backup_and_records_cooldown_before_one_scoped_run(self):
        result, collect, cooldown, environment, prepare, run = self.invoke({'completed_seed_mode': True})
        self.assertEqual(result['state'], 'completed_seed_ready')
        collect.assert_called_once_with(update=True)
        prepare.assert_called_once_with('a')
        cooldown.assert_called_once()
        run.assert_called_once_with('/private/authorization.json')
