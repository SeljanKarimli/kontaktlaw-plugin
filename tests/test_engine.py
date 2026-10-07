import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'shared'))
from kontaktlaw_core.exchange import envelope,validate,digest
from kontaktlaw_core.documents import extract,apply_docx,compare,clean_docx
from kontaktlaw_core.workspace import library_add,approve,draft,stage_source
from kontaktlaw_core.knowledge import article,search
from argparse import Namespace

class EvidenceTests(unittest.TestCase):
 def base(self,text='The Supplier are required to deliver 10 chairs, not 20.'):
  return envelope([{'id':'p0','text':text,'locator':'paragraph 1','variant':'current'}],'synthetic')
 def edit(self,data,quote='are',replacement='is',mode='grammar'):
  start=data['document']['spans'][0]['text'].index(quote)
  data['edits']=[{'id':'e1','span_id':'p0','start':start,'end':start+len(quote),'quote':quote,'replacement':replacement,'mode':mode}]
  return data
 def test_minimal_grammar(self):self.assertEqual(validate(self.edit(self.base())),[])
 def test_stale_document(self):
  original=self.base();result=self.base('Changed contract');self.assertTrue(any('Stale' in e for e in validate(result,original)))
 def test_forged_hash(self):
  x=self.base();x['document']['spans'][0]['text']='forged';self.assertIn('Document hash mismatch',validate(x))
 def test_protected_number_and_negation(self):
  for quote,replacement in [('10','20'),('not','now'),('Supplier','Buyer')]:
   with self.subTest(quote=quote):self.assertTrue(any('protected' in e for e in validate(self.edit(self.base(),quote,replacement))))
 def test_overlap_and_duplicate(self):
  x=self.edit(self.base());x['edits'].append(copy.deepcopy(x['edits'][0]));self.assertTrue(any('overlapping' in e for e in validate(x)))
 def test_wrong_offset(self):
  x=self.edit(self.base());x['edits'][0]['start']+=1;self.assertTrue(any('target mismatch' in e for e in validate(x)))
 def test_revision_edit_blocked(self):
  x=self.edit(self.base());x['document']['spans'][0]['variant']='unresolved';self.assertTrue(any('revision' in e for e in validate(x)))
 def test_complete_claim_blocked(self):
  x=self.base();x['coverage']['review_complete']=True;self.assertTrue(validate(x))
 def test_invented_authority(self):
  x=self.base();x['findings']=[{'id':'f','span_id':'p0','quote':'10 chairs','kind':'legal','affected_party':'Buyer','evidence_ids':['fake']}];self.assertTrue(validate(x))
 def test_false_current_law_claim(self):
  x=self.base();x['evidence']=[{'id':'law','title':'Source','locator':'article 1','quote':'rule','source_text':'rule','source_sha256':digest('rule'),'status':'snapshot','current_law_verified':True}];self.assertTrue(any('certification' in e for e in validate(x)))
 def test_unicode_codepoint_offsets(self):self.assertEqual(validate(self.edit(self.base('😀 The Supplier are ready.'),'are','is')),[])
 def test_deadline_without_trigger(self):
  x=self.base();x['obligations']=[{'span_id':'p0','quote':'10 chairs','calculated_date':'2026-10-01'}];self.assertTrue(validate(x))
 def test_malformed_collections_fail(self):
  for name in ('findings','evidence','edits','obligations'):
   x=self.base();x[name]=None;self.assertTrue(validate(x))

