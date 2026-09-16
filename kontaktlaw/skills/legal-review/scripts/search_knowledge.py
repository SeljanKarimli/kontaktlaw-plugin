#!/usr/bin/env python3
"""Read-only lexical retrieval from the bundled KontaktLaw legislation."""
from __future__ import annotations
import argparse
import hashlib
import html
from collections import Counter
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1] / 'references' / 'knowledge'
LAW_DIR = ROOT / 'MDs'

def normalize(value):
    value = value.replace('İ', 'i').replace('I', 'ı').casefold()
    value = value.translate(str.maketrans('əıöüçşğ', 'eioucsg'))
    return ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))

def tokens(value):
    return re.findall(r'\w+', normalize(plain(value)))

def plain(value):
    """Index formatting, never mutate the literal evidence returned to callers."""
    return html.unescape(re.sub(r'<[^>]*>', '', value))

def article_number(value):
    value = value.strip().removesuffix('.')
    if not re.fullmatch(r'\d+(?:[.-]\d+)*', value):
        raise ValueError('Invalid article number; use e.g. 13, 13.2 or 13-1.')
    return value

def source_path(source):
    name = source['file']
    if '/' in name or '\\' in name or name in ('.', '..'):
        raise ValueError('Invalid corpus filename.')
    matches = [p for p in LAW_DIR.iterdir() if unicodedata.normalize('NFC', p.name) == unicodedata.normalize('NFC', name)]
    if len(matches) != 1 or matches[0].is_symlink() or matches[0].resolve().parent != LAW_DIR.resolve():
        raise ValueError('Corpus file missing, ambiguous or outside corpus: ' + name)
    return matches[0]

def source_lines(source):
    data = source_path(source).read_bytes()
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise ValueError('Corpus integrity mismatch: ' + source['file'] + '. Reinstall the pinned release; do not edit the hash to bypass verification.')
    return data.decode('utf-8').splitlines()

def metadata():
    return json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))['sources']

def chunks(source):
    """Contiguous article sections, including all heading text and footnotes.

    Non-article headings delimit context but never discard text. No length-based
    guess is made about whether a heading embeds a substantive legal provision.
    """
    lines = source_lines(source)
    heading, article, start = source['title'], None, 1
    section_kind = 'snapshot_provision'
    for number, line in enumerate(lines, 1):
        clean = plain(line).strip()
        is_heading = re.match(r'^#{1,6}\s+', clean)
        if is_heading:
            title = re.sub(r'^#+\s+', '', clean)
            # Numbered provisions are subordinate text, even if the export
            # promoted them to Markdown headings of a higher visual level.
            if article and re.match(r'^' + re.escape(article) + r'\s*[.-]\s*\d', title):
                continue
            if number > start:
                yield from _section(lines, start, number-1, heading, article, section_kind)
            folded = normalize(title)
            if 'menbe senedlerinin' in folded or ('deyisiklik' in folded and 'siyahisi' in folded):
                section_kind = 'source_history'
            heading = re.sub(r'^#+\s+', '', clean)
            match = re.match(r'madde\s+(\d+(?:[.-]\d+)*)\b', normalize(heading))
            article = match.group(1) if match else None
            start = number
    yield from _section(lines, start, len(lines), heading, article, section_kind)

def _section(lines, start, end, heading, article, section_kind):
    if any(line.strip() and line.strip() != '---' for line in lines[start-1:end]):
        yield {'start':start, 'end':end, 'heading':heading, 'article':article, 'section_kind':section_kind, 'text':'\n'.join(lines[start-1:end])}

