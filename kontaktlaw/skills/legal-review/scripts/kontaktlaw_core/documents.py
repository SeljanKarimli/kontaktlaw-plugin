"""Extraction and conservative OOXML edits preserving untouched ZIP entries."""
from __future__ import annotations
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from .exchange import envelope, require_valid, document_hash

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NS = {'w': W[1:-1]}
ET.register_namespace('w', W[1:-1])

def text_of(node):
    return ''.join((n.text or '') if n.tag in (W+'t', W+'delText') else '\t' if n.tag == W+'tab' else '\n' if n.tag in (W+'br', W+'cr') else '' for n in node.iter())

def revision_view(node, excluded):
    if node.tag == W+excluded: return ''
    if node.tag in (W+'t',W+'delText'): return node.text or ''
    if node.tag == W+'tab': return '\t'
    if node.tag in (W+'br',W+'cr'): return '\n'
    return ''.join(revision_view(child,excluded) for child in node)

def extract(path, ocr=False, ocr_languages='aze+eng+rus'):
    path = Path(path)
    spans, warnings = [], []
    comments = []
    complete = True
    if path.suffix.lower() == '.docx':
        with ZipFile(path) as z:
            root = ET.fromstring(z.read('word/document.xml'))
            for idx, p in enumerate(root.iter(W+'p')):
                text = text_of(p)
                if not text: continue
                revisions = [{'type': 'insertion' if n.tag == W+'ins' else 'deletion',
                              'text': text_of(n), 'author': n.get(W+'author'), 'date': n.get(W+'date')}
                             for n in p.iter() if n.tag in (W+'ins', W+'del')]
                base={'locator': f'paragraph {idx+1}', 'revisions': revisions,
                      'comment_ids': [n.get(W+'id') for n in p.iter(W+'commentRangeStart')]}
                if revisions:
                    for variant,excluded in [('original','ins'),('revised','del')]:
                        spans.append({**base,'id':f'p{idx}-{variant}','text':revision_view(p,excluded),'variant':variant})
                else: spans.append({**base,'id':f'p{idx}','text':text,'variant':'current'})
            for name in z.namelist():
                if re.match(r'word/(header\d+|footer\d+|footnotes|endnotes)\.xml$', name):
                    part = ET.fromstring(z.read(name))
                    for i, p in enumerate(part.iter(W+'p')):
                        if text_of(p): spans.append({'id': f'{name}:{i}', 'text': text_of(p), 'locator': f'{name} paragraph {i+1}', 'variant': 'context'})
            if 'word/comments.xml' in z.namelist():
                comments = [{'id': n.get(W+'id'), 'text': text_of(n)} for n in ET.fromstring(z.read('word/comments.xml')).iter(W+'comment')]
            if any(n.tag in (W+'drawing', W+'pict', W+'altChunk') for n in root.iter()):
                complete = False; warnings.append('Embedded graphics/content require visual inspection; text extraction is incomplete.')
            if any(s.get('revisions') for s in spans): warnings.append('Unaccepted revisions are preserved as alternatives; resolve operative version before editing.')
    elif path.suffix.lower() == '.pdf':
        try: import pymupdf as fitz
        except ImportError as e: raise ValueError('PDF extraction requires PyMuPDF. Install requirements-document.txt.') from e
        with fitz.open(path) as pdf:
            for i, page in enumerate(pdf):
                text = page.get_text(sort=True).strip()
                method = 'pdf-text'
                if not text and ocr:
                    if not shutil.which('tesseract'): raise ValueError('OCR requested but Tesseract is unavailable.')
                    with tempfile.TemporaryDirectory() as temp:
                        png = Path(temp)/'page.png'
                        page.get_pixmap(dpi=300).save(str(png))
                        run = subprocess.run(['tesseract', str(png), 'stdout', '-l', ocr_languages], capture_output=True, text=True, encoding='utf-8', timeout=120)
                        if run.returncode: raise ValueError(f'OCR failed on page {i+1}: {run.stderr[:400]}')
                        text = run.stdout.strip(); method = 'ocr'
                    warnings.append(f'Page {i+1}: OCR requires visual verification of numbers, names and negations.')
                    complete = False
                if not text:
                    complete = False; warnings.append(f'Page {i+1}: no readable text. OCR or manual transcription required.')
                elif page.get_images() and method == 'pdf-text':
                    complete = False; warnings.append(f'Page {i+1}: embedded images may contain unextracted text; inspect visually.')
                spans.append({'id': f'page{i+1}', 'text': text, 'locator': f'page {i+1}', 'page': i+1, 'method': method, 'variant': 'current'})
    elif path.suffix.lower() in {'.txt', '.md'}:
        text = path.read_text(encoding='utf-8-sig')
        spans = [{'id': f'line{i+1}', 'text': t, 'locator': f'line {i+1}', 'variant': 'current'} for i,t in enumerate(text.splitlines()) if t.strip()]
    else: raise ValueError('Supported formats: DOCX, PDF, TXT and Markdown.')
    if not spans: raise ValueError('No readable content found.')
    for span in spans:
        match=re.match(r'^\s*(\d+(?:\.\d+)*)(?:[.)]|\s)',span['text'])
        if match:span['clause_id']=match.group(1)
    result = envelope(spans, path.name, file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), comments=comments)
    result['coverage'].update(extraction_complete=complete, warnings=warnings)
    return result

