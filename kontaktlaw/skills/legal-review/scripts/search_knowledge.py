#!/usr/bin/env python3
"""Read-only lexical retrieval from the bundled KontaktLaw legislation."""
from __future__ import annotations
import argparse
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
    return re.findall(r'\w+', normalize(value))

def metadata():
    return json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))['sources']

def has_body(lines, heading):
    body = '\n'.join(line for line in lines if line.strip() and not line.startswith(('#', '>'))).strip()
    return bool(body) and normalize(body) != normalize(heading)

def chunks(source):
    lines = (LAW_DIR / source['file']).read_text(encoding='utf-8').splitlines()
    heading, article, start, pending = source['title'], None, 1, []
    for number, line in enumerate(lines, 1):
        is_heading = re.match(r'^#{2,6}\s+', line)
        if (line.strip() == '---' or is_heading) and pending:
            if has_body(pending, heading):
                yield {'start':start, 'end':number-1, 'heading':heading, 'article':article, 'text':'\n'.join(pending)}
            pending = []
        if is_heading:
            heading = re.sub(r'^#+\s+', '', line)
            match = re.match(r'madde\s+(\d+(?:[.-]\d+)*)\b', normalize(heading))
            article = match.group(1) if match else None
        if line.strip() == '---':
            start = number + 1
            continue
        if not pending:
            start = number
        pending.append(line)
    if has_body(pending, heading):
        yield {'start':start, 'end':len(lines), 'heading':heading, 'article':article, 'text':'\n'.join(pending)}

def search(args):
    query = set(tokens(args.query))
    if not query and not args.article:
        raise ValueError('Provide a search phrase or --article.')
    corpus = []
    for source in metadata():
        if args.law and normalize(args.law) not in normalize(source['title'] + ' ' + source['file']):
            continue
        for chunk in chunks(source):
            if args.article and chunk['article'] != args.article:
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
                        'snapshot_date':source['snapshot_date'],**chunk,'score':round(score,5)})
    results.sort(key=lambda r: -r['score'])
    count = len(results)
    results = results[:args.limit]
    for result in results:
        result['truncated'] = len(result['text']) > 3500
        result['text'] = result['text'][:3500]
    return {'query':args.query,'matching_chunks':count,'returned':len(results),
            'verification':'Bundled snapshot only; not current-law verification. Read surrounding provisions.', 'results':results}

def read(args):
    source = next((s for s in metadata() if s['file'] == args.file), None)
    if source is None:
        raise ValueError('Choose an exact bundled filename from the catalog or search results.')
    if args.start < 1 or args.end < args.start or args.end-args.start >= 250:
        raise ValueError('Use 1-based lines and read at most 250 lines at a time.')
    lines = (LAW_DIR / source['file']).read_text(encoding='utf-8').splitlines()
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
