#!/usr/bin/env python3
"""Read-only, local document comparison. Legal interpretation belongs to the host.

Python 3.10+. Optional PDF/image dependencies: requirements-comparison.txt.
No network requests, model calls, document editing, or automatic OCR verification.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from difflib import SequenceMatcher
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZipFile, BadZipFile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
TOKEN = re.compile(r'\w+|[^\w\s]', re.UNICODE)
SUPPORTED = {'.docx', '.pdf', '.png', '.jpg', '.jpeg'}


class ComparisonError(ValueError):
    """Actionable input/dependency errors without private text in diagnostics."""


def pillow():
    try:
        from PIL import Image, ImageOps
        return Image, ImageOps
    except ImportError as exc:
        raise ComparisonError('Image OCR requires Pillow; install requirements-comparison.txt.') from exc


def pdf_library():
    try:
        import pymupdf
        return pymupdf
    except ImportError as exc:
        raise ComparisonError('PDF comparison requires PyMuPDF; install requirements-comparison.txt.') from exc


def warn(document, code, locator, message):
    document['coverage']['warnings'].append({'code': code, 'locator': locator, 'message': message})
    document['coverage']['extraction_complete'] = False


def add_span(document, text, locator, method='native', **metadata):
    if not text.strip():
        return
    span = {'id': f's{len(document["spans"])+1}', 'text': text,
            'locator': locator, 'method': method, **metadata}
    match = re.match(r'^\s*(\d+(?:\.\d+)*)(?:[.)]|\s)', text)
    if match:
        span['clause_id'] = match.group(1)
    document['spans'].append(span)


class OCR:
    def __init__(self, mode='auto', languages='aze+eng+rus', executable=None,
                 tessdata=None, review_dir=None, timeout=120):
        if mode not in {'auto', 'always', 'never'}:
            raise ComparisonError('OCR mode must be auto, always, or never.')
        if not re.fullmatch(r'[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*', languages):
            raise ComparisonError('Use Tesseract language codes separated by +, for example aze+eng+rus.')
        self.mode, self.languages = mode, languages
        self.executable = executable or os.environ.get('KONTAKTLAW_TESSERACT') or shutil.which('tesseract')
        self.tessdata = tessdata or os.environ.get('TESSDATA_PREFIX')
        self.review_dir = Path(review_dir) if review_dir else None
        self.timeout, self.checked, self.counter = timeout, False, 0

    def run(self, arguments):
        try:
            result = subprocess.run([self.executable, *arguments], capture_output=True,
                                    text=True, encoding='utf-8', errors='replace',
                                    timeout=self.timeout,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired as exc:
            raise ComparisonError(f'OCR exceeded {self.timeout} seconds; use a smaller or clearer scan.') from exc
        except OSError as exc:
            raise ComparisonError('Cannot start Tesseract; check --tesseract and its local dependencies.') from exc
        if result.returncode:
            raise ComparisonError('Tesseract failed. Check image readability and installed language packs.')
        return result.stdout

    def check(self):
        if self.checked:
            return
        if not self.executable:
            raise ComparisonError('Tesseract is unavailable. Install it and aze, eng, rus language packs; '
                                  'use --tesseract PATH or KONTAKTLAW_TESSERACT if it is not on PATH.')
        extra = ['--tessdata-dir', str(self.tessdata)] if self.tessdata else []
        available = set(self.run(['--list-langs', *extra]).splitlines())
        missing = set(self.languages.split('+')) - available
        if missing:
            raise ComparisonError('Missing Tesseract language packs: ' + ', '.join(sorted(missing)) +
                                  '. Install them or explicitly choose --ocr-languages.')
        self.checked = True

    def recognize(self, image):
        self.check()
        _, ImageOps = pillow()
        image = ImageOps.exif_transpose(image).convert('RGB')
        candidates = []
        with tempfile.TemporaryDirectory(prefix='kontaktlaw-ocr-') as temp:
            for angle in (0, 90, 180, 270):
                rotated = image.rotate(angle, expand=True, fillcolor='white')
                file = Path(temp) / 'input.png'
                rotated.save(file)
                args = [str(file), 'stdout', '-l', self.languages, '--psm', '3', '--dpi', '300']
                if self.tessdata:
                    args.extend(['--tessdata-dir', str(self.tessdata)])
                # A variable avoids relying on a separately installed tsv config file.
                args.extend(['-c', 'tessedit_create_tsv=1'])
                rows = list(csv.DictReader(io.StringIO(self.run(args)), delimiter='\t', quoting=csv.QUOTE_NONE))
                words = [row for row in rows if row.get('level') == '5' and (row.get('text') or '').strip()]
                weight = sum(len(row['text']) for row in words)
                score = sum(max(0, float(row['conf'])) * len(row['text']) for row in words) / max(1, weight)
                candidates.append((score, weight, angle, words))
                if angle == 0 and score >= 85 and len(words) >= 4:
                    break
            score, _, angle, words = max(candidates, key=lambda item: (item[0], item[1]))
        evidence = None
        if self.review_dir:
            self.review_dir.mkdir(parents=True, exist_ok=True)
            self.counter += 1
            evidence = self.review_dir / f'ocr-{self.counter:04d}.png'
            with evidence.open('xb') as file:
                image.rotate(angle, expand=True, fillcolor='white').save(file, format='PNG')
        groups = {}
        for row in words:
            key = (row['block_num'], row['par_num'])
            groups.setdefault(key, []).append(row)
        paragraphs = []
        for group in groups.values():
            text, records, previous_line = '', [], None
            for row in group:
                line = row['line_num']
                if text:
                    text += '\n' if previous_line != line else ' '
                start = len(text)
                text += row['text']
                records.append({'text': row['text'], 'start': start, 'end': len(text),
                                'confidence': float(row['conf']),
                                'bbox': [int(row[k]) for k in ('left', 'top', 'width', 'height')]})
                previous_line = line
            paragraphs.append({'text': text, 'ocr_words': records})
        return paragraphs, {'confidence': round(score, 2), 'rotation_ccw': angle,
                            'review_image': str(evidence.resolve()) if evidence else None,
                            'verification': 'required', 'languages': self.languages,
                            'bbox_coordinates': 'pixels in rotated review image; x,y,width,height'}

    def append(self, document, image, locator, **metadata):
        if self.mode == 'never':
            warn(document, 'ocr_disabled', locator, 'Image content was not read because OCR is disabled.')
            return
        paragraphs, details = self.recognize(image)
        warn(document, 'ocr_unverified', locator,
             'Visually verify OCR against the source, especially names, numbers, dates and negations.')
        document['coverage']['ocr_regions'].append({'locator': locator, **details, **metadata})
        if not paragraphs:
            warn(document, 'unreadable_image', locator, 'No text recognized; blank or unreadable image requires inspection.')
        for i, paragraph in enumerate(paragraphs, 1):
            add_span(document, paragraph.pop('text'), f'{locator}, OCR paragraph {i}', 'ocr',
                     ocr=details, **paragraph, **metadata)


def xml_text(node):
    if node.tag in {W+'t', W+'delText'}:
        return node.text or ''
    if node.tag == W+'tab':
        return '\t'
    if node.tag in {W+'br', W+'cr'}:
        return '\n'
    return ''.join(xml_text(child) for child in node)


def select_revision(root, view, part):
    revisions = any(n.tag in {W+'ins', W+'del', W+'moveFrom', W+'moveTo', W+'cellIns', W+'cellDel', W+'cellMerge'} or
                    (n.tag.startswith(W) and n.tag.endswith('Change')) for n in root.iter())
    if not revisions:
        return
    if view is None:
        raise ComparisonError(f'{part}: unresolved tracked changes; ask the user to select original or revised '
                              'with --before-revision / --after-revision.')
    if any(n.tag in {W+'moveFrom', W+'moveTo', W+'cellIns', W+'cellDel', W+'cellMerge'} or
           (n.tag.startswith(W) and n.tag.endswith('Change')) for n in root.iter()):
        raise ComparisonError(f'{part}: complex tracked changes need a user-resolved copy from Word.')
    if any(any(n.tag in {W+'ins', W+'del'} for n in p.iter()) for p in root.iter(W+'pPr')):
        raise ComparisonError(f'{part}: paragraph-mark revisions need a user-resolved copy from Word.')
    discard = W+('ins' if view == 'original' else 'del')
    unwrap = W+('del' if view == 'original' else 'ins')

    def walk(parent):
        for child in list(parent):
            if child.tag == discard:
                parent.remove(child)
                continue
            walk(child)
            if child.tag == unwrap:
                index = list(parent).index(child)
                parent.remove(child)
                for offset, sub in enumerate(list(child)):
                    parent.insert(index+offset, sub)
    walk(root)


def extract_docx(path, document, ocr, revision):
    with ZipFile(path) as archive:
        names = archive.namelist()
        if 'word/document.xml' not in names:
            raise ComparisonError('DOCX has no word/document.xml.')
        parts = ['word/document.xml'] + sorted(n for n in names if re.fullmatch(
            r'word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml', n))
        for part in parts:
            root = ET.fromstring(archive.read(part))
            select_revision(root, revision, part)
            relpath = str(PurePosixPath(part).parent / '_rels' / (PurePosixPath(part).name + '.rels'))
            relationships = {}
            if relpath in names:
                relationships = {n.get('Id'): n.attrib for n in ET.fromstring(archive.read(relpath))}
            counters = Counter()

            def walk(node, context=''):
                if node.tag == W+'tbl':
                    counters['table'] += 1
                    context = f'table {counters["table"]}'
                    rows = node.findall(W+'tr')
                    cells = [row.findall(W+'tc') for row in rows]
                    document.setdefault('tables', []).append({
                        'locator': f'{part}, {context}',
                        'rows': [[xml_text(cell) for cell in row] for row in cells]})
                    if any(n.tag in {W+'gridSpan', W+'vMerge', W+'hMerge'} for n in node.iter()):
                        warn(document, 'merged_table', f'{part}, {context}',
                             'Merged table cells require visual review of row and column relationships.')
                    if len(rows) != len(list(node.iter(W+'tr'))):
                        warn(document, 'complex_table', f'{part}, {context}',
                             'Nested or wrapped table rows require visual review of structure and coverage.')
                    for r, row in enumerate(rows, 1):
                        for c, cell in enumerate(row.findall(W+'tc'), 1):
                            walk(cell, f'{context}, row {r}, cell {c}')
                    return
                if node.tag == W+'p':
                    counters['paragraph'] += 1
                    locator = f'{part}, ' + (context+', ' if context else '') + f'paragraph {counters["paragraph"]}'
                    add_span(document, xml_text(node), locator, part=part)
                    for image in node.iter():
                        if image.tag.split('}')[-1] not in {'blip', 'imagedata'}:
                            continue
                        rid = image.get(R+'embed') or image.get(R+'id') or image.get(R+'link')
                        rel = relationships.get(rid, {})
                        if rel.get('TargetMode') == 'External':
                            warn(document, 'external_image', locator, 'Linked image not fetched; supply a local copy.')
                            continue
                        target = posixpath.normpath(posixpath.join(posixpath.dirname(part), rel.get('Target', '')))
                        if target.startswith('/'):
                            target = target.lstrip('/')
                        if target not in names or not target.startswith('word/'):
                            warn(document, 'missing_image', locator, 'Embedded image could not be resolved.')
                            continue
                        if ocr.mode == 'never':
                            warn(document, 'ocr_disabled', locator, 'Embedded image was not read.')
                            continue
                        Image, _ = pillow()
                        try:
                            with Image.open(io.BytesIO(archive.read(target))) as bitmap:
                                ocr.append(document, bitmap, locator+', '+target, part=part)
                        except (OSError, ValueError) as exc:
                            if isinstance(exc, ComparisonError):
                                raise
                            warn(document, 'unsupported_image', locator, 'Embedded graphic needs visual inspection.')
                    if any(n.tag == W+'txbxContent' for n in node.iter()):
                        warn(document, 'text_box_order', locator, 'Text box reading order requires visual inspection.')
                    if any(n.tag in {W+'object', W+'altChunk'} for n in node.iter()):
                        warn(document, 'unsupported_content', locator, 'Embedded object/content requires separate inspection.')
                    if any(n.tag == W+'drawing' for n in node.iter()) and not any(
                            n.tag.split('}')[-1] in {'blip', 'txbxContent'} for n in node.iter()):
                        warn(document, 'unsupported_drawing', locator, 'Drawing/chart requires visual inspection.')
                    return
                if node.tag in {W+'altChunk', W+'object'}:
                    warn(document, 'unsupported_content', part, 'Embedded object/content requires separate inspection.')
                for child in node:
                    walk(child, context)
            walk(root)
            if any(n.tag == W+'numPr' for n in root.iter()):
                warn(document, 'automatic_numbering', part,
                     'Word automatic numbering is not rendered; use paragraph/table locators and check clause numbering visually.')
            if any(n.tag in {W+'fldChar', W+'instrText'} for n in root.iter()):
                warn(document, 'field_values', part, 'Only cached field text is read; verify displayed field values in Word.')
        if 'word/comments.xml' in names:
            root = ET.fromstring(archive.read('word/comments.xml'))
            document['comments'] = [{'id': n.get(W+'id'), 'text': xml_text(n)} for n in root.iter(W+'comment')]


def extract_pdf(path, document, ocr):
    fitz = pdf_library()
    try:
        opened = fitz.open(path)
    except fitz.FileDataError as exc:
        raise ComparisonError('PDF is corrupt or unreadable; provide a valid PDF copy.') from exc
    with opened as pdf:
        if pdf.needs_pass:
            raise ComparisonError('Encrypted PDF requires a user-supplied unlocked copy; no password guessing is performed.')
        document['page_count'] = len(pdf)
        for number, page in enumerate(pdf, 1):
            locator = f'page {number}'
            # PyMuPDF text/image boxes use unrotated coordinates. Normalize the
            # in-memory render too; never save the source PDF.
            if page.rotation:
                page.set_rotation(0)
            blocks = [b for b in page.get_text('blocks', sort=True) if b[6] == 0 and b[4].strip()]
            images = page.get_image_info()
            # Whole-page OCR for scans; otherwise keep exact native text and OCR each
            # displayed image region with native text masked to avoid duplicate layers.
            if not blocks or ocr.mode == 'always':
                if ocr.mode == 'never':
                    warn(document, 'unreadable_page', locator, 'No native text; OCR is disabled.')
                    continue
                Image, _ = pillow()
                pix = page.get_pixmap(dpi=300, alpha=False)
                with Image.open(io.BytesIO(pix.tobytes('png'))) as bitmap:
                    ocr.append(document, bitmap, locator, page=number, bbox=list(page.rect))
                continue
            entries = [(b[1], b[0], 'text', b) for b in blocks]
            entries += [(item['bbox'][1], item['bbox'][0], 'image', item) for item in images]
            seen_regions = set()
            for _, _, kind, entry in sorted(entries, key=lambda item: (item[0], item[1])):
                if kind == 'text':
                    add_span(document, entry[4], locator+f', block {entry[5]+1}', 'pdf-text',
                             page=number, bbox=list(entry[:4]))
                    if '\ufffd' in entry[4]:
                        warn(document, 'broken_encoding', locator, 'Native text has replacement characters; rerun --ocr always.')
                    continue
                rect = fitz.Rect(entry['bbox']) & page.rect
                key = tuple(rect)
                if rect.is_empty or key in seen_regions:
                    continue
                seen_regions.add(key)
                region = locator+f', image region {len(seen_regions)}'
                if ocr.mode == 'never':
                    warn(document, 'ocr_disabled', region, 'Image region not read; it may contain additional text.')
                    continue
                Image, _ = pillow()
                from PIL import ImageDraw
                pix = page.get_pixmap(dpi=300, clip=rect, alpha=False)
                with Image.open(io.BytesIO(pix.tobytes('png'))) as bitmap:
                    bitmap = bitmap.convert('RGB')
                    draw = ImageDraw.Draw(bitmap)
                    for word in page.get_text('words'):
                        intersection = fitz.Rect(word[:4]) & rect
                        if not intersection.is_empty:
                            draw.rectangle(((intersection.x0*300/72-pix.x, intersection.y0*300/72-pix.y),
                                            (intersection.x1*300/72-pix.x, intersection.y1*300/72-pix.y)), fill='white')
                    ocr.append(document, bitmap, region, page=number, bbox=list(rect), native_text_masked=True)
            if page.first_annot or page.first_widget:
                warn(document, 'pdf_annotations', locator, 'Annotations/form widgets require visual review; body text only.')


def extract(path, ocr=None, revision=None):
    path = Path(path).resolve()
    if path.suffix.lower() not in SUPPORTED:
        raise ComparisonError('Supported formats: DOCX, PDF, PNG, JPG and JPEG.')
    if not path.is_file():
        raise ComparisonError(f'Input file not found: {path.name}')
    if revision not in {None, 'original', 'revised'}:
        raise ComparisonError('Revision view must be original or revised.')
    ocr = ocr or OCR()
    document = {'name': path.name, 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'revision_view': revision, 'spans': [], 'comments': [],
                'coverage': {'extraction_complete': True, 'warnings': [], 'ocr_regions': []}}
    try:
        if path.suffix.lower() == '.docx':
            extract_docx(path, document, ocr, revision)
        elif path.suffix.lower() == '.pdf':
            extract_pdf(path, document, ocr)
        else:
            if ocr.mode == 'never':
                warn(document, 'ocr_disabled', 'image', 'Image input requires OCR.')
            else:
                Image, _ = pillow()
                with Image.open(path) as bitmap:
                    ocr.append(document, bitmap, 'image 1', page=1)
    except (BadZipFile, ET.ParseError, OSError) as exc:
        raise ComparisonError(f'Cannot read {path.name}; provide a valid, readable document.') from exc
    if not document['spans']:
        warn(document, 'no_readable_text', 'document', 'No readable text; comparison is incomplete.')
    if hashlib.sha256(path.read_bytes()).hexdigest() != document['sha256']:
        raise ComparisonError('An input changed during extraction. Retry with stable copies.')
    return document


def tokens(document):
    values, positions = [], []
    for span in document['spans']:
        for match in TOKEN.finditer(span['text']):
            values.append(match.group())
            positions.append((span, match.start(), match.end()))
    return values, positions


def passages(positions, start, end):
    result = []
    for span, a, b in positions[start:end]:
        if result and result[-1]['span_id'] == span['id']:
            result[-1]['end'] = b
            result[-1]['quote'] = span['text'][result[-1]['start']:b]
        else:
            result.append({'span_id': span['id'], 'locator': span['locator'], 'start': a, 'end': b,
                           'quote': span['text'][a:b], 'context': span['text'], 'method': span['method']})
    return result


def occurrence_count(sequence, subsequence):
    size = len(subsequence)
    return sum(sequence[i:i+size] == subsequence for i in range(len(sequence)-size+1))


def anchor(positions, index):
    if not positions:
        return None
    span, start, end = positions[min(index, len(positions)-1)]
    return {'span_id': span['id'], 'locator': span['locator'],
            'offset': start if index < len(positions) else end, 'context': span['text']}


def compare(before, after):
    left, lp = tokens(before)
    right, rp = tokens(after)
    operations = [list(op) for op in SequenceMatcher(None, left, right, autojunk=False).get_opcodes() if op[0] != 'equal']
    # Only pair unique, exact multiword deletion/insertion runs. Repeated clauses
    # and edited moves remain ordinary differences, never speculative moves.
    paired, changes = set(), []
    for i, (tag, a, b, c, d) in enumerate(operations):
        if tag != 'delete' or b-a < 5:
            continue
        signature = left[a:b]
        if occurrence_count(left, signature) != 1 or occurrence_count(right, signature) != 1:
            continue
        candidates = [j for j, (other, _, _, x, y) in enumerate(operations)
                      if other == 'insert' and right[x:y] == signature and j not in paired]
        if len(candidates) == 1:
            j = candidates[0]
            paired.update({i, j})
            changes.append(('move', a, b, operations[j][3], operations[j][4]))
    changes += [tuple(op) for i, op in enumerate(operations) if i not in paired]
    changes.sort(key=lambda op: (op[3], op[1]))
    result = []
    for tag, a, b, c, d in changes:
        old, new = passages(lp, a, b), passages(rp, c, d)
        uncertain = any(item['method'] == 'ocr' for item in old+new)
        result.append({'id': f'change-{len(result)+1}',
                       'type': {'insert': 'addition', 'delete': 'deletion', 'replace': 'replacement', 'move': 'move'}[tag],
                       'before': old, 'after': new,
                       'before_anchor': anchor(lp, a), 'after_anchor': anchor(rp, c),
                       'uncertainty': 'ocr_requires_visual_verification' if uncertain else None,
                       'legal_effect': None, 'legal_review_status': 'requires_contextual_host_review'})
    complete = bool(left and right) and before['coverage']['extraction_complete'] and after['coverage']['extraction_complete']
    structural_warnings = []
    old_tables, new_tables = before.get('tables', []), after.get('tables', [])
    if old_tables or new_tables:
        shape = lambda tables: [[len(row) for row in table['rows']] for table in tables]
        # A flat text match alone cannot establish unchanged table relationships.
        # Flag topology changes, and same-token text redistributed between cells.
        cell_tokens = lambda tables: [[[TOKEN.findall(cell) for cell in row] for row in table['rows']] for table in tables]
        if shape(old_tables) != shape(new_tables) or (left == right and cell_tokens(old_tables) != cell_tokens(new_tables)):
            complete = False
            structural_warnings.append('Table structure or cell boundaries differ, or cannot be aligned across formats. '
                                       'Inspect row/column relationships visually before concluding there are no changes.')
    return {'schema_version': 'kontaktlaw-comparison/1.0', 'before': before, 'after': after,
            'changes': result, 'coverage': {'complete': complete,
                'status': 'changes_found' if result else 'no_text_changes' if complete else 'inconclusive',
                'visual_verification_required': not complete, 'structural_warnings': structural_warnings},
            'comparison_scope': 'Text content; formatting, signatures and visual layout are not certified. '
                                'Whitespace and line wrapping are ignored only for matching.'}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before')
    parser.add_argument('after')
    parser.add_argument('--out', required=True)
    parser.add_argument('--ocr', choices=['auto', 'always', 'never'], default='auto')
    parser.add_argument('--ocr-languages', default='aze+eng+rus')
    parser.add_argument('--tesseract', help='Path to a local Tesseract executable')
    parser.add_argument('--tessdata', help='Local language-pack directory')
    parser.add_argument('--before-revision', choices=['original', 'revised'])
    parser.add_argument('--after-revision', choices=['original', 'revised'])
    args = parser.parse_args(argv)
    output = Path(args.out).resolve()
    review_dir = output.with_name(output.stem+'.review')
    try:
        if output in {Path(args.before).resolve(), Path(args.after).resolve()} or output.exists() or review_dir.exists():
            raise ComparisonError('Choose a new output filename; inputs and existing results are never overwritten.')
        ocr = OCR(args.ocr, args.ocr_languages, args.tesseract, args.tessdata, review_dir)
        before = extract(args.before, ocr, args.before_revision)
        after = extract(args.after, ocr, args.after_revision)
        result = compare(before, after)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
            file.write('\n')
        print(f'{len(result["changes"])} text changes; status={result["coverage"]["status"]}; '
              f'coverage_complete={result["coverage"]["complete"]}. Result: {output}')
        return 0
    except (ComparisonError, OSError, ValueError) as exc:
        print(f'Comparison not completed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
