"""Build independent plugins from shared sources; --check detects package drift."""
from pathlib import Path
import argparse
import shutil
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
PAIRS=(('kontaktlaw','legal-review'),('kontaktlaw-text','legal-review-text'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    mismatches=[]
    for plugin,skill in PAIRS:
        target=ROOT/plugin/'skills'/skill
        skill_text=(ROOT/'shared/SKILL.template.md').read_text(encoding='utf-8').replace('__SKILL_NAME__',skill).replace('__DISPLAY_NAME__','KontaktLaw Text' if plugin=='kontaktlaw-text' else 'KontaktLaw')
        if plugin == 'kontaktlaw':
            skill_text=skill_text.replace('description: Review contracts', 'description: Use when a user submits or uploads a contract or legal document, including an attachment-only message. Review contracts')
            skill_text += '\n## Optional local Word viewer\n\nThe website JSON contract is the default. When the user explicitly requests the local Word viewer, read references/automatic-review.md for the legacy viewer adapter and its layout preflight. Its prose packets are only a viewer transport, never the default result. Keep the original and use the core apply-docx --all-grammar pipeline for automatic corrections; do not reinstate the legacy viewer grammar approval gates.\n'
            skill_text=skill_text.replace('Internal JSON records do not change the prose-only user output rule.', 'The website JSON contract controls presentation; evidence records remain internal.')
            start=skill_text.index('Begin with `Müqavilə')
            end=skill_text.index('\nBefore returning', start)
            skill_text=skill_text[:start]+'Return website-compatible JSON by default. Read [the website contract](references/website-contract.md) and use its versioned schema. Retain the evidence exchange internally. No six-paragraph prose wrapper is required for KontaktLaw.\n'+skill_text[end:]
            skill_text=skill_text.replace('Read [the prompt guide](references/prompt-guide.md)', 'Read [the website contract](references/website-contract.md), then [the prompt guide](references/prompt-guide.md)')
        skill_path=target/'SKILL.md'
        if args.check:
            if skill_path.read_text(encoding='utf-8')!=skill_text:mismatches.append(str(skill_path.relative_to(ROOT)))
        else:skill_path.write_text(skill_text,encoding='utf-8',newline='\n')
        files=[(ROOT/'requirements-document.txt',target/'scripts/requirements-document.txt')]
        for source in (ROOT/'shared/references').rglob('*'):
            if source.is_file():files.append((source,target/'references'/source.relative_to(ROOT/'shared/references')))
        for source in (ROOT/'shared/kontaktlaw_core').glob('*.py'):
            files.append((source,target/'scripts/kontaktlaw_core'/source.name))
        for source,dest in files:
            content=source.read_bytes()
            if plugin == 'kontaktlaw' and source.suffix == '.md':
                overlay=ROOT/'shared/website-profile'/source.relative_to(ROOT/'shared/references') if source.is_relative_to(ROOT/'shared/references') else None
                if overlay and overlay.exists(): content=overlay.read_bytes()
                elif source.parent.name == 'gpt':
                    text=content.decode('utf-8')
                    text=re.sub(r'Output: [^\n]+', 'Output: follow the canonical language rule in SKILL.md and return the task JSON defined in website-contract.json, or the caller task schema. No prose wrapper. For auxiliary tasks without a structured task contract, return an object with an answer string.', text, count=1)
                    content=text.encode('utf-8')
                elif source.name == 'prompt-guide.md':
                    text=content.decode('utf-8');text=re.sub(r'- Use readable prose by default\.[^\n]+', '- Return website-compatible JSON by default; website-contract.md defines the public output. Keep evidence exchange records internally. The caller task schema controls focused worker responses.',text);content=text.encode('utf-8')
                elif source.name == 'evidence-workflow.md':
                    text=content.decode('utf-8')
                    text=re.sub(r'6\. Presentation:[^\n]+', '6. Presentation: convert validated evidence to the website JSON contract; preserve rejected candidates with reasons.',text)
                    text=text.replace('Render Azerbaijani prose with exactly the existing six labeled paragraphs.', 'Render the website JSON contract through website-result.')
                    text=text.replace("Internal JSON does not alter the user's prose output preference. Never show implementation records unless asked.", 'Return website JSON through website-result; keep the evidence exchange internal.')
                    text=text.replace('The conservative writer refuses complex or cross-run edits; use Word for these.', 'The writer preserves formatting across simple runs; complex structures require document-tool repair. For automatic grammar use --all-grammar.')
                    content=text.encode('utf-8')
            if args.check:
                if not dest.exists() or content!=dest.read_bytes():mismatches.append(str(dest.relative_to(ROOT)))
            else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content)
        wrappers={
            'kontaktlaw.py':'from kontaktlaw_core.cli import main\nif __name__ == "__main__":\n    import sys\n    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")\n    main()\n',
            'search_knowledge.py':'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent))\nfrom kontaktlaw_core import knowledge as core\nfrom kontaktlaw_core.knowledge import *\nif __name__ == "__main__":\n    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")\n    core.main()\nelse:\n    sys.modules[__name__] = core\n'}
        for filename,content in wrappers.items():
            dest=target/'scripts'/filename
            if args.check:
                if not dest.exists() or dest.read_text(encoding='utf-8')!=content:mismatches.append(str(dest.relative_to(ROOT)))
            else:dest.write_text(content,encoding='utf-8',newline='\n')
    if mismatches:print('\n'.join(mismatches));return 1
    print('Shared sources and both plugin packages agree.' if args.check else 'Built both independent plugin packages.')
    return 0

if __name__=='__main__':sys.exit(main())