def apply_docx(source, result, output, selected_ids, grammar_policy="conservative"):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve() or output.exists(): raise ValueError('Use a new output filename; originals are never overwritten.')
    original = extract(source)
    require_valid(result, original, grammar_policy)
    edits = [e for e in result['edits'] if e['id'] in selected_ids]
    if set(selected_ids) != {e['id'] for e in edits}: raise ValueError('Unknown edit selection.')
    with ZipFile(source) as z:
        root = ET.fromstring(z.read('word/document.xml'))
        paragraphs = list(root.iter(W+'p'))
        for edit in sorted(edits, key=lambda e: (e['span_id'], -e['start'])):
            if not re.fullmatch(r'p\d+', edit['span_id']): raise ValueError('Only body paragraph edits are supported.')
            p = paragraphs[int(edit['span_id'][1:])]
            # Limit edits to an ordinary single text node; do not flatten runs,
            # fields, bookmarks, hyperlinks, revisions or comment boundaries.
            if any(n.tag in (W+'ins', W+'del', W+'fldChar', W+'instrText', W+'hyperlink', W+'sdt', W+'tab', W+'br', W+'cr') for n in p.iter()):
                raise ValueError('Complex paragraph: apply this edit in Word instead.')
            pos, matched = 0, False
            for n in p.iter(W+'t'):
                value = n.text or ''
                if pos <= edit['start'] and edit['end'] <= pos+len(value):
                    a,b = edit['start']-pos, edit['end']-pos
                    if value[a:b] != edit['quote']: raise ValueError('Target changed during edit application.')
                    n.text = value[:a] + edit['replacement'] + value[b:]
                    n.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                    matched=True; break
                pos += len(value)
            if not matched:
                nodes=list(p.iter(W+'t')); position=0; affected=[]
                for node in nodes:
                    value=node.text or ''; a=max(0,edit['start']-position); b=min(len(value),edit['end']-position)
                    if a<b: affected.append((node,value,a,b))
                    position+=len(value)
                if ''.join(value[a:b] for _,value,a,b in affected)!=edit['quote']: raise ValueError('Cross-run target mismatch')
                remaining=edit['replacement']
                for index,(node,value,a,b) in enumerate(affected):
                    take=len(remaining) if index==len(affected)-1 else min(b-a,len(remaining))
                    node.text=value[:a]+remaining[:take]+value[b:];remaining=remaining[take:]
                    node.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
        data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        # Keep all namespace declarations, including prefixes referenced by mc:Ignorable.
        original_xml = z.read('word/document.xml').decode('utf-8')
        opening = re.search(r'<(?:\w+:)?document\b[^>]*>', original_xml).group(0)
        new_xml = data.decode('utf-8')
        new_open = re.search(r'<(?:\w+:)?document\b[^>]*>', new_xml).group(0)
        declarations = re.findall(r'xmlns(?::[\w]+)?="[^"]*"', opening)
        for declaration in declarations:
            prefix = declaration.split('=')[0]
            if not re.search(re.escape(prefix)+r'=', new_open): new_open = new_open[:-1]+' '+declaration+'>'
        new_xml = re.sub(r'<(?:\w+:)?document\b[^>]*>', lambda _: new_open, new_xml, count=1)
        output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, 'w') as out:
            for item in z.infolist(): out.writestr(item, new_xml.encode('utf-8') if item.filename == 'word/document.xml' else z.read(item.filename))
    return {'output': str(output), 'applied': len(edits), 'layout_verification': 'Render and inspect before delivery; existing revisions remain unchanged.'}

