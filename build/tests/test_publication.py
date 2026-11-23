import json
import os
import sys
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publication import BuildLock, publish, recover


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.public = self.workspace / "public"
        self.staging = self.workspace / "candidate"
        for parent, label in ((self.public, "old"), (self.staging, "new")):
            for name in ("data", "img", "diagnostics"):
                (parent / name).mkdir(parents=True)
                (parent / name / "value").write_text(label, encoding="utf-8")
        (self.public / "favicon.png").write_bytes(b"static")

    def test_publication_promotes_all_folders_and_preserves_static_files(self):
        publish(self.staging, self.public)
        for name in ("data", "img", "diagnostics"):
            self.assertEqual((self.public / name / "value").read_text("utf-8"), "new")
        self.assertEqual((self.public / "favicon.png").read_bytes(), b"static")
        self.assertFalse((self.workspace / ".hs-map-data-update.json").exists())

    def test_a_failure_restores_the_previous_complete_publication(self):
        def fail(index):
            if index == 1:
                raise RuntimeError("injected interruption")
        with self.assertRaisesRegex(RuntimeError, "injected"):
            publish(self.staging, self.public, fail)
        for name in ("data", "img", "diagnostics"):
            self.assertEqual((self.public / name / "value").read_text("utf-8"), "old")

    def test_an_incomplete_lock_is_never_reclaimed_as_a_missing_pid(self):
        lock = self.workspace / ".hs-map-data.lock"
        lock.write_text("", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "creating its lock"):
            with BuildLock(self.workspace):
                self.fail("entered an occupied lock")
        self.assertTrue(lock.exists())

    def test_live_lock_is_exclusive(self):
        with BuildLock(self.workspace):
            with self.assertRaisesRegex(RuntimeError, "running"):
                with BuildLock(self.workspace):
                    self.fail("entered an occupied lock")
        self.assertFalse((self.workspace / ".hs-map-data.lock").exists())

    def test_recovery_refuses_a_journal_targeting_source_code(self):
        backup = self.workspace / ".hs-map-backup-test"
        backup.mkdir()
        journal = {"schema_version": 1, "phase": "installing", "backup": backup.name,
                   "entries": [{"name": "../src", "existed": False}]}
        (self.workspace / ".hs-map-data-update.json").write_text(json.dumps(journal), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "target"):
            recover(self.public)

    def test_default_build_recovers_before_opening_an_invalid_next_bundle(self):
        script_folder = self.workspace / "build"
        script_folder.mkdir()
        for script in Path(__file__).resolve().parents[1].glob("*.py"):
            shutil.copy2(script, script_folder / script.name)
        backup = self.workspace / ".hs-map-backup-interrupted"
        backup.mkdir()
        (self.public / "data").rename(backup / "data")
        (self.staging / "data").rename(self.public / "data")
        journal = {"schema_version": 1, "phase": "installing", "backup": backup.name,
                   "entries": [{"name": name, "existed": True} for name in ("data", "img", "diagnostics")]}
        (self.workspace / ".hs-map-data-update.json").write_text(json.dumps(journal), encoding="utf-8")
        env = {**os.environ, "HERO_SIEGE_BIN": str(self.workspace / "game"),
               "HS_DATA_BUNDLE": str(self.workspace / "missing-bundle")}
        env.pop("HS_MAP_OUTPUT", None)
        failed = subprocess.run([sys.executable, str(script_folder / "build.py")], env=env,
                                text=True, capture_output=True, timeout=20)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("Cannot read Extractor manifest", failed.stderr)
        self.assertFalse((self.workspace / ".hs-map-data-update.json").exists())
        for name in ("data", "img", "diagnostics"):
            self.assertEqual((self.public / name / "value").read_text("utf-8"), "old")


if __name__ == "__main__":
    unittest.main()
