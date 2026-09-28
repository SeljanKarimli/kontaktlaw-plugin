#!/usr/bin/env python3
"""Local review state, validated text edits and a read-only clause viewer.

The host model supplies grammar decisions, parties and legal findings. This helper
never calls a model, decides legal risk, or modifies the supplied document.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

from compare_documents import ComparisonError, OCR, extract

PLUGIN = Path(__file__).resolve().parents[3]
ASSETS = Path(__file__).resolve().parents[1] / 'assets' / 'viewer'
SCHEMA = 1
LABELS = ['Problemli bənd', 'Problemli mətn', 'Riskin izahı', 'Hüquqi əsas',
          'Qısa düzəliş təklifi', 'Risk səviyyəsi']


class ReviewError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.review-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def output_dir(path):
    path = Path(path).resolve()
    if path == PLUGIN or PLUGIN in path.parents:
        raise ReviewError('Review output must be outside the plugin package.')
    return path


def load(directory):
    state = read_json(output_dir(directory) / 'review.json')
    if state.get('schema_version') != SCHEMA:
        raise ReviewError('Unsupported review schema. Prepare a new review directory.')
    return state


def save(directory, state):
    atomic_json(output_dir(directory) / 'review.json', state)


def prepare(source, directory, mode='auto', languages='aze+eng+rus', executable=None,
            tessdata=None, revision=None):
    directory = output_dir(directory)
    source = Path(source).resolve()
    if directory == source or directory in source.parents:
        raise ReviewError('Keep source documents outside the review output directory.')
    identity = {'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'ocr': mode, 'languages': languages, 'revision': revision}
    if (directory / 'review.json').exists():
        existing = load(directory)
        if existing['input'] != identity:
            raise ReviewError('This directory belongs to a different input/version. Choose a new directory.')
        return existing
    document = extract(source, OCR(mode, languages, executable, tessdata,
                                  directory / 'ocr-evidence'), revision)
    if document['sha256'] != identity['sha256']:
        raise ReviewError('Source changed during preparation; retry with a stable copy.')
    # Keep the extractor's table/cell locators and paragraph IDs across both versions.
    state = {'schema_version': SCHEMA, 'input': identity, 'name': document['name'],
             'document_id': identity['sha256'], 'original_version': digest(identity),
             'coverage': document['coverage'], 'comments': document.get('comments', []),
             'tables': document.get('tables', []), 'original': document['spans'],
             'corrected': copy.deepcopy(document['spans']), 'corrections': [],
             'parties': [], 'selected_party': None, 'findings': [],
             'verified_ocr': [], 'stage': 'extracted'}
    state['document_version'] = digest(state['corrected'])
    save(directory, state)
    return state


def require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f'{label} must be nonempty text.')
    return value


def occurrence_range(text, quote, occurrence):
    require_text(quote, 'Quotation')
    if type(occurrence) is not int or occurrence < 1:
        raise ReviewError('An explicit positive quotation occurrence is required.')
    start = -1
    for _ in range(occurrence):
        start = text.find(quote, start + 1)
        if start < 0:
            raise ReviewError('Quotation does not match the specified occurrence.')
    return start, start + len(quote)


def check_grammar(before, after, protected):
    if not isinstance(after, str) or not after.strip() or before == after:
        raise ReviewError('Replacement must be different, nonempty text.')
    # Deterministic guards supplement, rather than replace, the host's semantic review.
    numbers = r'\d+(?:[.,:/-]\d+)*'
    if re.findall(numbers, before) != re.findall(numbers, after):
        raise ReviewError('Grammar corrections cannot change numbers or dates.')
    for term in protected:
        if before.count(term) != after.count(term):
            raise ReviewError('Grammar correction changes a protected term.')
    negations = r'\b(?:not|no|never|shall|must|may|deyil|deyildir|olmaz|не|нет|нельзя)\b'
    if re.findall(negations, before, re.I) != re.findall(negations, after, re.I):
        raise ReviewError('Grammar correction changes a protected obligation or negation.')


def apply_grammar(state, packet):
    fingerprint = digest(packet)
    if state.get('grammar_packet') == fingerprint:
        return state
    if state['stage'] != 'extracted':
        raise ReviewError('Grammar was already finalized. Use a new review directory to revise it.')
    if not state['original']:
        raise ReviewError('No readable text is available. Obtain a readable source before review.')
    if packet.get('original_version') != state['original_version']:
        raise ReviewError('Grammar packet targets a different original version.')
    if packet.get('reviewed_complete_document') is not True:
        raise ReviewError('Read the complete available document before finalizing grammar.')
    protected = packet.get('protected_terms')
    if not isinstance(protected, list) or not all(isinstance(t, str) and t for t in protected):
        raise ReviewError('Supply protected_terms: names, defined terms, currencies and duty/negation phrases.')
    spans = {s['id']: s for s in state['original']}
    verified = packet.get('verified_ocr', [])
    for entry in verified:
        span = spans.get(entry.get('span_id'))
        if not span or span['method'] != 'ocr' or entry.get('quote') != span['text'] or entry.get('visually_verified') is not True:
            raise ReviewError('OCR verification requires the exact full span and visual verification.')
    verified_ids = {entry['span_id'] for entry in verified}
    parties = packet.get('parties', [])
    seen = {'general'}
    for party in parties:
        pid = require_text(party.get('id'), 'Party ID')
        if pid in seen:
            raise ReviewError('Party IDs must be unique; general is reserved.')
        seen.add(pid)
        require_text(party.get('name'), 'Party name')
        require_text(party.get('role'), 'Party role')
        span = spans.get(party.get('span_id'))
        if not span or (span['method'] == 'ocr' and span['id'] not in verified_ids):
            raise ReviewError('Party evidence must reference a verified document span.')
        occurrence_range(span['text'], party.get('quote'), party.get('occurrence'))
    changes = []
    for change in packet.get('corrections', []):
        span = spans.get(change.get('span_id'))
        if not span or (span['method'] == 'ocr' and span['id'] not in verified_ids):
            raise ReviewError('Cannot correct unknown or unverified OCR text.')
        start, end = occurrence_range(span['text'], change.get('quote'), change.get('occurrence'))
        if change.get('meaning_preserved') is not True or change.get('verified') is not True:
            raise ReviewError('Every correction requires semantic and exact-context verification.')
        require_text(change.get('reason'), 'Grammar explanation')
        check_grammar(change['quote'], change.get('replacement'), protected)
        changes.append({**change, 'start': start, 'end': end})
    result = copy.deepcopy(state)
    for span in result['corrected']:
        edits = sorted([c for c in changes if c['span_id'] == span['id']], key=lambda c: c['start'])
        cursor, delta, pieces = 0, 0, []
        for change in edits:
            if change['start'] < cursor:
                raise ReviewError('Grammar corrections overlap.')
            pieces.extend([span['text'][cursor:change['start']], change['replacement']])
            change['corrected_start'] = change['start'] + delta
            change['corrected_end'] = change['corrected_start'] + len(change['replacement'])
            delta += len(change['replacement']) - (change['end'] - change['start'])
            cursor = change['end']
        pieces.append(span['text'][cursor:])
        span['text'] = ''.join(pieces)
    result.update(corrections=changes, parties=parties, verified_ocr=sorted(verified_ids),
                  stage='grammar_complete', grammar_packet=fingerprint)
    result['document_version'] = digest(result['corrected'])
    return result


def select_party(state, party_id):
    if state['stage'] == 'extracted':
        raise ReviewError('Complete grammar before selecting a review perspective.')
    if party_id != 'general' and party_id not in {p['id'] for p in state['parties']}:
        raise ReviewError('Select an identified party ID or general.')
    if state['selected_party'] == party_id:
        return state
    result = copy.deepcopy(state)
    result.update(selected_party=party_id, findings=[], stage='party_selected')
    result.pop('findings_packet', None)
    return result


def original_range(state, span_id, start, end):
    edits = sorted([c for c in state['corrections'] if c['span_id'] == span_id],
                   key=lambda c: c['corrected_start'])

    def boundary(position, is_end):
        delta = 0
        for edit in edits:
            left, right = edit['corrected_start'], edit['corrected_end']
            if position <= left:
                return position - delta
            if position < right:
                return edit['end'] if is_end else edit['start']
            delta += (right - left) - (edit['end'] - edit['start'])
        return position - delta

    return boundary(start, False), boundary(end, True)


def finalize_findings(state, packet):
    if state['stage'] not in {'party_selected', 'complete'} or not state['selected_party']:
        raise ReviewError('Select the review perspective before adding risks.')
    if packet.get('document_version') != state['document_version'] or packet.get('selected_party') != state['selected_party']:
        raise ReviewError('Risk packet targets a different document version or perspective.')
    if packet.get('reviewed_complete_document') is not True:
        raise ReviewError('Review the complete available document and cross-references first.')
    if not isinstance(packet.get('findings'), list):
        raise ReviewError('findings must be a list, including [] when no material risks were found.')
    result = copy.deepcopy(state)
    original = {s['id']: s for s in state['original']}
    corrected = {s['id']: s for s in state['corrected']}
    findings = []
    for index, item in enumerate(packet['findings'], 1):
        require_text(item.get('title'), 'Risk title')
        paragraphs = item.get('paragraphs', {})
        if set(paragraphs) != set(LABELS):
            raise ReviewError('Each risk must contain exactly the six canonical labeled paragraphs.')
        for label in LABELS:
            require_text(paragraphs[label], label)
        finding = {**item, 'id': f'risk-{index}', 'anchors': [], 'link_error': None}
        try:
            requested = item.get('anchors')
            if not isinstance(requested, list) or not requested:
                raise ReviewError('No exact passage anchor was supplied.')
            for anchor in requested:
                if anchor.get('document_version') != state['document_version']:
                    raise ReviewError('Anchor document version is stale.')
                sid = anchor.get('span_id')
                span = corrected.get(sid)
                if not span:
                    raise ReviewError('The paragraph is unavailable.')
                if span['method'] == 'ocr' and sid not in state['verified_ocr']:
                    raise ReviewError('OCR quotation has not been visually verified.')
                start, end = occurrence_range(span['text'], anchor.get('quote'), anchor.get('occurrence'))
                if anchor['quote'] not in paragraphs['Problemli mətn']:
                    raise ReviewError('The anchor quotation is absent from Problemli mətn.')
                old_start, old_end = original_range(state, sid, start, end)
                finding['anchors'].append({'span_id': sid, 'locator': span['locator'],
                    'occurrence': anchor['occurrence'], 'document_version': state['document_version'],
                    'original': {'start': old_start, 'end': old_end,
                                 'quote': original[sid]['text'][old_start:old_end]},
                    'corrected': {'start': start, 'end': end, 'quote': anchor['quote']}})
        except ReviewError as exc:
            finding['anchors'] = []
            finding['link_error'] = str(exc)
        findings.append(finding)
    result.update(findings=findings, stage='complete', findings_packet=digest(packet))
    return result


def public_state(state):
    # Do not send local paths, OCR file paths or host-only verification packets to the browser.
    keys = ['schema_version', 'name', 'document_id', 'document_version', 'stage', 'parties',
            'selected_party', 'findings', 'corrections', 'verified_ocr']
    data = {key: state[key] for key in keys}
    data['coverage'] = {'extraction_complete': state['coverage']['extraction_complete'],
                        'warnings': state['coverage'].get('warnings', [])}
    data['tables'] = [{'locator': t['locator'], 'row_sizes': [len(row) for row in t['rows']]}
                      for t in state.get('tables', [])]
    for version in ('original', 'corrected'):
        data[version] = [{k: s[k] for k in ('id', 'text', 'locator', 'method')}
                         for s in state[version]]
    return data


def corrected_download(state):
    return ('\n\n'.join(s['text'] for s in state['corrected']) + '\n').encode('utf-8-sig')


def make_server(directory, token=None, port=0):
    directory = output_dir(directory)
    load(directory)
    token = token or secrets.token_urlsafe(32)
    prefix = '/' + token + '/'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Never log private text, capability URLs or filenames.

        def do_GET(self):
            self.server.last_access = time.monotonic()
            host = f'127.0.0.1:{self.server.server_port}'
            route = urlsplit(self.path).path
            if self.headers.get('Host') != host or not route.startswith(prefix):
                self.send_error(404)
                return
            resource = route[len(prefix):]
            try:
                attachment = False
                if resource in ('', 'index.html', 'viewer.js', 'viewer.css'):
                    filename = resource or 'index.html'
                    content = (ASSETS / filename).read_bytes()
                    mime = {'index.html': 'text/html', 'viewer.js': 'text/javascript',
                            'viewer.css': 'text/css'}[filename]
                elif resource == 'review.json':
                    content = json.dumps(public_state(load(directory)), ensure_ascii=False).encode()
                    mime = 'application/json'
                elif resource == 'corrected.txt':
                    content = corrected_download(load(directory))
                    mime, attachment = 'text/plain', True
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', mime + '; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
                if attachment:
                    self.send_header('Content-Disposition', 'attachment; filename="kontaktlaw-corrected.txt"')
                self.end_headers()
                self.wfile.write(content)
            except (OSError, ValueError, KeyError):
                self.send_error(503, 'Review unavailable; reload after preparation finishes.')

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.last_access = time.monotonic()
    server.review_url = f'http://127.0.0.1:{server.server_port}{prefix}'
    return server


def running_service(directory):
    try:
        service = read_json(Path(directory) / 'service.json')
        url = urlsplit(service['url'])
        if url.scheme != 'http' or url.hostname != '127.0.0.1' or not re.fullmatch(r'/[A-Za-z0-9_-]+/', url.path):
            return None
        with urlopen(service['url'] + 'review.json', timeout=1) as response:
            if json.load(response)['document_id'] == load(directory)['document_id']:
                return service
    except (OSError, ValueError, KeyError):
        return None
    return None


def serve(directory, background=False):
    directory = output_dir(directory)
    load(directory)
    current = running_service(directory)
    if current:
        print(json.dumps(current))
        return
    if background:
        with (directory / 'service.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'serve',
                                        '--out', str(directory)], stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                                       start_new_session=os.name != 'nt')
        for _ in range(60):
            current = running_service(directory)
            if current:
                print(json.dumps(current))
                return
            if process.poll() is not None:
                break
            time.sleep(.1)
        raise ReviewError('Viewer failed to start. Inspect service.log in the review directory.')
    server = make_server(directory)
    service = {'url': server.review_url, 'pid': os.getpid()}
    atomic_json(directory / 'service.json', service)
    print(json.dumps(service), flush=True)

    def idle_shutdown():
        while time.monotonic() - server.last_access < 7200:
            time.sleep(30)
        server.shutdown()

    threading.Thread(target=idle_shutdown, daemon=True).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('source')
    p.add_argument('--ocr', choices=['auto', 'always', 'never'], default='auto')
    p.add_argument('--ocr-languages', default='aze+eng+rus')
    p.add_argument('--tesseract')
    p.add_argument('--tessdata')
    p.add_argument('--revision', choices=['original', 'revised'])
    grammar = sub.add_parser('grammar')
    grammar.add_argument('--packet', required=True)
    select = sub.add_parser('select')
    select.add_argument('--party', required=True)
    findings = sub.add_parser('findings')
    findings.add_argument('--packet', required=True)
    sub.add_parser('status')
    server = sub.add_parser('serve')
    server.add_argument('--background', action='store_true')
    for command in (p, grammar, select, findings, sub.choices['status'], server):
        command.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'serve':
            serve(args.out, args.background)
            return 0
        if args.command == 'prepare':
            state = prepare(args.source, args.out, args.ocr, args.ocr_languages,
                            args.tesseract, args.tessdata, args.revision)
        else:
            state = load(args.out)
            if args.command == 'grammar':
                state = apply_grammar(state, read_json(args.packet))
            elif args.command == 'select':
                state = select_party(state, args.party)
            elif args.command == 'findings':
                state = finalize_findings(state, read_json(args.packet))
            if args.command != 'status':
                save(args.out, state)
        print(json.dumps({k: state[k] for k in ('stage', 'original_version', 'document_version', 'selected_party')}, ensure_ascii=False))
        return 0
    except (ReviewError, ComparisonError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Review not completed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