class DocumentTests(unittest.TestCase):
 def fixture(self,folder,revision=False):
  p=Path(folder)/'original.docx'
  xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>The Supplier are ready.</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table amount 100.</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
  if revision:xml+='<w:p><w:del w:author="Reviewer"><w:r><w:delText>old term</w:delText></w:r></w:del><w:ins><w:r><w:t>new term</w:t></w:r></w:ins></w:p>'
  xml+='</w:body></w:document>'
  with ZipFile(p,'w') as z:
   z.writestr('word/document.xml',xml);z.writestr('word/comments.xml','<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:comment w:id="0"><w:p><w:r><w:t>Keep this comment.</w:t></w:r></w:p></w:comment></w:comments>');z.writestr('word/styles.xml','unchanged styles')
  return p
 def test_table_comments_revisions(self):
  with tempfile.TemporaryDirectory() as d:
   x=extract(self.fixture(d,True));self.assertEqual(len(x['document']['spans']),4);self.assertEqual(x['document']['spans'][2]['variant'],'original');self.assertEqual(x['document']['spans'][2]['text'],'old term');self.assertEqual(x['document']['spans'][3]['text'],'new term');self.assertIn('Keep this comment',x['document']['comments'][0]['text'])
 def test_apply_preserves_zip_parts_and_original(self):
  with tempfile.TemporaryDirectory() as d:
   path=self.fixture(d,True);before=path.read_bytes();x=extract(path);EvidenceTests().edit(x);out=Path(d)/'new.docx';apply_docx(path,x,out,['e1']);self.assertEqual(path.read_bytes(),before)
   self.assertIn('Supplier is ready',extract(out)['document']['spans'][0]['text'])
   with ZipFile(path) as a,ZipFile(out) as b:
    for name in a.namelist():
     if name!='word/document.xml':self.assertEqual(a.read(name),b.read(name))
 def test_no_original_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   path=self.fixture(d);x=extract(path);EvidenceTests().edit(x)
   with self.assertRaises(ValueError):apply_docx(path,x,path,['e1'])
 def test_clean_copy_requires_explicit_revision_view(self):
  with tempfile.TemporaryDirectory() as d:
   path=self.fixture(d,True);out=Path(d)/'clean.docx';clean_docx(path,out,'revised');x=extract(out)
   self.assertEqual(x['document']['spans'][2]['text'],'new term');self.assertEqual(x['document']['spans'][2]['variant'],'current')
   self.assertEqual(extract(path)['document']['spans'][2]['variant'],'original')
 def test_comparison(self):
  a=EvidenceTests().base('Payment after acceptance.');b=EvidenceTests().base('Payment before acceptance.');self.assertEqual(compare(a,b)['changes'][0]['type'],'replace')

class LibraryTests(unittest.TestCase):
 def test_approval_and_missing_terms(self):
  with tempfile.TemporaryDirectory() as d:
   record={'id':'supply','jurisdiction':'AZ','contract_type':'supply','party_position':'buyer','preferred_wording':'Pay {{amount}} after {{trigger}}.','fallback_wording':'Negotiate.'};library_add(d,record)
   with self.assertRaises(ValueError):draft(d,'supply',{})
   approve(d,'supply','Test human');result=draft(d,'supply',{'amount':'AZN 100'});self.assertIn('[[MISSING: trigger]]',result['text'])
 def test_traversal_blocked(self):
  with self.assertRaises(ValueError):draft('.','../secret',{})
 def test_changed_context_revokes_approval(self):
  with tempfile.TemporaryDirectory() as d:
   record={'id':'supply','jurisdiction':'AZ','contract_type':'supply','party_position':'buyer','preferred_wording':'Pay {{amount}}.','fallback_wording':'Negotiate.'};library_add(d,record);approve(d,'supply','Test human')
   path=Path(d)/'library/supply.json';record=json.loads(path.read_text(encoding='utf-8'));record['party_position']='seller';path.write_text(json.dumps(record),encoding='utf-8')
   with self.assertRaises(ValueError):draft(d,'supply',{})

class SourceRefreshTests(unittest.TestCase):
 def test_stage_preserves_previous_and_detects_removed_article(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'knowledge';(root/'MDs').mkdir(parents=True);previous='## Maddə 1\nFirst rule\n## Maddə 2\nSecond rule\n';(root/'MDs/law.md').write_text(previous,encoding='utf-8');(root/'sources.json').write_text(json.dumps({'sources':[{'file':'law.md','official_url':'https://e-qanun.az/framework/123'}]}),encoding='utf-8')
   candidate=Path(d)/'candidate.md';candidate.write_text('## Maddə 1\nUpdated rule\n',encoding='utf-8');out=stage_source(root,'law.md',candidate,Path(d)/'workspace','https://e-qanun.az/framework/123','2026-09-22T00:00:00Z')
   self.assertEqual(out['removed_articles'],['2']);self.assertFalse(out['promoted']);self.assertEqual((root/'MDs/law.md').read_text(encoding='utf-8'),previous);self.assertTrue((Path(out['staging_directory'])/'previous.md').exists())

class RetrievalTests(unittest.TestCase):
 def test_cross_language(self):
  result=search(Namespace(query='termination liability',article=None,law='Mülki',limit=6));self.assertGreater(result['matching_chunks'],0)
 def test_complete_article(self):
    result=article('Mülki','390');self.assertEqual(result['article'],'390');self.assertGreater(len(result['text']),100);self.assertNotIn('truncated',result)
 def test_snapshot_evidence_checked_against_actual_file(self):
  record=article('Mülki','390');x=EvidenceTests().base()
  x['evidence']=[{'id':'law','title':record['title'],'locator':'article 390','file':record['file'],'start':record['start'],'end':record['end'],'url':record['official_url'],'source_text':record['text'],'quote':record['text'][:40],'source_sha256':digest(record['text']),'status':'snapshot'}]
  self.assertEqual(validate(x),[]);x['evidence'][0]['title']='Invented Code';self.assertTrue(any('catalog' in e for e in validate(x)))

if __name__=='__main__':unittest.main()
