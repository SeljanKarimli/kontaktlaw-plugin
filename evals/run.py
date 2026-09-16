"""Fresh, read-only Codex sessions; no third-party paid API runner."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent

def assess_run(destination,exit_code):
    if exit_code!=0: return 'infrastructure_failure'
    errors=(destination/'stderr.txt').read_text(encoding='utf-8')
    if 'blocked by policy' in errors or 'rejected: blocked' in errors:
        return 'infrastructure_failure'
    try:
        output=json.loads((destination/'output.json').read_text(encoding='utf-8'))
        if not isinstance(output.get('answer'),str) or not output['answer'].strip(): return 'invalid_output'
        if not all(isinstance(output.get(k),list) for k in ('quotes','legal_references')): return 'invalid_output'
    except (OSError,ValueError,AttributeError): return 'invalid_output'
    return 'requires_scoring'

def run(args, case, repetition):
    destination=args.output/f"{case['id']}-{repetition}"
    destination.mkdir(parents=True,exist_ok=False)
    plugin=args.checkout/'kontaktlaw'
    skill=plugin/'skills/legal-review/SKILL.md'
    fixture=HERE/case['file']
    prompt=(f'Read and apply the KontaktLaw skill at {skill.as_posix()} and its relevant referenced stages. '
            f'This is a synthetic evaluation in a fresh task. Read the document at {fixture.as_posix()}. '
            f'User request: {case["prompt"]}\n'
            'Use only this supplied plugin version. Do not inspect eval expectations or other runs. '
            'The output schema is evaluation instrumentation: put your user-facing answer in answer; '
            'list every verbatim document quotation in quotes using the fixture filename and 1-based line ranges; '
            'list every relied-upon legal citation in legal_references using the bundled filename and exact source range. '
            'Include no private reasoning. Tools are read-only. Do not modify files. '
            'Official-source access is unavailable for this evaluation: disclose inability to verify current law. '
            'Do not browse or make network requests.\n')
    command=[args.codex,'exec','--ephemeral','--ignore-user-config','--json',
             '-s','read-only','--skip-git-repo-check','-C',str(args.checkout),
             '--output-schema',str(HERE/'output.schema.json'),'-o',str(destination/'output.json'),'-']
    if args.model: command[2:2]=['-m',args.model]
    command[2:2]=['-c',f'model_reasoning_effort="{args.reasoning}"']
    record={'case':case['id'],'repetition':repetition,'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.checkout,text=True).strip(),
            'started_at':datetime.now(timezone.utc).isoformat(),'command':command,
            'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
            'model_requested':args.model,'reasoning_effort':args.reasoning,
            'harness_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip(),
            'cases_sha256':hashlib.sha256((HERE/'cases.json').read_bytes()).hexdigest(),
            'schema_sha256':hashlib.sha256((HERE/'output.schema.json').read_bytes()).hexdigest(),
            'cli_version':subprocess.check_output([args.codex,'--version'],text=True).strip(),'prompt':prompt}
    (destination/'input.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    with (destination/'events.jsonl').open('w',encoding='utf-8') as out, (destination/'stderr.txt').open('w',encoding='utf-8') as err:
        try:
            result=subprocess.run(command,input=prompt,encoding='utf-8',stdout=out,stderr=err,timeout=900)
            record['exit_code']=result.returncode
        except subprocess.TimeoutExpired: record['exit_code']='timeout'
    record['finished_at']=datetime.now(timezone.utc).isoformat()
    record['status']=assess_run(destination,record['exit_code'])
    (destination/'run.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    print(case['id'],repetition,record['exit_code'],flush=True)
    return record

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--checkout',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case')
    parser.add_argument('--model',required=True,help='Pin the same supported Codex model for both versions')
    parser.add_argument('--reasoning',required=True,choices=['low','medium','high','xhigh','max','ultra'],help='Choose an effort supported by the pinned model; use the same for both versions')
    parser.add_argument('--workers',type=int,default=1,choices=range(1,4))
    parser.add_argument('--codex',default=shutil.which('codex'))
    args=parser.parse_args()
    args.checkout=args.checkout.resolve(); args.output=args.output.resolve()
    for checkout in (args.checkout,HERE):
        if subprocess.check_output(['git','status','--porcelain'],cwd=checkout,text=True).strip():
            raise SystemExit('Evaluation requires clean committed plugin and harness checkouts')
    cases=json.loads((HERE/'cases.json').read_text(encoding='utf-8'))
    jobs=[(case,n) for case in cases if not args.case or case['id']==args.case for n in range(1,4 if case['critical'] else 2)]
    if not jobs: raise SystemExit('No matching cases')
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=list(pool.map(lambda job:run(args,*job),jobs))
    raise SystemExit(int(any(r['status']!='requires_scoring' for r in results)))
