"""The .mer document carries bounded, verified resources and survives interrupted saves."""

import base64
import copy
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401

from meridiana import model, project_index, recovery
from meridiana.underlay import Underlay


class ProjectArchive(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.path = self.folder / "design.mer"

    def project(self):
        p = model.Project(name="Tetto è sud", job_id="job-1", series_id="series-1", reserved=True)
        p.underlays = [Underlay("u1", image=base64.b64encode(b"same bytes").decode())]
        p.report = {"attachments": [{"path": "sheet.pdf", "title": "Sheet",
                                     "data": base64.b64encode(b"same bytes").decode()}]}
        return p

    def rewrite(self, mutate):
        with zipfile.ZipFile(self.path) as z:
            entries = {i.filename: z.read(i) for i in z.infolist()}
        mutate(entries)
        with zipfile.ZipFile(self.path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in entries.items():
                z.writestr(name, data)

    def test_saving_mer_creates_a_zip_with_deduplicated_binary_resources(self):
        p = self.project()
        p.save(self.path)
        self.assertTrue(zipfile.is_zipfile(self.path), "a .mer is a ZIP document")
        with zipfile.ZipFile(self.path) as z:
            self.assertEqual(z.infolist()[0].filename, "mimetype")
            self.assertEqual(z.infolist()[0].compress_type, zipfile.ZIP_STORED)
            assets = [name for name in z.namelist() if name.startswith("assets/")]
            self.assertEqual(len(assets), 1)
            self.assertEqual(z.read(assets[0]), b"same bytes")
            raw = json.loads(z.read("project.json"))
            from meridiana import __version__
            self.assertEqual(json.loads(z.read("manifest.json"))["producer"],
                             {"name": "Meridiana", "version": __version__})
            self.assertEqual(raw["version"], model.FORMAT_VERSION)
            self.assertEqual(raw["underlays"][0]["image"], raw["report"]["attachments"][0]["data"])
        q, notice = model.Project.load(self.path)
        self.assertIsNone(notice)
        self.assertEqual(q.underlays[0].image, p.underlays[0].image)
        self.assertTrue(q.reserved)
        self.assertEqual((q.job_id, q.series_id), ("job-1", "series-1"))

    def test_failed_replace_keeps_the_original_document_and_does_not_mutate_the_project(self):
        p = self.project()
        p.save(self.path)
        original = self.path.read_bytes()
        p.name = "Modified"
        before = copy.deepcopy(p.to_json())
        import meridiana.project_archive as archive
        real_replace = archive.os.replace

        def fail_target(source, target):
            if Path(target) == self.path:
                raise OSError("disk disconnected")
            return real_replace(source, target)

        with mock.patch.object(archive.os, "replace", side_effect=fail_target):
            with self.assertRaisesRegex(OSError, "disconnected"):
                p.save(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(p.to_json(), before)
        self.assertEqual(list(self.folder.glob("*.tmp")), [])

    def test_corrupt_resource_falls_back_to_valid_backup_and_resave_preserves_that_backup(self):
        p = self.project()
        p.save(self.path)
        p.name = "Later"
        p.save(self.path)
        good_backup = self.path.with_name(self.path.name + ".bak").read_bytes()

        def corrupt(entries):
            asset = next(name for name in entries if name.startswith("assets/"))
            entries[asset] = b"bad bytes!"
        self.rewrite(corrupt)
        q, notice = model.Project.load(self.path)
        self.assertEqual(q.name, "Tetto è sud")
        self.assertIn("previous", notice)
        q.save(self.path)
        self.assertEqual(self.path.with_name(self.path.name + ".bak").read_bytes(), good_backup)

    def test_future_container_version_is_not_hidden_by_a_backup(self):
        self.project().save(self.path)
        self.project().save(self.path)

        def future(entries):
            manifest = json.loads(entries["manifest.json"])
            manifest["container_version"] = 999
            entries["manifest.json"] = json.dumps(manifest).encode()
        self.rewrite(future)
        with self.assertRaisesRegex(ValueError, "newer"):
            model.Project.load(self.path)

    def test_archive_paths_duplicates_and_unlisted_members_are_rejected(self):
        from meridiana import project_archive as archive
        for name in ("../outside", "/outside", "assets/../outside", "unlisted"):
            with self.subTest(name=name):
                self.project().save(self.path)
                self.rewrite(lambda entries, name=name: entries.update({name: b"x"}))
                with self.assertRaises(ValueError):
                    archive.read(self.path)
        self.project().save(self.path)
        with zipfile.ZipFile(self.path, "a") as z:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr("mimetype", archive.MIMETYPE)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            archive.read(self.path)

    def test_limits_apply_before_resource_decode_and_decompression(self):
        from meridiana import project_archive as archive
        p = self.project()
        with mock.patch.object(archive, "RESOURCE_LIMIT", 4):
            with self.assertRaisesRegex(ValueError, "limit"):
                p.save(self.path)
        self.assertFalse(self.path.exists())
        p.save(self.path)
        with mock.patch.object(archive, "RESOURCE_LIMIT", 4):
            with self.assertRaisesRegex(ValueError, "limit"):
                archive.read(self.path)
        with mock.patch.object(archive, "TOTAL_LIMIT", 8):
            with self.assertRaisesRegex(ValueError, "limit"):
                archive.read(self.path)

    def test_entry_limit_is_checked_before_zipfile_allocates_the_directory(self):
        from meridiana import project_archive as archive
        self.project().save(self.path)
        with mock.patch.object(archive, "ENTRY_LIMIT", 2), \
                mock.patch.object(zipfile, "ZipFile", side_effect=AssertionError("directory already allocated")):
            with self.assertRaisesRegex(ValueError, "limit"):
                archive.read(self.path)

    def test_resource_references_are_only_interpreted_in_known_binary_fields(self):
        from meridiana import project_archive as archive
        data = self.project().to_json()
        data["resources"]["extension"] = {"$asset": "not-an-asset"}
        archive.write(self.path, data)
        self.assertEqual(archive.read(self.path)["resources"]["extension"], {"$asset": "not-an-asset"})

    def test_index_reads_mer_metadata_without_opening_binary_resources_and_keeps_privacy(self):
        self.project().save(self.path)
        original = zipfile.ZipFile.open

        def without_assets(z, name, *args, **kwargs):
            filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
            self.assertFalse(filename.startswith("assets/"))
            return original(z, name, *args, **kwargs)

        with mock.patch.object(zipfile.ZipFile, "open", without_assets):
            rows = project_index.scan([(self.folder, {})])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Tetto è sud")
        self.assertTrue(rows[0]["reserved"])

    def test_recovery_embeds_an_attachment_added_since_the_last_save(self):
        p = self.project()
        attachment = self.folder / "new.pdf"
        attachment.write_bytes(b"new data")
        p.report["attachments"] = [{"path": str(attachment), "title": "New"}]
        before = copy.deepcopy(p.to_json())
        recovery.write(self.folder / "state", self.path, p.to_json())
        attachment.unlink()
        restored = recovery.pending(self.folder / "state")[0]["project"]
        self.assertEqual(base64.b64decode(restored["report"]["attachments"][0]["data"]), b"new data")
        self.assertEqual(p.to_json(), before)

    def test_changed_project_json_with_an_invalid_hash_is_rejected(self):
        from meridiana import project_archive as archive
        self.project().save(self.path)
        self.rewrite(lambda entries: entries.update({"project.json": b"{}"}))
        with self.assertRaises(ValueError):
            archive.read(self.path)

    def test_non_finite_numbers_are_rejected_even_when_the_archive_digest_is_valid(self):
        from meridiana import project_archive as archive
        for number in (b"1e999", b"-1e999", b"NaN", b"Infinity"):
            with self.subTest(number=number):
                self.project().save(self.path)

                def malformed(entries, number=number):
                    project = json.loads(entries["project.json"])
                    project["resources"]["number"] = 123456789.125
                    raw = json.dumps(project).encode().replace(b"123456789.125", number)
                    entries["project.json"] = raw
                    manifest = json.loads(entries["manifest.json"])
                    manifest["members"]["project.json"] = {
                        "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                    entries["manifest.json"] = json.dumps(manifest).encode()

                self.rewrite(malformed)
                with self.assertRaisesRegex(ValueError, "non-finite"):
                    archive.read(self.path)

    def test_invalid_known_resource_container_is_rejected_as_a_document_error(self):
        from meridiana import project_archive as archive
        self.project().save(self.path)

        def malformed(entries):
            project = json.loads(entries["project.json"])
            project["underlays"] = 17
            entries["project.json"] = json.dumps(project).encode()
            manifest = json.loads(entries["manifest.json"])
            manifest["members"]["project.json"] = {"size": len(entries["project.json"]),
                                                     "sha256": hashlib.sha256(entries["project.json"]).hexdigest()}
            entries["manifest.json"] = json.dumps(manifest).encode()
        self.rewrite(malformed)
        with self.assertRaises(ValueError):
            archive.read(self.path)

    def test_resaving_a_loaded_project_keeps_its_embedded_report_profile_and_logo(self):
        from meridiana import portability
        logo = self.folder / "logo.png"
        logo.write_bytes(b"logo data")
        p = self.project()
        p.save(self.path, report_profile={"name": "Studio", "signer": "Designer", "logo": str(logo)})
        logo.unlink()
        q, _ = model.Project.load(self.path)
        q.save(self.folder / "second.mer")
        r, _ = model.Project.load(self.folder / "second.mer")
        profile = portability.profile(r, self.folder / "cache")
        self.assertEqual(profile["signer"], "Designer")
        self.assertEqual(Path(profile["logo"]).read_bytes(), b"logo data")

    def test_failed_backup_replace_does_not_replace_the_project(self):
        from meridiana import project_archive as archive
        p = self.project()
        p.save(self.path)
        original = self.path.read_bytes()
        with mock.patch.object(archive.os, "replace", side_effect=OSError("backup blocked")):
            with self.assertRaisesRegex(OSError, "backup blocked"):
                p.save(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.folder.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