def excerpt(chunk, query):
    """Bound output to 3500 characters and 250 lines; retain exact locations.

    A single overlong source line is a literal prefix; text_start_column and
    text_end_column make that partial-line boundary explicit.
    """
    lines = chunk['text'].split('\n')
    best = max(range(len(lines)), key=lambda i: len(query.intersection(tokens(lines[i])))) if query else 0
    begin = max(0, best - 1)
    if begin != best and len(lines[begin]) + 1 + min(len(lines[best]),3500) > 3500:
        begin = best
    selected, length = [], 0
    for line in lines[begin:begin+250]:
        needed = len(line) + bool(selected)
        if selected and length + needed > 3500:
            break
        selected.append(line[:3500] if not selected else line)
        length += len(selected[-1]) + (len(selected) > 1)
        if length >= 3500: break
    value = dict(chunk)
    value.update(section_start=chunk['start'], section_end=chunk['end'],
                 start=chunk['start']+begin, end=chunk['start']+begin+len(selected)-1,
                 text='\n'.join(selected), text_start_column=1,
                 text_end_column=len(selected[-1]) if selected else 0,
                 truncated=begin > 0 or len(selected) < len(lines) or (bool(selected) and selected[-1] != lines[begin+len(selected)-1]))
    return value

def search(args):
    article = article_number(args.article) if args.article is not None else None
    if not 1 <= args.limit <= 20:
        raise ValueError('Limit must be between 1 and 20.')
    query = set(tokens(args.query))
    if not query and not article:
        raise ValueError('Provide a search phrase or --article.')
    corpus = []
    for source in metadata():
        if args.law and normalize(args.law) not in normalize(source['title'] + ' ' + source['file']):
            continue
        for chunk in chunks(source):
            if article and chunk['article'] != article:
                continue
            terms = tokens(chunk['text'])
            counts = Counter(terms)
            corpus.append((source, chunk, counts, len(terms)))
    frequencies = Counter(t for _,_,counts,_ in corpus for t in query if t in counts)
    average = sum(length for *_,length in corpus) / max(1,len(corpus))
    results = []
    for source, chunk, counts, length in corpus:
        score = 0.0
        for term in query:
            tf = counts.get(term, 0)
            if tf:
                idf = math.log(1 + (len(corpus)-frequencies[term]+0.5)/(frequencies[term]+0.5))
                score += idf * (tf*2.2)/(tf+1.2*(0.25+0.75*length/max(1,average)))
        if query and score <= 0:
            continue
        results.append({'file':source['file'],'title':source['title'],'official_url':source['official_url'],
                        'snapshot_date':source['snapshot_date'],**excerpt(chunk, query),'score':round(score,5)})
    results.sort(key=lambda r: -r['score'])
    count = len(results)
    results = results[:args.limit]
    return {'query':args.query,'matching_chunks':count,'returned':len(results),
            'verification':'Bundled snapshot only; not current-law verification. Read surrounding provisions.', 'results':results}

def read(args):
    source = next((s for s in metadata() if unicodedata.normalize('NFC', s['file']) == unicodedata.normalize('NFC', args.file)), None)
    if source is None:
        raise ValueError('Choose an exact bundled filename from the catalog or search results.')
    if args.start < 1 or args.end < args.start or args.end-args.start >= 250:
        raise ValueError('Use 1-based lines and read at most 250 lines at a time.')
    lines = source_lines(source)
    if args.start > len(lines):
        raise ValueError('The start line is beyond the file.')
    return {**source,'total_lines':len(lines),'lines':[{'line':i+1,'text':lines[i]} for i in range(args.start-1,min(args.end,len(lines)))]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    lookup = commands.add_parser('search')
    lookup.add_argument('query',nargs='?',default='')
    lookup.add_argument('--law',default='')
    lookup.add_argument('--article')
    lookup.add_argument('--limit',type=int,default=6,choices=range(1,21),metavar='1..20')
    fetch = commands.add_parser('read')
    fetch.add_argument('--file',required=True)
    fetch.add_argument('--start',type=int,required=True)
    fetch.add_argument('--end',type=int,required=True)
    args = parser.parse_args()
    try:
        result = search(args) if args.command == 'search' else read(args)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error)+'\n')

if __name__ == '__main__':
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
