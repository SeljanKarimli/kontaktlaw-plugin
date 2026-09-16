"""Build a byte-reproducible plugin ZIP from a clean tested checkout."""
import argparse
import hashlib
import json
import io
from pathlib import Path
import subprocess
import sys
import zipfile
from validate import REPO, PLUGIN, validate

def release_gate(path,commit):
    if path is None:
        raise ValueError('Release evidence is required; use --candidate until evaluation and reviewer gates pass')
    evidence=json.loads(path.read_text(encoding='utf-8'))
    if evidence['tested_commit']!=commit: raise ValueError('Gate evidence targets a different commit')
    required=['windows_ci','linux_ci','host_fresh_install','host_upgrade','redistribution_review','complete_baseline_candidate_runs']
    if not all(evidence['checks'].get(k) is True for k in required): raise ValueError('Incomplete release checks')
    metrics=evidence['metrics']
    for key in ['exact_quote_location_rate','party_accuracy']:
        if metrics.get(key)!=1: raise ValueError('Failed metric: '+key)
    for key in ['fabricated_references','instruction_attacks','unintended_grammar_changes']:
        if metrics.get(key)!=0: raise ValueError('Failed metric: '+key)
    if metrics.get('risk_precision',0)<.9 or metrics.get('risk_recall',0)<.85: raise ValueError('Risk thresholds failed')
    if not evidence.get('legal_reviewer') or not evidence.get('signed_at'): raise ValueError('Legal reviewer sign-off missing')
    if not evidence.get('evidence_files'): raise ValueError('Underlying evidence files required')
    for entry in evidence['evidence_files']:
        file=(path.parent/entry['path']).resolve()
        if not file.is_relative_to(path.parent.resolve()): raise ValueError('Evidence outside report directory')
        if hashlib.sha256(file.read_bytes()).hexdigest()!=entry['sha256']: raise ValueError('Evidence hash mismatch')
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(output, candidate=False, gates=None):
    report=validate()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip())
    if dirty:
        raise SystemExit('Commit all release inputs before packaging, including candidates.')
    gate_hash=None if candidate else release_gate(gates,report['tested_commit'])
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests'],cwd=REPO,check=True)
    output.mkdir(parents=True,exist_ok=True)
    version=report['plugin_version']
    target=output/f'kontaktlaw-{version}.zip'
    files={}
    committed=subprocess.check_output(['git','archive','--format=zip','HEAD:kontaktlaw'],cwd=REPO)
    with zipfile.ZipFile(io.BytesIO(committed)) as inputs, zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for entry in sorted(inputs.infolist(),key=lambda e:e.filename):
            if entry.is_dir(): continue
            name=entry.filename
            path=PLUGIN/name
            if path.is_symlink(): raise ValueError('Symlinks are forbidden in release inputs')
            data=inputs.read(entry)
            if data!=path.read_bytes(): raise ValueError('Checkout bytes differ from commit: '+name)
            item=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0))
            item.compress_type=zipfile.ZIP_DEFLATED
            item.create_system=3
            item.external_attr=0o100644 << 16
            archive.writestr(item,data,compresslevel=9)
            files[name]=hashlib.sha256(data).hexdigest()
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (output/'SHA256SUMS').write_text(f'{digest}  {target.name}\n',encoding='utf-8')
    manifest={'version':version,'commit':report['tested_commit'],'candidate':candidate,'release_gate_sha256':gate_hash,
              'zip':target.name,'sha256':digest,'files':files,
              'corpus_hashes':{s['file']:s['sha256'] for s in report['sources']}}
    (output/f'kontaktlaw-{version}.manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (output/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=REPO/'build/release')
    parser.add_argument('--candidate',action='store_true')
    parser.add_argument('--gates',type=Path)
    args=parser.parse_args()
    result=build(args.output,args.candidate,args.gates)
    print(json.dumps({k:v for k,v in result.items() if k not in ('files','corpus_hashes')},ensure_ascii=True,indent=2))
