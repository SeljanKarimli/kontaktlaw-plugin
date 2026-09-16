"""Dependency-free release checks. No model-quality or current-law claims."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / 'kontaktlaw'
SPEC = importlib.util.spec_from_file_location('lookup', PLUGIN / 'skills/legal-review/scripts/search_knowledge.py')
lookup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lookup)

class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self, value): self.parts.append(value)

def inventory(lines):
    """Independent audit parser: HTMLParser + token parsing, not chunker regex."""
    articles=[]
    subordinate=[]
    active=None
    history=False
    classifications={'blank':[], 'separator':[], 'metadata':[], 'searchable':[]}
    for number,line in enumerate(lines,1):
        reader=Text(); reader.feed(line); clean=''.join(reader.parts).strip()
        if not clean: kind='blank'
        elif clean == '---': kind='separator'
        elif clean.startswith('>'): kind='metadata'
        else: kind='searchable'
        classifications[kind].append(number)
        if clean.startswith('#'):
            parts=clean.lstrip('#').strip().split()
            heading=' '.join(parts).replace('İ','i').replace('I','ı').casefold()
            if 'mənbə sənədlərinin' in heading or ('dəyişiklik' in heading and 'siyahısı' in heading):
                history=True
            if len(parts)>1 and parts[0].casefold() in ('maddə','madde'):
                token=parts[1].rstrip('.')
                if re.fullmatch(r'[0-9]+(?:[.-][0-9]+)*',token):
                    active=token
                    articles.append({'article':token,'line':number,'section_kind':'source_history' if history else 'snapshot_provision'})
                else:
                    raise AssertionError(f'Unclassified article heading at line {number}: {clean[:100]}')
            elif active and parts and parts[0].rstrip('.')==active and len(parts)>1 and parts[1][0:1].isdigit():
                subordinate.append({'article':active,'line':number})
            elif active and parts and parts[0].startswith(active+'.'):
                subordinate.append({'article':active,'line':number})
            else:
                active=None
    return articles,classifications,subordinate

def ranges(numbers):
    result=[]
    for value in numbers:
        if result and result[-1][1]+1 == value: result[-1][1]=value
        else: result.append([value,value])
    return result

def validate():
    manifest=json.loads((PLUGIN/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    assert manifest['name']=='kontaktlaw'
    sources=[]
    for source in lookup.metadata():
        lines=lookup.source_lines(source)
        articles,classes,subordinate=inventory(lines)
        chunks=list(lookup.chunks(source))
        covered=set()
        for chunk in chunks:
            assert chunk['text']=='\n'.join(lines[chunk['start']-1:chunk['end']])
            covered.update(range(chunk['start'],chunk['end']+1))
        missing=set(classes['searchable'])-covered
        assert not missing,(source['file'], sorted(missing)[:10])
        for entry in articles+subordinate:
            assert any(c['article']==entry['article'] and c['start']<=entry['line']<=c['end'] for c in chunks), entry
        for entry in articles:
            assert any(c['section_kind']==entry['section_kind'] and c['start']<=entry['line']<=c['end'] for c in chunks),entry
        sources.append({'file':source['file'],'sha256':source['sha256'],'articles':articles,
                        'article_count':len(articles),'retrievable_article_count':len(articles),
                        'article_count_scope':'All headings, including historical amendment headings; not current operative article count',
                        'subordinate_headings_verified':subordinate,
                        'searchable_ranges':ranges(classes['searchable']),
                        'exclusions':{k:ranges(v) for k,v in classes.items() if k!='searchable'},
                        'missing_substantive_lines':sorted(missing),'sections':len(chunks)})
    proof=json.loads((PLUGIN/'provenance.json').read_text())
    assert len(proof['prompts'])==12
    for prompt in proof['prompts']:
        assert hashlib.sha256((PLUGIN/prompt['path']).read_bytes()).hexdigest()==prompt['sha256']
    for relative in ['skills/legal-review/SKILL.md','skills/legal-review/references/prompt-guide.md']:
        content=(PLUGIN/relative).read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)',content):
            if '://' not in link: assert ((PLUGIN/relative).parent/link).is_file(),link
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=REPO,text=True).strip())
    return {'plugin_version':manifest['version'],'tested_commit':commit,'tracked_worktree_dirty':dirty,
            'checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'commands':['python -B -m unittest discover -s tests -v','python -B scripts/validate.py'],
            'sources':sources,'prompt_hashes_verified':12,'current_law_verified':False,
            'model_evaluation':'separate eval report required','legal_signoff':'separate reviewer approval required'}

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path); args=parser.parse_args()
    result=validate()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='sources'},indent=2))
    for source in result['sources']:
        print(source['file'], source['article_count'], 'articles;', len(source['missing_substantive_lines']), 'missing lines')
