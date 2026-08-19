from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quillframe-release-bundle.yml"


class ReleaseWorkflowContractTests(unittest.TestCase):
    def test_v091_release_is_exact_main_and_post_download_verified(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("tags: ['v0.9.1']", text)
        self.assertNotIn("tags: ['v*']", text)
        self.assertIn('test "$RELEASE_TAG" = "v${FRAMEWORK_VERSION}"', text)
        self.assertIn('test "$COMMIT" = "$MAIN_COMMIT"', text)
        self.assertIn('rm "release-out/quillframe-framework-${COMMIT}.second.tar"', text)
        self.assertNotIn("release-out/quillframe-framework-*.tar", text)
        self.assertIn('gh release download "$RELEASE_TAG"', text)
        self.assertIn("sha256sum -c SHA256SUMS", text)
        self.assertIn('tar -xf "$BUNDLE_NAME" -C unpacked', text)
        self.assertIn('python unpacked/quillframe.py doctor', text)
        self.assertIn('python unpacked/quillframe.py self-test', text)
        self.assertIn('python unpacked/project_sdk.py self-test', text)
        self.assertIn('python unpacked/harness/control_plane/mcp_stdio.py --self-test', text)
        self.assertIn('python unpacked/studio/host_bridge.py self-test', text)
        self.assertIn("python -m pip wheel unpacked --no-deps", text)
        self.assertIn("PYTHONPATH=", text)
        self.assertIn("from quillframe import AgentJob, Quillframe", text)


if __name__ == "__main__":
    unittest.main()
