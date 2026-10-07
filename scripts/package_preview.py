"""Create reproducible standalone preview ZIPs; does not publish or install."""
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]

def main():
 subprocess.run([sys.executable,str(ROOT/'scripts/build_plugins.py'),'--check'],check=True)
 folder=ROOT/'build/preview';folder.mkdir(parents=True,exist_ok=True);outputs={}
 for name in ('kontaktlaw','kontaktlaw-text'):
  version=json.loads((ROOT/name/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']
  target=folder/(name+'-'+version+'.zip')
  with ZipFile(target,'w',ZIP_DEFLATED) as z:
   for p in sorted((ROOT/name).rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'):
     info=ZipInfo(str(p.relative_to(ROOT)).replace('\\','/'),date_time=(2026,1,1,0,0,0));info.compress_type=ZIP_DEFLATED;z.writestr(info,p.read_bytes())
  outputs[target.name]=hashlib.sha256(target.read_bytes()).hexdigest()
 (folder/'checksums.json').write_text(json.dumps(outputs,indent=2)+'\n',encoding='utf-8');print(json.dumps(outputs,indent=2))

if __name__=='__main__':main()
