"""
Self-test for Jamfbreak.

Tests the RodoExploit pipeline's Manifest.plist editing and validation
logic — the core safety-critical code path that must not produce a
corrupt backup (which could cause issues after restore).
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
import plistlib
from contextlib import closing
from pathlib import Path
from unittest import mock

from jamfbreak import device, rodo_pipeline, runtime_paths
from jamfbreak.gui_html import HTML
from scripts import check_public_tree


def _make_test_manifest(serial: str = "PLACEHOLDER_SN",
                        udid: str = "PLACEHOLDER_UDID") -> bytes:
    """Create a Manifest.plist with placeholder values."""
    data = {
        "SerialNumber": serial,
        "UniqueDeviceID": udid,
        "ProductType": "iPad13,8",
        "BuildVersion": "22B5075a",
        "BackupKeyBag": b"\x00" * 64,
        "Lockdown": {
            "DeviceName": "Test iPad",
            "ProductVersion": "18.2",
        },
    }
    return plistlib.dumps(data, fmt=plistlib.FMT_BINARY)


def _write_valid_backup(
    directory: str | Path,
    *,
    manifest: bytes | None = None,
    snapshot_state: str = "finished",
    product_version: str = "18.2",
) -> Path:
    bdir = Path(directory)
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "Manifest.plist").write_bytes(manifest or _make_test_manifest())
    (bdir / "Info.plist").write_bytes(
        plistlib.dumps(
            {
                "Product Version": product_version,
                "Product Type": "iPad13,8",
                "Target Identifier": bdir.name,
            },
            fmt=plistlib.FMT_BINARY,
        )
    )
    (bdir / "Status.plist").write_bytes(
        plistlib.dumps(
            {"SnapshotState": snapshot_state}, fmt=plistlib.FMT_BINARY
        )
    )
    (bdir / "Manifest.mbdb").write_bytes(b"mbdb\x05\x00test-record")
    return bdir


def _device_info(**changes) -> device.DeviceInfo:
    values = {
        "udid": "00008101-00012345ABCDEF",
        "serial": "F1LMLPLKABCDEFG",
        "imei": "",
        "build_version": "22B5075a",
        "product_version": "18.2",
        "product_type": "iPad13,8",
        "activation_state": "Activated",
        "name": "Test iPad",
    }
    values.update(changes)
    return device.DeviceInfo(**values)


class EditManifestTest(unittest.TestCase):
    def test_edit_injects_serial_and_udid(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "Manifest.plist"
            mpath.write_bytes(_make_test_manifest())

            rodo_pipeline.edit_manifest_plist(
                mpath, serial="F1LMLPLKABCDEFG", udid="00008101-00012345ABCDEF"
            )

            with open(mpath, "rb") as f:
                edited = plistlib.load(f)

            self.assertEqual(edited["SerialNumber"], "F1LMLPLKABCDEFG")
            self.assertEqual(edited["UniqueDeviceID"], "00008101-00012345ABCDEF")
            self.assertEqual(edited["ProductType"], "iPad13,8")
            self.assertEqual(edited["BuildVersion"], "22B5075a")

    def test_edit_preserves_nested_keys(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "Manifest.plist"
            mpath.write_bytes(_make_test_manifest())

            rodo_pipeline.edit_manifest_plist(
                mpath, serial="NEWSN", udid="NEWUDID"
            )

            with open(mpath, "rb") as f:
                edited = plistlib.load(f)

            self.assertEqual(edited["Lockdown"]["DeviceName"], "Test iPad")
            self.assertEqual(edited["Lockdown"]["ProductVersion"], "18.2")

    def test_edit_raises_on_missing_serial_key(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "Manifest.plist"
            data = {"UniqueDeviceID": "X", "ProductType": "iPad13,8"}
            mpath.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY))

            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline.edit_manifest_plist(mpath, serial="S", udid="U")

    def test_edit_raises_on_missing_udid_key(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "Manifest.plist"
            data = {"SerialNumber": "X", "ProductType": "iPad13,8"}
            mpath.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY))

            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline.edit_manifest_plist(mpath, serial="S", udid="U")

    def test_edit_raises_on_corrupt_plist(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "Manifest.plist"
            mpath.write_bytes(b"this is not a plist")

            with self.assertRaises(Exception):
                rodo_pipeline.edit_manifest_plist(mpath, serial="S", udid="U")

    def test_edit_rejects_ambiguous_duplicate_identity_keys(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "Manifest.plist"
            data = {
                "SerialNumber": "FIRST",
                "Nested": {"SerialNumber": "SECOND"},
                "UniqueDeviceID": "U",
            }
            original = plistlib.dumps(data, fmt=plistlib.FMT_BINARY)
            mpath.write_bytes(original)

            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline.edit_manifest_plist(mpath, serial="S", udid="U")

            self.assertEqual(mpath.read_bytes(), original)

    def test_edit_rejects_invalid_udid_without_changing_file(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "Manifest.plist"
            original = _make_test_manifest()
            mpath.write_bytes(original)
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline.edit_manifest_plist(
                    mpath, serial="SERIAL", udid="bad\nvalue"
                )
            self.assertEqual(mpath.read_bytes(), original)


class ValidateBackupTest(unittest.TestCase):
    def _noop_log(self, text, kind, tag):
        pass

    def test_validates_good_backup(self):
        with tempfile.TemporaryDirectory() as d:
            _write_valid_backup(d)
            rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_fails_on_missing_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_fails_on_corrupt_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            _write_valid_backup(d)
            mpath = Path(d) / "Manifest.plist"
            mpath.write_bytes(b"not a plist")
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_fails_on_missing_serial_key(self):
        with tempfile.TemporaryDirectory() as d:
            data = {"UniqueDeviceID": "X", "ProductType": "iPad"}
            _write_valid_backup(
                d, manifest=plistlib.dumps(data, fmt=plistlib.FMT_BINARY)
            )
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_fails_on_missing_status(self):
        with tempfile.TemporaryDirectory() as d:
            _write_valid_backup(d)
            (Path(d) / "Status.plist").unlink()
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_fails_on_unfinished_backup(self):
        with tempfile.TemporaryDirectory() as d:
            _write_valid_backup(d, snapshot_state="failed")
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_fails_on_missing_payload_index(self):
        with tempfile.TemporaryDirectory() as d:
            _write_valid_backup(d)
            (Path(d) / "Manifest.mbdb").unlink()
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_fails_on_encrypted_backup(self):
        with tempfile.TemporaryDirectory() as d:
            data = plistlib.loads(_make_test_manifest())
            data["IsEncrypted"] = True
            _write_valid_backup(
                d, manifest=plistlib.dumps(data, fmt=plistlib.FMT_BINARY)
            )
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_fails_when_source_identifier_does_not_match_folder(self):
        with tempfile.TemporaryDirectory() as d:
            _write_valid_backup(d)
            info_path = Path(d) / "Info.plist"
            info = plistlib.loads(info_path.read_bytes())
            info["Target Identifier"] = "OTHER-SOURCE"
            info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_BINARY))
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_validates_nonempty_sqlite_payload_index(self):
        with tempfile.TemporaryDirectory() as d:
            _write_valid_backup(d)
            (Path(d) / "Manifest.mbdb").unlink()
            with closing(sqlite3.connect(Path(d) / "Manifest.db")) as connection:
                connection.execute("CREATE TABLE Files (fileID TEXT)")
                connection.execute("INSERT INTO Files VALUES ('abc')")
                connection.commit()
            rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_fails_on_empty_sqlite_payload_index(self):
        with tempfile.TemporaryDirectory() as d:
            _write_valid_backup(d)
            (Path(d) / "Manifest.mbdb").unlink()
            with closing(sqlite3.connect(Path(d) / "Manifest.db")) as connection:
                connection.execute("CREATE TABLE Files (fileID TEXT)")
                connection.commit()
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_folder(Path(d), self._noop_log)

    def test_rejects_oversized_plist_before_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Manifest.plist"
            with open(path, "wb") as handle:
                handle.truncate(rodo_pipeline.MAX_PLIST_BYTES + 1)
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._load_plist_dict(path)

    def test_rejects_excessive_backup_file_count(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "one").write_bytes(b"1")
            (root / "two").write_bytes(b"2")
            with mock.patch.object(rodo_pipeline, "MAX_BACKUP_FILES", 1):
                with self.assertRaises(rodo_pipeline.BackupValidationError):
                    rodo_pipeline._validate_backup_tree(root)

    def test_rejects_excessive_nested_depth(self):
        nested = "value"
        for _ in range(rodo_pipeline.MAX_NESTED_DEPTH + 1):
            nested = {"nested": nested}
        with self.assertRaises(rodo_pipeline.BackupValidationError):
            list(rodo_pipeline._walk_nested(nested))


class VerifyEditTest(unittest.TestCase):
    def _noop_log(self, text, kind, tag):
        pass

    def test_verify_confirms_correct_values(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "Manifest.plist"
            mpath.write_bytes(_make_test_manifest())
            rodo_pipeline.edit_manifest_plist(
                mpath, serial="VERIFY_SN", udid="VERIFY-UDID"
            )
            rodo_pipeline._verify_manifest_edit(
                mpath, serial="VERIFY_SN", udid="VERIFY-UDID", log=self._noop_log
            )

    def test_verify_fails_on_wrong_serial(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "Manifest.plist"
            mpath.write_bytes(_make_test_manifest())
            rodo_pipeline.edit_manifest_plist(
                mpath, serial="CORRECT_SN", udid="CORRECT-UDID"
            )
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._verify_manifest_edit(
                    mpath, serial="WRONG_SN", udid="CORRECT-UDID", log=self._noop_log
                )


class CompatibilityTest(unittest.TestCase):
    def _noop_log(self, text, kind, tag):
        pass

    def test_rejects_backup_from_newer_ios(self):
        with tempfile.TemporaryDirectory() as d:
            bdir = _write_valid_backup(d, product_version="19.0")
            with self.assertRaises(rodo_pipeline.BackupValidationError):
                rodo_pipeline._validate_backup_compatibility(
                    bdir, _device_info(product_version="18.2"), self._noop_log
                )


class RestoreCommandTest(unittest.TestCase):
    def test_helper_resolution_is_limited_to_explicit_bin_folder(self):
        with tempfile.TemporaryDirectory() as d:
            helper = Path(d) / "ideviceinfo.exe"
            helper.write_bytes(b"test")
            with mock.patch("jamfbreak.device.asset_dir", return_value=Path(d)):
                self.assertEqual(
                    Path(device._bin("ideviceinfo.exe")), helper.resolve()
                )
        with self.assertRaises(device.DeviceError):
            device._bin(r"..\ideviceinfo.exe")

    def test_background_helpers_do_not_open_console_windows(self):
        completed = mock.Mock(returncode=0, stdout=b"value\n", stderr=b"")
        with mock.patch(
            "jamfbreak.device.subprocess.run", return_value=completed
        ) as run:
            self.assertEqual(
                device._run("ideviceinfo.exe", ["-k", "DeviceName"]),
                "value",
            )

        self.assertEqual(
            run.call_args.kwargs["creationflags"],
            device.subprocess_creation_flags(),
        )
        if device.os.name == "nt":
            self.assertNotEqual(run.call_args.kwargs["creationflags"], 0)

    def test_command_has_only_the_safe_restore_shape(self):
        command = device.build_restore_command(
            "idevicebackup2.exe",
            r"C:\backups",
            "TARGET-UDID",
            source_udid="SOURCE-UDID",
        )
        self.assertEqual(
            command,
            [
                "idevicebackup2.exe",
                "--udid",
                "TARGET-UDID",
                "--source",
                "SOURCE-UDID",
                "restore",
                "--system",
                "--settings",
                "--skip-apps",
                "--no-reboot",
                r"C:\backups",
            ],
        )
        self.assertNotIn("--full", command)
        self.assertNotIn("--remove", command)

    def test_binary_preflight_rejects_missing_safety_flags(self):
        completed = mock.Mock(stdout=b"--system --settings --udid --source")
        with mock.patch("jamfbreak.device.subprocess.run", return_value=completed):
            with self.assertRaises(device.DeviceError):
                device.validate_restore_tool("idevicebackup2.exe")


class PipelineSafetyTest(unittest.TestCase):
    def test_failed_restore_never_reboots_and_reports_uncertain_state(self):
        logs = []

        def log(text, kind, tag):
            logs.append(text)

        with tempfile.TemporaryDirectory() as d:
            bdir = _write_valid_backup(Path(d) / "SOURCE-UDID")
            original_manifest = (bdir / "Manifest.plist").read_bytes()
            info = _device_info()
            with (
                mock.patch(
                    "jamfbreak.rodo_pipeline.device.get_device_info",
                    side_effect=[info, info],
                ),
                mock.patch(
                    "jamfbreak.rodo_pipeline.device.restore_backup",
                    return_value=7,
                ) as restore,
                mock.patch("jamfbreak.rodo_pipeline.subprocess.run") as reboot,
            ):
                result = rodo_pipeline.run_rodo_pipeline(
                    log, backup_dir=str(bdir)
                )

            self.assertEqual(result.exit_code, 3)
            self.assertIn("uncertain", result.error)
            restore.assert_called_once()
            reboot.assert_not_called()
            self.assertEqual((bdir / "Manifest.plist").read_bytes(), original_manifest)
            self.assertTrue(any("will NOT reboot" in line for line in logs))

    def test_identity_change_aborts_before_restore(self):
        with tempfile.TemporaryDirectory() as d:
            bdir = _write_valid_backup(Path(d) / "SOURCE-UDID")
            first = _device_info()
            changed = _device_info(serial="DIFFERENT-SERIAL")
            with (
                mock.patch(
                    "jamfbreak.rodo_pipeline.device.get_device_info",
                    side_effect=[first, changed],
                ),
                mock.patch(
                    "jamfbreak.rodo_pipeline.device.restore_backup"
                ) as restore,
            ):
                result = rodo_pipeline.run_rodo_pipeline(
                    lambda *_: None, backup_dir=str(bdir)
                )
            self.assertEqual(result.exit_code, 5)
            restore.assert_not_called()

    def test_success_reboots_only_after_zero_exit(self):
        with tempfile.TemporaryDirectory() as d:
            bdir = _write_valid_backup(Path(d) / "SOURCE-UDID")
            info = _device_info()
            reboot_result = mock.Mock(returncode=0)
            with (
                mock.patch(
                    "jamfbreak.rodo_pipeline.device.get_device_info",
                    side_effect=[info, info],
                ),
                mock.patch(
                    "jamfbreak.rodo_pipeline.device.restore_backup",
                    return_value=0,
                ),
                mock.patch(
                    "jamfbreak.rodo_pipeline.device._bin",
                    return_value="idevicerestart.exe",
                ),
                mock.patch(
                    "jamfbreak.rodo_pipeline.subprocess.run",
                    return_value=reboot_result,
                ) as reboot,
            ):
                result = rodo_pipeline.run_rodo_pipeline(
                    lambda *_: None, backup_dir=str(bdir)
                )
            self.assertEqual(result.exit_code, 0)
            reboot.assert_called_once_with(
                ["idevicerestart.exe", "-u", info.udid],
                check=False,
                timeout=30,
                creationflags=device.subprocess_creation_flags(),
            )


class FindBackupDirTest(unittest.TestCase):
    def test_returns_none_when_empty(self):
        result = rodo_pipeline.find_backup_dir()
        if result is not None:
            self.assertTrue(result.is_dir())
            self.assertTrue((result / "Manifest.plist").is_file())


class PublicGuiTest(unittest.TestCase):
    def test_gui_uses_jamfbreak_brand(self):
        self.assertIn("<title>Jamfbreak</title>", HTML)
        self.assertIn(">Jamfbreak <", HTML)
        self.assertNotIn("MDM Patcher", HTML)
        self.assertEqual(device.__package__, "jamfbreak")

    def test_gui_has_no_license_gate(self):
        """The Bypass button must not depend on a license-key workflow."""
        self.assertNotIn("license key", HTML.lower())
        self.assertNotIn("validate_key", HTML)
        self.assertNotIn("keyValid", HTML)

    def test_gui_renders_device_metadata_as_text(self):
        self.assertNotIn("innerHTML", HTML)
        self.assertIn("valueNode.textContent = String(value || '—')", HTML)
        self.assertIn("document.createTextNode(String(text))", HTML)


class PublicReleaseTest(unittest.TestCase):
    def test_frozen_assets_resolve_beside_executable(self):
        with (
            mock.patch.object(runtime_paths.sys, "frozen", True, create=True),
            mock.patch.object(
                runtime_paths.sys,
                "executable",
                r"C:\Program Files\Jamfbreak\Jamfbreak.exe",
            ),
        ):
            self.assertEqual(
                runtime_paths.asset_dir("backups"),
                Path(r"C:\Program Files\Jamfbreak\backups"),
            )

    def test_release_spec_excludes_private_runtime_assets_and_upx(self):
        spec = Path("Jamfbreak.spec").read_text(encoding="utf-8")
        self.assertEqual(spec.count("datas = webview_datas"), 1)
        self.assertNotIn("datas = webview_datas +", spec)
        self.assertIn("upx=False", spec)
        self.assertIn(
            'icon=str(project_root / "Jamfbreak Logo.ico")', spec
        )

    def test_readme_centers_project_logo(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith('<p align="center">'))
        self.assertIn(
            '<img src="Jamfbreak%20Logo.png" alt="Jamfbreak logo" width="180">',
            readme,
        )

    def test_public_docs_contain_no_developer_home_path(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertNotIn("C:" + "\\Users\\", readme)


class PublicTreePrivacyTest(unittest.TestCase):
    def test_accepts_safe_text_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "README.md").write_text("# Safe project\n", encoding="utf-8")
            self.assertEqual(
                check_public_tree.check_paths(root, ["README.md"]),
                [],
            )

    def test_rejects_private_binary_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            private_file = root / "jamfbreak" / "bin" / "helper.exe"
            private_file.parent.mkdir(parents=True)
            private_file.write_bytes(b"not a public release asset")
            problems = check_public_tree.check_paths(
                root, ["jamfbreak/bin/helper.exe"]
            )
            self.assertTrue(any("forbidden private/generated path" in p for p in problems))

    def test_rejects_personal_windows_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "notes.txt"
            source.write_text(
                "Local path: " + "C:" + "\\Users\\" + "developer\\backup",
                encoding="utf-8",
            )
            problems = check_public_tree.check_paths(root, ["notes.txt"])
            self.assertTrue(any("Windows user profile path" in p for p in problems))


def main(argv=None) -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([
        loader.loadTestsFromTestCase(EditManifestTest),
        loader.loadTestsFromTestCase(ValidateBackupTest),
        loader.loadTestsFromTestCase(VerifyEditTest),
        loader.loadTestsFromTestCase(CompatibilityTest),
        loader.loadTestsFromTestCase(RestoreCommandTest),
        loader.loadTestsFromTestCase(PipelineSafetyTest),
        loader.loadTestsFromTestCase(FindBackupDirTest),
        loader.loadTestsFromTestCase(PublicGuiTest),
        loader.loadTestsFromTestCase(PublicReleaseTest),
        loader.loadTestsFromTestCase(PublicTreePrivacyTest),
    ])
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
