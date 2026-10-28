from pathlib import Path
import os
import subprocess
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
BIN = PROJECT / 'desktop/shell/bin'


class BacklightChoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.env = dict(os.environ, PATH=f'{BIN}:{os.environ["PATH"]}', IPADLINUX_BACKLIGHT_DIR=str(self.base))

    def backlight(self, name, brightness=500):
        device = self.base / name
        device.mkdir()
        (device / 'max_brightness').write_text('1000\n')
        (device / 'brightness').write_text(f'{brightness}\n')
        return device

    def run_script(self, *args):
        return subprocess.run(['bash', str(BIN / args[0]), *args[1:]], env=self.env, text=True, capture_output=True)

    def test_known_panel_wins_over_other_backlights(self):
        self.backlight('other')
        panel = self.backlight('20e200080.backlight')
        self.assertEqual(self.run_script('omarchy-hw-display').stdout, '20e200080.backlight\n')
        self.assertEqual(self.run_script('omarchy-brightness-display', '--no-osd', '30%').stdout, '30\n')
        self.assertEqual((panel / 'brightness').read_text(), '300\n')
        self.assertEqual((self.base / 'other/brightness').read_text(), '500\n')

    def test_sole_unknown_backlight_is_used(self):
        self.backlight('panel', brightness=250)
        self.assertEqual(self.run_script('omarchy-hw-display').stdout, 'panel\n')
        self.assertEqual(self.run_script('omarchy-brightness-display').stdout, '25\n')

    def test_no_or_ambiguous_backlight_is_unavailable(self):
        for names in ((), ('one', 'two')):
            with self.subTest(names=names):
                for name in names:
                    self.backlight(name)
                self.assertEqual(self.run_script('omarchy-hw-display').returncode, 1)
                result = self.run_script('omarchy-brightness-display')
                self.assertEqual((result.returncode, result.stdout), (1, 'unavailable\n'))


class BootIntroTests(unittest.TestCase):
    def test_shell_calls_succeed_without_side_effects(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home, XDG_STATE_HOME=home)
            for args in ((), ('--prepare-theme', 'tokyo-night')):
                with self.subTest(args=args):
                    result = subprocess.run(['bash', str(BIN / 'omarchy-theme-bg-boot-intro'), *args],
                                            env=env, capture_output=True)
                    self.assertEqual((result.returncode, result.stdout), (0, b''))
            self.assertEqual(list(Path(home).iterdir()), [])
