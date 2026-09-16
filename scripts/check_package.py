"""Exercise real ZIP staging and byte-identical rebuilds without user config edits."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from install import install, hashes, full_path

ROOT=Path(__file__).resolve().parents[1]

def check(baseline=None):
    archive=ROOT/'build/release/kontaktlaw-1.1.0.zip'
    manifest=ROOT/'build/release/kontaktlaw-1.1.0.manifest.json'
    expected=json.loads(manifest.read_text(encoding='utf-8'))
    # Extended Windows paths preserve long original corpus filenames.
    with tempfile.TemporaryDirectory(prefix='kontaktlaw-check-',dir=full_path(Path(tempfile.gettempdir()))) as folder:
        parent=Path(folder)
        (parent/'unrelated.txt').write_text('keep')
        if baseline:
            assert hashlib.sha256(baseline.read_bytes()).hexdigest()=='2b19af9b06f24870600f85efe7578231236dce80445cf5f531e8280640e43ff8'
            with zipfile.ZipFile(baseline) as old:
                files={n:hashlib.sha256(old.read(n)).hexdigest() for n in old.namelist() if not n.endswith('/')}
            old_manifest=parent/'baseline.json'
            old_manifest.write_text(json.dumps({'sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'files':files}),encoding='utf-8')
            install(baseline,old_manifest,parent)
        install(archive,manifest,parent)
        assert hashes(parent/'kontaktlaw')==expected['files']
        assert (parent/'unrelated.txt').read_text()=='keep'
        if baseline:
            assert json.loads((parent/'kontaktlaw.previous/.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']=='1.0.0'
        (parent/'kontaktlaw/README.md').write_text('user modification')
        try: install(archive,manifest,parent)
        except ValueError as error: assert 'modified' in str(error)
        else: raise AssertionError('Modified installation overwritten')
    scratch=ROOT/'kontaktlaw/.env.package-test'
    assert not scratch.exists()
    try:
        scratch.write_text('SYNTHETIC_IGNORED_FILE=exclude_me')
        subprocess.run([sys.executable,'-B','scripts/package.py','--candidate','--output','build/repeat'],cwd=ROOT,check=True)
        repeated=ROOT/'build/repeat/kontaktlaw-1.1.0.zip'
        assert repeated.read_bytes()==archive.read_bytes()
        with zipfile.ZipFile(repeated) as packed: assert '.env.package-test' not in packed.namelist()
    finally: scratch.unlink()
    result={'tested_commit':expected['commit'],'real_baseline_zip_upgrade':bool(baseline),
            'preserved_unrelated_files':True,'preserved_modified_install':True,
            'repeat_build_identical':True,'ignored_file_excluded':True,
            'host_marketplace_install':'not tested; folder staging only'}
    (ROOT/'build/package-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--baseline',type=Path); args=parser.parse_args()
    print(json.dumps(check(args.baseline),indent=2))
