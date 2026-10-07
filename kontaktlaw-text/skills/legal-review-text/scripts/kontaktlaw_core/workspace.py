"""Explicit personal library and human-reviewed source staging."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import re
import shutil
from .exchange import load, save, digest

def library_fingerprint(record):
    import json
    return digest(json.dumps({k:record[k] for k in ('id','jurisdiction','contract_type','party_position','preferred_wording','fallback_wording')},ensure_ascii=False,sort_keys=True))

def library_add(workspace, record):
    root = Path(workspace).resolve()
    name = record.get('id', '')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', name): raise ValueError('Use a lowercase library ID with letters, numbers, hyphens or underscores.')
    for field in ('jurisdiction', 'contract_type', 'party_position', 'preferred_wording', 'fallback_wording'):
        if not isinstance(record.get(field), str) or not record[field]: raise ValueError(f'Missing {field}')
    record = {**record, 'approved': False, 'approval_date': None, 'approved_content_sha256': None}
    save(root/'library'/f'{name}.json', record)
    return record

def approve(workspace, record_id, approver):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', record_id): raise ValueError('Invalid library ID')
    if not approver.strip(): raise ValueError('Approver name required')
    path = Path(workspace).resolve()/'library'/f'{record_id}.json'
    record = load(path)
    # An explicit CLI command records a human decision, never a model quality claim.
    record.update(approved=True, approved_by=approver, approval_date=datetime.now(timezone.utc).isoformat(),
                  approved_content_sha256=library_fingerprint(record))
    import json
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return record

def draft(workspace, record_id, values):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', record_id): raise ValueError('Invalid library ID')
    record = load(Path(workspace).resolve()/'library'/f'{record_id}.json')
    if not record.get('approved') or record.get('approved_content_sha256') != library_fingerprint(record):
        raise ValueError('Template is unapproved or changed after approval.')
    missing = []
    def replacement(match):
        key = match.group(1)
        if key not in values or values[key] in (None, ''):
            missing.append(key); return f'[[MISSING: {key}]]'
        return str(values[key])
    text = re.sub(r'\{\{([\w.-]+)\}\}', replacement, record['preferred_wording'])
    return {'text': text, 'missing_terms': sorted(set(missing)), 'template_id': record_id, 'requires_legal_review': True}

def stage_source(knowledge_root, source_file, candidate_file, workspace, official_url, retrieved_at):
    """Stage an explicitly supplied official-source transcription; never silently promote."""
    root = Path(knowledge_root)
    sources = load(root/'sources.json')['sources']
    old = next((s for s in sources if s['file'] == source_file), None)
    if not old: raise ValueError('Unknown source; new sources require a separately reviewed catalog addition.')
    if official_url != old['official_url']: raise ValueError('Official URL must match the existing catalog.')
    datetime.fromisoformat(retrieved_at.replace('Z', '+00:00'))
    content = Path(candidate_file).read_text(encoding='utf-8-sig')
    previous = (root/'MDs'/source_file).read_text(encoding='utf-8')
    def headings(text):
        return set(re.findall(r'^#{2,6}\s+.*?(?:Maddə|MADDƏ)\s+(\d+(?:[.-]\d+)*)', re.sub(r'<[^>]+>', '', text), re.M))
    before, after = headings(previous), headings(content)
    if not after: raise ValueError('No parsable article headings; convert official source into reviewed Markdown first.')
    sha = digest(content)
    folder = Path(workspace).resolve()/'source-staging'/sha
    if folder.exists(): raise ValueError('This candidate is already staged.')
    folder.mkdir(parents=True)
    shutil.copy2(root/'MDs'/source_file, folder/'previous.md')
    (folder/'candidate.md').write_text(content, encoding='utf-8')
    record = {'source_file': source_file, 'official_url': official_url, 'retrieved_at': retrieved_at,
              'candidate_sha256': sha, 'previous_sha256': digest(previous),
              'removed_articles': sorted(before-after), 'added_articles': sorted(after-before),
              'effective_date_evidence': None, 'status': 'pending_human_source_review',
              'promoted': False}
    save(folder/'review.json', record)
    return {**record, 'staging_directory': str(folder)}
