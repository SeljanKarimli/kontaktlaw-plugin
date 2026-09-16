"""Stage a verified plugin in a local folder; registration uses plugin-creator.

Never overwrite an unmanaged or user-modified installation. Retain old versions.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

STATE='.kontaktlaw-install.json'
def full_path(path):
    path=path.resolve()
    value=str(path)
    if os.name=='nt' and not value.startswith('\\\\?\\'):
        value='\\\\?\\UNC\\'+value[2:] if value.startswith('\\\\') else '\\\\?\\'+value
        return Path(value)
    return path

def hashes(root):
    root=full_path(root)
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and p.name!=STATE and '__pycache__' not in p.parts}

def install(archive, manifest_path, parent):
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=manifest['sha256']:
        raise ValueError('ZIP checksum mismatch')
    parent=full_path(parent); parent.mkdir(parents=True,exist_ok=True)
    target=parent/'kontaktlaw'
    if target.is_symlink() or target.resolve()!=parent/'kontaktlaw': raise ValueError('Installation target must not be a symlink or junction')
    if target.exists():
        state=target/STATE
        if not state.is_file() or hashes(target)!=json.loads(state.read_text(encoding='utf-8'))['files']:
            raise ValueError('Existing installation is unmanaged or modified; preserve it and choose a new folder')
        if any(p.is_symlink() or not p.resolve().is_relative_to(target.resolve()) for p in target.rglob('*')): raise ValueError('Installation contains a symlink or external junction')
    with tempfile.TemporaryDirectory(prefix='.kontaktlaw-',dir=parent) as temporary:
        staged=Path(temporary)/'kontaktlaw'; staged.mkdir()
        with zipfile.ZipFile(archive) as source:
            names=[]
            for info in source.infolist():
                name=PurePosixPath(info.filename)
                if name.is_absolute() or '..' in name.parts or '\\' in info.filename or ':' in info.filename:
                    raise ValueError('Unsafe ZIP path')
                if info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Unexpected directory or symbolic link in ZIP')
                names.append(info.filename)
            if len(names)!=len(set(names)) or set(names)!=set(manifest['files']):
                raise ValueError('ZIP file inventory mismatch')
            source.extractall(staged)
        if hashes(staged)!=manifest['files']: raise ValueError('Extracted file checksum mismatch')
        plugin=json.loads((staged/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        if plugin['name']!='kontaktlaw': raise ValueError('Wrong plugin')
        (staged/STATE).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        backup=None
        if target.exists():
            backup=parent/'kontaktlaw.previous'
            if backup.exists(): raise ValueError('Rollback folder already exists; preserve it or choose a new folder')
            target.rename(backup)
        try: staged.rename(target)
        except Exception:
            if backup: backup.rename(target)
            raise
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--zip',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--parent',type=Path,required=True)
    args=parser.parse_args()
    print(install(args.zip,args.manifest,args.parent))
