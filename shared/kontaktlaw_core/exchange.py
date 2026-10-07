"""Versioned evidence exchange and fail-closed edit validation."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import re

VERSION = "1.0"
TASKS = {"review", "research", "grammar", "draft", "compare", "obligations", "summary", "reply"}
KINDS = {"legal", "commercial", "conditional"}

def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def document_hash(spans):
    # Identical framing in Python and TypeScript, including empty spans.
    return digest("\n".join(s["text"] for s in spans))

def envelope(spans, name, task="review", language="az", **metadata):
    sha = document_hash(spans)
    return {"schema_version": VERSION, "task": task, "language": language,
            "selected_party": None, "document": {"id": sha, "name": name,
            "sha256": sha, "spans": spans, **metadata},
            "coverage": {"extraction_complete": True, "reviewed_span_ids": [],
                         "missing_annexes": [], "warnings": []},
            "findings": [], "evidence": [], "edits": [], "obligations": []}

def protected_tokens(text):
    """Conservative lexical gate, not a semantic equivalence proof."""
    pattern = r'\d+(?:[.,:/%-]\d+)*|[A-ZƏÖÜÇŞĞİА-ЯЁ][\w-]*|\b(?:not|no|never|shall|must|may|unless|required|pay|не|нет|обязан|вправе|должен|deyil|olmaz|borcludur|bilər|etməlidir)\b|["“][^"”]+["”]'
    return Counter(re.findall(pattern, text, re.UNICODE))

def _validate(data, original=None, grammar_policy="conservative"):
    errors = []
    if not isinstance(data, dict): return ["Exchange must be an object"]
    if data.get("schema_version") != VERSION: errors.append("Unsupported schema_version")
    if data.get("task") not in TASKS: errors.append("Unknown task")
    if data.get("language") not in {"az", "en", "ru"}: errors.append("Unsupported language")
    if 'selected_party' not in data or (data['selected_party'] is not None and not isinstance(data['selected_party'],str)):errors.append('Invalid selected_party')
    for field in ('summary','reply'):
        if field in data and not isinstance(data[field],str):errors.append(f'{field} must be plain text')
    doc = data.get("document", {})
    spans = doc.get("spans", []) if isinstance(doc, dict) else []
    if not isinstance(spans, list) or not spans: return errors + ["Document spans required"]
    if any(not isinstance(s, dict) or not isinstance(s.get("text"), str) or not isinstance(s.get("id"), str) for s in spans):
        return errors + ["Invalid span"]
    by_id = {s["id"]: s for s in spans}
    if len(by_id) != len(spans): errors.append("Duplicate span IDs")
    if doc.get("sha256") != document_hash(spans): errors.append("Document hash mismatch")
    if not isinstance(doc.get("id"), str) or not doc["id"]: errors.append("Document identity required")
    if not isinstance(doc.get('name'),str):errors.append('Document name required')
    if original:
        old = original.get("document", {})
        if any(doc.get(k) != old.get(k) for k in ("id", "sha256")) or spans != old.get("spans"):
            errors.append("Stale or different document")
        for key in ('file_sha256','ooxml_sha256','host','scope','item_id','attachment_ids','comments'):
            if doc.get(key) != old.get(key): errors.append(f"Document metadata changed: {key}")
    for field in ("findings", "evidence", "edits", "obligations"):
        if not isinstance(data.get(field), list): errors.append(f"{field} must be an array")
    if errors: return errors
    coverage = data.get("coverage", {})
    if not isinstance(coverage, dict): return ["Invalid coverage"]
    if type(coverage.get('extraction_complete')) is not bool:errors.append('extraction_complete must be boolean')
    reviewed = coverage.get("reviewed_span_ids", [])
    if not isinstance(reviewed, list) or any(not isinstance(s,str) or s not in by_id for s in reviewed): return errors + ["Invalid reviewed span IDs"]
    if not isinstance(coverage.get('warnings'),list) or not isinstance(coverage.get('missing_annexes'),list):return errors + ['Coverage warnings and missing_annexes must be arrays']
    if coverage.get("review_complete") and (not coverage.get("extraction_complete") or
            set(reviewed) != set(by_id) or coverage.get("missing_annexes") or coverage.get("warnings")):
        errors.append("Complete-review claim contradicts coverage")
    evidence = {}
    for item in data["evidence"]:
        if not isinstance(item, dict): errors.append("Invalid evidence record"); continue
        eid = item.get("id")
        if not isinstance(eid, str) or eid in evidence: errors.append("Missing or duplicate evidence ID"); continue
        evidence[eid] = item
        quote, source = item.get("quote"), item.get("source_text")
        if not isinstance(quote, str) or not quote or not isinstance(source, str) or quote not in source:
            errors.append(f"Evidence {eid}: quotation not in inspected source text")
        if not item.get("title") or not item.get("locator"): errors.append(f"Evidence {eid}: missing title/locator")
        if item.get("source_sha256") != digest(source or ""): errors.append(f"Evidence {eid}: source hash mismatch")
        if item.get("status") not in {"snapshot", "official_inspected", "unverified"}: errors.append(f"Evidence {eid}: invalid status")
        if item.get('status') == 'snapshot':
            from .knowledge import metadata, LAW_DIR
            source=next((s for s in metadata() if s['file']==item.get('file')),None)
            start,end=item.get('start'),item.get('end')
            if not source or type(start) is not int or type(end) is not int or start<1 or end<start:
                errors.append(f'Evidence {eid}: bundled filename and exact line range required')
            else:
                lines=(LAW_DIR/source['file']).read_text(encoding='utf-8').splitlines()
                if end>len(lines) or '\n'.join(lines[start-1:end]) != item.get('source_text'):
                    errors.append(f'Evidence {eid}: source passage differs from bundled file')
                if source['title']!=item.get('title') or source['official_url']!=item.get('url'):
                    errors.append(f'Evidence {eid}: authority differs from catalog')
        # Automatic output must never purport to certify legal currency.
        if item.get("current_law_verified") is True: errors.append(f"Evidence {eid}: current-law certification requires human review")
        if item.get("status") == "official_inspected" and (not re.match(r"^https://(?:[\w-]+\.)?e-qanun\.az/", item.get("url", "")) or not item.get("retrieved_at")):
            errors.append(f"Evidence {eid}: official URL and retrieval time required")
    findings = set()
    for f in data["findings"]:
        if not isinstance(f, dict): errors.append("Invalid finding"); continue
        fid = f.get("id")
        if not isinstance(fid, str) or fid in findings: errors.append("Missing or duplicate finding ID")
        else: findings.add(fid)
        span = by_id.get(f.get("span_id"))
        quote = f.get("quote")
        if not span or not isinstance(quote, str) or not quote or quote not in span["text"]: errors.append(f"Finding {fid}: quote/locator mismatch")
        if f.get("kind") not in KINDS: errors.append(f"Finding {fid}: invalid classification")
        if not f.get("affected_party"): errors.append(f"Finding {fid}: affected party required")
        refs = f.get("evidence_ids", [])
        if not isinstance(refs, list) or any(not isinstance(r,str) or r not in evidence for r in refs):
            errors.append(f"Finding {fid}: unresolved evidence");continue
        if f.get("kind") == "legal" and (not refs or any(evidence.get(r, {}).get("status") == "unverified" for r in refs)):
            errors.append(f"Finding {fid}: legal claim needs inspected evidence")
    intervals, ids = {}, set()
    for e in data["edits"]:
        if not isinstance(e, dict): errors.append("Invalid edit"); continue
        eid = e.get("id")
        if not isinstance(eid, str) or eid in ids: errors.append("Missing or duplicate edit ID")
        else: ids.add(eid)
        span = by_id.get(e.get("span_id"))
        start, end, quote = e.get("start"), e.get("end"), e.get("quote")
        # Offsets are Unicode code points, not UTF-16 code units.
        if (not span or type(start) is not int or type(end) is not int or start < 0 or end <= start or
                end > len(span["text"]) or span["text"][start:end] != quote):
            errors.append(f"Edit {eid}: exact target mismatch"); continue
        if span.get("variant", "current") != "current": errors.append(f"Edit {eid}: unresolved revision")
        if not isinstance(e.get("replacement"), str) or e["replacement"] == quote: errors.append(f"Edit {eid}: missing/unchanged replacement")
        if e.get("mode") not in {"grammar", "legal"}: errors.append(f"Edit {eid}: invalid mode")
        if grammar_policy != "all" and e.get("mode") == "grammar" and protected_tokens(quote) != protected_tokens(e.get("replacement", "")):
            errors.append(f"Edit {eid}: protected terms changed")
        for a, b in intervals.setdefault(e["span_id"], []):
            if start < b and end > a: errors.append(f"Edit {eid}: overlapping target")
        intervals[e["span_id"]].append((start, end))
    for obligation in data["obligations"]:
        if not isinstance(obligation, dict): errors.append("Invalid obligation"); continue
        if not all(k in obligation for k in ('responsible_party','trigger','deadline','description')):errors.append('Obligation fields missing; use null for unknown trigger/deadline')
        span = by_id.get(obligation.get("span_id"))
        if not span or not obligation.get("quote") or obligation["quote"] not in span["text"]: errors.append("Obligation quote mismatch")
        if obligation.get("calculated_date") and not all(obligation.get(k) for k in ("trigger_date", "calendar", "calculation_explanation")):
            errors.append("Calculated deadline lacks trigger/calendar evidence")
    return errors

def validate(data, original=None, grammar_policy="conservative"):
    try: return _validate(data, original, grammar_policy)
    except (TypeError, KeyError, AttributeError, ValueError) as error:
        return [f'Malformed exchange: {error}']

def require_valid(data, original=None, grammar_policy="conservative"):
    errors = validate(data, original, grammar_policy)
    if errors: raise ValueError("; ".join(errors))
    return data

def load(path):
    with open(path, encoding="utf-8-sig") as f: return json.load(f)

def save(path, value):
    from pathlib import Path
    path = Path(path)
    if path.exists(): raise ValueError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
