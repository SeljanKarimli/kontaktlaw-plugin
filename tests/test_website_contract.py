import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'shared'))
from kontaktlaw_core.exchange import envelope
from kontaktlaw_core.website import export_review, utf16_length

class WebsiteContract(unittest.TestCase):
    def test_json_profile_overrides_prose_without_changing_text_plugin(self):
        root=Path(__file__).resolve().parents[1]
        skill=(root/'kontaktlaw/skills/legal-review/SKILL.md').read_text(encoding='utf-8')
        risk=(root/'kontaktlaw/skills/legal-review/references/prompts/gpt/risk_review.md').read_text(encoding='utf-8')
        self.assertIn('website-compatible JSON by default',skill)
        self.assertNotIn('prose-only user output rule',skill)
        self.assertNotIn('Use exactly this prose layout',risk)
        self.assertIn('Use exactly this prose layout',(root/'kontaktlaw-text/skills/legal-review-text/references/prompts/gpt/risk_review.md').read_text(encoding='utf-8'))
    def test_unicode_and_empty_replacement(self):
        text='😀 söz söz.'
        data=envelope([{'id':'p0','text':text,'locator':'1'}], 'synthetic.txt')
        data['edits']=[{'id':'g1','span_id':'p0','start':2,'end':6,'quote':'söz ','replacement':'','mode':'grammar'}]
        result=export_review(data,'gpt-6.1-sol','low','a'*64)
        finding=result['documentReview']['findings'][0]
        self.assertEqual(finding['source_span']['start'],3)
        self.assertEqual(finding['replacement'],'')
        self.assertEqual(utf16_length('😀'),2)
        self.assertEqual(data['document']['spans'][0]['text'],text)
    def test_unsupported_legal_claim_and_reserved_party_are_rejected(self):
        data=envelope([{'id':'p0','text':'A pays B.','locator':'1'}],'synthetic.txt')
        data['findings']=[{'id':'r','span_id':'p0','quote':'A pays B.','affected_party':'A','kind':'legal','legal_basis':'Invented law'}]
        result=export_review(data,'gpt-6.1-sol','low','b'*64)['documentReview']
        self.assertEqual(result['findings'],[])
        self.assertIn('inspected evidence',result['rejectedFindings'][0]['reason'])
        data['findings'][0].update(kind='commercial', affected_party='party-general')
        self.assertEqual(export_review(data,'gpt-6.1-sol','low','b'*64)['documentReview']['findings'],[])
    def test_rejected_risk_is_retained(self):
        data=envelope([{'id':'p0','text':'A pays B.','locator':'1'}],'synthetic.txt')
        data['selected_party']='A'
        data['findings']=[{'id':'r','span_id':'p0','quote':'A pays B.','affected_party':'B'}]
        result=export_review(data,'gpt-6.1-sol','low','b'*64)['documentReview']
        self.assertEqual(result['findings'],[])
        self.assertEqual(result['rejectedFindings'][0]['id'],'r')
if __name__=='__main__': unittest.main()