def compare(before, after):
    from difflib import SequenceMatcher
    require_valid(before);require_valid(after)
    left, right = before['document']['spans'], after['document']['spans']
    changes=[]
    for tag,a,b,c,d in SequenceMatcher(None,[s['text'] for s in left],[s['text'] for s in right],autojunk=False).get_opcodes():
        if tag != 'equal': changes.append({'type': tag, 'before': left[a:b], 'after': right[c:d], 'legal_effect': 'Requires contextual legal review'})
    return {'before_sha256': document_hash(left), 'after_sha256': document_hash(right), 'changes': changes}

def clean_docx(source,output,revision_view):
    """Explicitly choose original/revised text; refuse unsupported revision types."""
    source,output=Path(source),Path(output)
    if revision_view not in ('original','revised'):raise ValueError('Explicit revision view required.')
    if source.resolve()==output.resolve() or output.exists():raise ValueError('Use a new output filename.')
    with ZipFile(source) as archive:
        replacements={}
        for name in archive.namelist():
            if not re.match(r'word/(document|header\d+|footer\d+|footnotes|endnotes)\.xml$',name):continue
            raw=archive.read(name);root=ET.fromstring(raw)
            if any(n.tag.startswith(W) and (n.tag[len(W):].endswith('Change') or n.tag[len(W):].startswith('move')) for n in root.iter()):
                raise ValueError('Moved text or formatting revisions require explicit review in Word.')
            for p in root.iter(W+'pPr'):
                if any(n.tag in (W+'ins',W+'del') for n in p.iter()):raise ValueError('Paragraph-mark revisions require Word review.')
            drop='del' if revision_view=='revised' else 'ins'
            unwrap='ins' if revision_view=='revised' else 'del'
            def resolve(parent):
                for child in list(parent):
                    if child.tag in (W+'ins',W+'del') and any(n.tag in (W+'commentRangeStart',W+'commentRangeEnd',W+'commentReference') for n in child.iter()):
                        raise ValueError('Revision intersects a comment anchor; resolve it in Word.')
                    resolve(child)
                    if child.tag==W+drop:parent.remove(child)
                    elif child.tag==W+unwrap:
                        index=list(parent).index(child);parent.remove(child)
                        for offset,grandchild in enumerate(list(child)):parent.insert(index+offset,grandchild)
                    elif child.tag==W+'delText':child.tag=W+'t'
            resolve(root)
            xml=ET.tostring(root,encoding='unicode')
            original_open=re.search(r'<(?:\w+:)?\w+\b[^>]*>',raw.decode('utf-8').split('?>')[-1]).group(0)
            new_open=re.search(r'<(?:\w+:)?\w+\b[^>]*>',xml).group(0)
            for declaration in re.findall(r'xmlns(?::[\w]+)?="[^"]*"',original_open):
                if declaration.split('=')[0]+'=' not in new_open:new_open=new_open[:-1]+' '+declaration+'>'
            xml=re.sub(r'<(?:\w+:)?\w+\b[^>]*>',lambda _:new_open,xml,count=1)
            replacements[name]=xml.encode('utf-8')
        output.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(output,'w') as out:
            for item in archive.infolist():out.writestr(item,replacements.get(item.filename,archive.read(item.filename)))
    return {'output':str(output),'revision_view':revision_view,'visual_verification':'Render and inspect before delivery.'}
