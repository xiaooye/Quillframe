from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core_operations import CoreOperations
from persistence.quillframe_sqlite import QuillframeStore


class NativeProjectPublicContractTests(unittest.TestCase):
    def test_core_project_outputs_are_native_and_never_db_shaped(self):
        with tempfile.TemporaryDirectory(prefix="qf-native-public-") as tmp:
            store = QuillframeStore(Path(tmp))
            store.create_project("NATIVE-PUBLIC", "Native Public", "en-US")
            ops = CoreOperations(store)
            inspect = ops.project_inspect("NATIVE-PUBLIC")
            listing = ops.project_list()

        self.assertEqual(inspect["schema"], "quillframe_project_inspection_v1_0")
        self.assertEqual(inspect["manifest"]["schema"], "quillframe_project_v1_0")
        self.assertEqual(inspect["manifest"]["id"], "NATIVE-PUBLIC")
        self.assertEqual(inspect["scope"], "novel")
        self.assertEqual(inspect["data_boundary"], ".quillframe/data")
        self.assertFalse(inspect["authority"])
        self.assertTrue(inspect["manifest_fingerprint"].startswith("sha256:"))
        self.assertNotIn("project", inspect)
        self.assertNotIn("project_schema_version", str(inspect))
        self.assertEqual(listing["schema"], "quillframe_project_list_v1_0")
        self.assertFalse(listing["authority"])
        self.assertEqual(listing["items"][0]["id"], "NATIVE-PUBLIC")
        self.assertNotIn("project_id", listing["items"][0])
        self.assertNotIn("project_schema_version", str(listing))


if __name__ == "__main__":
    unittest.main()
