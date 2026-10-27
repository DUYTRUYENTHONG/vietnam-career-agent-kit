"""Distribution uses the pinned Git tree, never a local candidate workspace."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from scripts.package_community import build


class CommunityPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'maintainer@example.invalid')
        self.git('config', 'user.name', 'Fictional Maintainer')
        (self.repo / 'README.md').write_text('Fictional community project', encoding='utf8')
        self.git('add', 'README.md')
        self.git('commit', '-qm', 'Initial fictional source')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, check=True, capture_output=True)

    def test_only_committed_public_source_is_packaged_with_matching_manifest(self):
        (self.repo / 'private').mkdir()
        (self.repo / 'private/cv.txt').write_text('Untracked fictional candidate data', encoding='utf8')
        output = self.base / 'share.zip'
        result = build(self.repo, output)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(['vietnam-career-agent-kit/README.md'],
                             [item.filename for item in archive.infolist() if not item.is_dir()])
        manifest = json.loads(output.with_suffix('.manifest.json').read_text(encoding='utf8'))
        self.assertEqual(result, manifest)
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), result['archive_sha256'])
        self.assertEqual(self.git('rev-parse', 'HEAD').stdout.decode().strip(), result['commit'])
        with self.assertRaises(FileExistsError):
            build(self.repo, output)

    def test_tracked_private_artifact_blocks_publication_and_in_repo_output_is_refused(self):
        with self.assertRaises(ValueError):
            build(self.repo, self.repo / 'unsafe.zip')
        (self.repo / 'candidate.pdf').write_text('Fictional PDF must not ship', encoding='utf8')
        self.git('add', 'candidate.pdf')
        self.git('commit', '-qm', 'Fictional bad artifact')
        output = self.base / 'blocked.zip'
        with self.assertRaises(ValueError):
            build(self.repo, output)
        self.assertFalse(output.exists())
