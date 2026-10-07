"""Website 2.0 presentation adapter. Evidence exchange stays immutable."""
from copy import deepcopy
from datetime import datetime, timezone
from .exchange import require_valid, digest, validate

SCHEMA_VERSION = 'website-2.0'
PLUGIN_VERSION = '2.0.0-preview.2'

def utf16_length(text):
    return len(text.encode('utf-16-le')) // 2

def export_review(data, model, reasoning, prompt_fingerprint, original=None):
    # Validate identity, coverage and evidence independently of display candidates.
    checked = deepcopy(data)
    checked['findings'] = []; checked['edits'] = []
    require_valid(checked, original)
    spans = data['document']['spans']
    text = '\n'.join(span['text'] for span in spans)
    offsets = {}; cursor = 0
    for span in spans:
        offsets[span['id']] = cursor
        cursor += len(span['text']) + 1
    by_id = {span['id']: span for span in spans}
    findings = []; rejected = []; intervals = []; seen = set()
    def reject(item, reason):
        rejected.append({'id': str(item.get('id', 'unknown')), 'quote': item.get('quote', ''), 'issue': item.get('title', item.get('explanation', 'Tapıntı')), 'reason': reason})
    for item in data['findings']:
        if not isinstance(item.get('id'), str) or item['id'] in seen:
            reject(item, 'Missing or duplicate finding ID'); continue
        seen.add(item['id'])
        span = by_id.get(item.get('span_id')); quote = item.get('quote', '')
        if not span or not quote or span['text'].count(quote) != 1:
            reject(item, 'Dəqiq mənbə birmənalı tapılmadı.'); continue
        party = item.get('affected_party')
        if not party or party in ('party-general', 'Ümumi', 'general') or (data.get('selected_party') not in (None, 'party-general', 'Ümumi', 'general', party)):
            reject(item, 'Seçilmiş tərəfə aidiyyət təsdiqlənmədi.'); continue
        if item.get('duplicate_of'):
            reject(item, 'Təkrar tapıntı: '+item['duplicate_of']); continue
        individual = deepcopy(checked); individual['findings'] = [item]
        errors = validate(individual, original)
        if errors:
            reject(item, '; '.join(errors)); continue
        start = offsets[span['id']] + span['text'].index(quote)
        severity = item.get('severity', 'medium')
        findings.append({'id': item['id'], 'quote': quote, 'issue': item.get('title', 'Risk'),
            'riskLevel': severity if severity in ('low','medium','high','critical') else 'medium',
            'status': 'unclear' if item.get('kind') == 'conditional' else 'legal_risk', 'riskType': 'contract_risk', 'confidence': item.get('confidence', .6),
            'analysis': item.get('explanation', ''), 'affected_party_id': party,
            'why_risky_for_selected_party': item.get('explanation', ''),
            'legalBasis': ' '.join(e['title'] + ': ' + e['quote'] for e in data['evidence'] if e['id'] in item.get('evidence_ids', [])) or 'Hüquqi əsas tapılmadı', 'referenceIndexes': [],
            'recommendation': item.get('recommendation', item.get('proposal', '')),
            'suggested_clause': item.get('proposal', ''), 'detection_source': 'ai',
            'remediation_mode': 'review_draft' if item.get('proposal') else 'recommendation_only',
            'source_span': {'start': utf16_length(text[:start]), 'end': utf16_length(text[:start+len(quote)]), 'text': quote}})
    for edit in data['edits']:
        if edit.get('mode') != 'grammar': continue
        if not isinstance(edit.get('id'), str) or edit['id'] in seen:
            reject(edit, 'Missing or duplicate edit ID'); continue
        seen.add(edit['id'])
        span = by_id.get(edit.get('span_id')); start = edit.get('start'); end = edit.get('end')
        if not span or span.get('variant', 'current') != 'current' or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(span['text']) or span['text'][start:end] != edit.get('quote') or not isinstance(edit.get('replacement'), str):
            reject(edit, 'Qrammatik düzəlişin mənbəsi təsdiqlənmədi.'); continue
        a = offsets[span['id']] + start; b = offsets[span['id']] + end
        if any(a < y and b > x for x,y in intervals):
            reject(edit, 'Üst-üstə düşən düzəlişlər birləşdirilməlidir.'); continue
        intervals.append((a,b))
        findings.append({'id': edit['id'], 'quote': edit['quote'], 'issue': edit.get('explanation', 'Qrammatik düzəliş'),
            'riskLevel': 'low', 'status': 'legal_risk', 'riskType': 'technical_inconsistency', 'confidence': .6,
            'legalBasis': '', 'referenceIndexes': [], 'recommendation': 'Avtomatik tətbiq edilir.',
            'suggested_clause': edit['replacement'], 'replacement': edit['replacement'], 'detection_source': 'grammar', 'remediation_mode': 'auto_apply',
            'source_span': {'start': utf16_length(text[:a]), 'end': utf16_length(text[:b]), 'text': edit['quote']}})
    if len(prompt_fingerprint) != 64 or any(c not in '0123456789abcdef' for c in prompt_fingerprint):
        raise ValueError('Supply the SHA-256 of the actual effective instructions')
    return {'query': data['task'], 'documentName': data['document']['name'], 'answer': data.get('summary',''),
        'model': model, 'generatedAt': datetime.now(timezone.utc).isoformat(), 'references': [],
        'documentReview': {'documentName': data['document']['name'], 'documentText': text,
            'sourceDocumentText': text, 'findings': findings, 'rejectedFindings': rejected,
            'humanReview': [{'issue': item['issue'], 'reason': item['reason']} for item in rejected] +
                [{'issue': 'Əhatə məhdudiyyəti', 'reason': warning} for warning in data['coverage'].get('warnings',[])],
            'provenance': {'pluginVersion': PLUGIN_VERSION, 'schemaVersion': SCHEMA_VERSION, 'model': model,
                'reasoning': reasoning, 'documentHash': digest(text), 'promptFingerprint': prompt_fingerprint}}}
