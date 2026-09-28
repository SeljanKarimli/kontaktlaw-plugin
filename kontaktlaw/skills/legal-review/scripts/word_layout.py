"""Surgical DOCX text edits and native Word page previews. No document rebuilding."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from zipfile import ZipFile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def paragraphs(node):
    # Match compare_documents' traversal (text boxes belong to their outer paragraph).
    if node.tag == W + 'p':
        yield node
    elif node.tag == W + 'tbl':
        for row in node.findall(W + 'tr'):
            for cell in row.findall(W + 'tc'):
                yield from paragraphs(cell)
    else:
        for child in node:
            yield from paragraphs(child)


def corrected_docx(source, target, state):
    from lxml import etree as ET
    from compare_documents import xml_text
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve():
        raise ValueError('The source must not be overwritten.')
    if hashlib.sha256(source.read_bytes()).hexdigest() != state['input']['sha256']:
        raise ValueError('Source changed since extraction.')
    spans = {s['id']: s for s in state['original']}
    by_part = {}
    for change in state['corrections']:
        if any(c in change['replacement'] for c in ('\n','\r','\t')):
            raise ValueError('Grammar edits must not introduce paragraph breaks or tabs.')
        span = spans[change['span_id']]
        part = span['locator'].split(',')[0]
        by_part.setdefault(part, []).append((span, change))
    replacements = {}
    with ZipFile(source) as archive:
        for part, edits in by_part.items():
            root = ET.fromstring(archive.read(part), ET.XMLParser(resolve_entities=False, no_network=True))
            if any(n.tag in {W+'ins', W+'del', W+'moveFrom', W+'moveTo'} for n in root.iter()):
                raise ValueError('Resolve tracked changes in Word before format-preserving edits.')
            ps = list(paragraphs(root))
            for span, change in sorted(edits, key=lambda item: item[1]['start'], reverse=True):
                number = int(re.search(r'paragraph (\d+)$', span['locator'])[1])
                p = ps[number - 1]
                text = xml_text(p)
                start, end = change['start'], change['end']
                if text[start:end] != change['quote']:
                    raise ValueError('DOCX paragraph does not match the approved correction.')
                cursor, touched = 0, []
                for n in p.iter():
                    value = (n.text or '') if n.tag == W+'t' else '\t' if n.tag == W+'tab' else '\n' if n.tag in {W+'br', W+'cr'} else ''
                    right = cursor + len(value)
                    if value and cursor < end and right > start:
                        if n.tag != W+'t':
                            raise ValueError('Corrections cannot remove tabs or breaks.')
                        touched.append((n, cursor, right))
                    cursor = right
                if not touched:
                    raise ValueError('No editable Word text found.')
                # Reject different run formatting rather than flattening it.
                styles = [ET.tostring(n.getparent().find(W+'rPr')) if n.getparent().find(W+'rPr') is not None else b'' for n, _, _ in touched]
                if len(set(styles)) != 1:
                    raise ValueError('Split this correction into spans with identical run formatting.')
                for i, (n, left, right) in enumerate(touched):
                    old = n.text or ''
                    n.text = old[:max(0,start-left)] + (change['replacement'] if i == 0 else '') + old[min(len(old),end-left):]
                    n.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
            replacements[part] = ET.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        temporary = target.with_suffix('.tmp')
        try:
            with ZipFile(temporary, 'w') as output:
                for item in archive.infolist():
                    output.writestr(item, replacements.get(item.filename, archive.read(item.filename)))
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


def render_pages(directory, state):
    import pymupdf as fitz
    directory = Path(directory).resolve()
    source = Path(state.get('source_path', ''))
    if source.suffix.lower() != '.docx':
        raise ValueError('Native Word preview requires the original DOCX; prepare it again if missing.')
    corrected_docx(source, directory/'corrected.docx', state)
    manifest = {'document_version': state['document_version'], 'findings_packet': state.get('findings_packet'), 'selected_party': state['selected_party'], 'versions': {}}
    script = Path(__file__).with_name('render_word.py')
    for version, docx in [('original', source), ('corrected', directory/'corrected.docx')]:
        pdf = directory / (version+'.pdf')
        subprocess.run([sys.executable,str(script),str(docx),str(pdf)], check=True, timeout=120,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with fitz.open(pdf) as document:
            pages, locations, unresolved = [], {}, []
            normalized = ' '.join(' '.join(p.get_text() for p in document).split())
            for risk in state['findings']:
                boxes = []
                if not risk['anchors']:
                    unresolved.append(risk['id'])
                for anchor in risk['anchors']:
                    quote = ' '.join(anchor[version]['quote'].split())
                    # Repeated or uncertain quotations are never guessed.
                    if not quote or normalized.count(quote) != 1:
                        unresolved.append(risk['id']); continue
                    matches = [(i, rect) for i, page in enumerate(document) for rect in page.search_for(quote)]
                    if not matches:
                        unresolved.append(risk['id'])
                    for i, rect in matches:
                        page = document[i]
                        boxes.append({'page':i+1, 'x':rect.x0/page.rect.width*100,
                                      'y':rect.y0/page.rect.height*100, 'width':rect.width/page.rect.width*100,
                                      'height':rect.height/page.rect.height*100})
                locations[risk['id']] = boxes
            for i, page in enumerate(document, 1):
                name = f'{version}-page-{i}.png'
                page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(directory/name)
                pages.append({'image':name,'width':page.rect.width,'height':page.rect.height})
            manifest['versions'][version] = {'pages':pages,'risks':locations,'unresolved':sorted(set(unresolved))}
    manifest['page_count_matches'] = len(manifest['versions']['original']['pages']) == len(manifest['versions']['corrected']['pages'])
    (directory/'layout.json').write_text(json.dumps(manifest), encoding='utf-8')
    return manifest
