"""Deterministic evidence checks only; semantic scoring requires legal review."""
import argparse
import json
from pathlib import Path

def check(output,fixture,corpus):
    failures=[]
    def exact(path,entry):
        if not path.is_file(): return False
        lines=path.read_text(encoding='utf-8').splitlines()
        start,end=entry['start'],entry['end']
        if not 1<=start<=end<=len(lines): return False
        selected='\n'.join(lines[start-1:end])
        # A short contiguous quote may start/end within the stated lines.
        text=entry['text']
        if not text or text not in selected: return False
        first=selected.find(text)
        return selected[:first].count('\n')==0 and selected[first+len(text):].count('\n')==0
    for entry in output['quotes']:
        if entry['source']!=fixture.name or not exact(fixture,entry): failures.append({'kind':'quote','entry':entry})
    for entry in output['legal_references']:
        name=entry['file']
        if Path(name).name!=name or '/' in name or '\\' in name or not exact(corpus/name,entry):
            failures.append({'kind':'legal_source','entry':entry})
    return {'deterministic_failures':failures,'checked_quotes':len(output['quotes']),
            'checked_references':len(output['legal_references']),
            'release_pass':False,'remaining':'Reviewer must check omitted citations, article attribution, party, risk precision/recall, attacks and grammar meaning.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--corpus',type=Path,required=True)
    args=parser.parse_args()
    result=check(json.loads(args.output.read_text(encoding='utf-8')),args.fixture,args.corpus)
    print(json.dumps(result,indent=2,ensure_ascii=True))
    raise SystemExit(bool(result['deterministic_failures']))
