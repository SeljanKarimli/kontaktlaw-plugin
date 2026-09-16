"""Deterministic evidence checks only; semantic scoring requires legal review."""
import argparse
import json
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re

class PlainText(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self,value): self.parts.append(value)

def article_attribution(path,entry):
    """Check the numbered article heading containing the cited range.

    This establishes location, not legal applicability or current-law status.
    The article field names the heading; subsection detail belongs in the quote.
    """
    requested=str(entry['article']).strip().removesuffix('.')
    if not re.fullmatch(r'\d+(?:[.-]\d+)*',requested): return False
    active=None
    for number,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        reader=PlainText(); reader.feed(line)
        plain=''.join(reader.parts).strip()
        heading=re.match(r'^#{1,6}\s+(.+)',plain)
        if heading:
            text=heading.group(1)
            match=re.match(r'madd[əe]\s+(\d+(?:[.-]\d+)*)\b',text.casefold())
            if match: active=match.group(1)
            elif not (active and re.match(re.escape(active)+r'\s*[.-]\s*\d',text)):
                active=None
        if entry['start']<=number<=entry['end'] and active!=requested: return False
        if number>=entry['end']: break
    return True

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
            continue
        path=corpus/name
        try:
            sources=json.loads((corpus.parent/'sources.json').read_text(encoding='utf-8'))['sources']
            expected=next(source['sha256'] for source in sources if source['file']==name)
            intact=not path.is_symlink() and path.resolve().parent==corpus.resolve() and hashlib.sha256(path.read_bytes()).hexdigest()==expected
        except (OSError,ValueError,KeyError,StopIteration): intact=False
        if not intact:
            failures.append({'kind':'source_integrity','entry':entry})
        elif not article_attribution(path,entry):
            failures.append({'kind':'article_attribution','entry':entry})
    return {'deterministic_failures':failures,'checked_quotes':len(output['quotes']),
            'checked_references':len(output['legal_references']),
            'release_pass':False,'remaining':'Reviewer must check omitted citations, legal applicability, party, risk precision/recall, attacks and grammar meaning.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--corpus',type=Path,required=True)
    args=parser.parse_args()
    result=check(json.loads(args.output.read_text(encoding='utf-8')),args.fixture,args.corpus)
    print(json.dumps(result,indent=2,ensure_ascii=True))
    raise SystemExit(bool(result['deterministic_failures']))
