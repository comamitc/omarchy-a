from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT / 'desktop/configuration/scale-output'
BASH = shutil.which('bash')


def bash_has_mapfile():
    return BASH is not None and subprocess.run([BASH, '-c', 'type mapfile'], capture_output=True).returncode == 0


def panel(name, mode, flags='preferred, current'):
    return (f'{name} "Apple Inc. Panel"\n'
            '  Enabled: yes\n'
            '  Modes:\n'
            f'    {mode} px, 60.000000 Hz ({flags})\n'
            '  Scale: 1.000000\n')


@unittest.skipUnless(bash_has_mapfile(), 'scale-output needs bash 4+ (mapfile)')
class ScaleOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.calls = self.root / 'calls'
        fake = self.root / 'wlr-randr'
        fake.write_text('#!/bin/sh\n'
                        'if [ "$#" -eq 0 ]; then cat "$FAKE_STATE"; else echo "$*" >> "$FAKE_CALLS"; fi\n')
        fake.chmod(0o755)

    def run_with(self, state):
        (self.root / 'state').write_text(state)
        env = dict(os.environ, PATH=f'{self.root}:{os.environ["PATH"]}',
                   FAKE_STATE=str(self.root / 'state'), FAKE_CALLS=str(self.calls))
        result = subprocess.run([BASH, str(SCRIPT)], env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.calls.read_text() if self.calls.exists() else ''

    def test_known_native_panels_scale_to_two_in_either_orientation(self):
        for mode in ('1536x2048', '2048x1536', '1668x2388', '2388x1668'):
            for flags in ('preferred, current', 'current, preferred', 'current'):
                with self.subTest(mode=mode, flags=flags):
                    self.calls.unlink(missing_ok=True)
                    self.assertEqual(self.run_with(panel('DSI-1', mode, flags)), '--output DSI-1 --scale 2\n')

    def test_unknown_mode_or_extra_output_leaves_scale_unchanged(self):
        cases = {
            'vm mode': panel('Virtual-1', '1280x800'),
            'not current': panel('DSI-1', '1668x2388', 'preferred'),
            'two outputs': panel('DSI-1', '1668x2388') + panel('HDMI-A-1', '1920x1080'),
            'disabled': panel('DSI-1', '1668x2388').replace('Enabled: yes', 'Enabled: no'),
        }
        for name, state in cases.items():
            with self.subTest(name):
                self.assertEqual(self.run_with(state), '')
