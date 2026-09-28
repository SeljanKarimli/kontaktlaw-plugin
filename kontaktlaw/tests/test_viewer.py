"""Opt-in rendered tests: KONTAKTLAW_RUN_BROWSER_TESTS=1, Playwright + Chrome.

Set KONTAKTLAW_BROWSER to a Chromium executable and KONTAKTLAW_SCREENSHOTS to
an output directory outside the plugin to retain screenshots of synthetic data.
"""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest

from test_review import r, make_docx, raw_docx, grammar_packet, correction, risk_packet


@unittest.skipUnless(os.environ.get('KONTAKTLAW_RUN_BROWSER_TESTS') == '1', 'Opt-in rendered viewer tests')
class ViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.runtime = sync_playwright().start()
        executable = os.environ.get('KONTAKTLAW_BROWSER')
        cls.browser = cls.runtime.chromium.launch(executable_path=executable) if executable else cls.runtime.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True)
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.on('console',lambda m: self.errors.append(m.text) if m.type in ['error','warning'] else None)

    def start(self,state,out):
        r.save(out,state)
        server = r.make_server(out)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.page.goto(server.review_url,wait_until='networkidle')
        self.page.locator('#filename').filter(has_text=state['name']).wait_for()
        self.assertEqual(self.page.title(),'KontaktLaw · Sənəd baxışı')
        self.assertTrue(self.page.locator('#document .source-span').count())
        self.assertEqual(self.page.locator('vite-error-overlay, nextjs-portal').count(),0)
        return server

    def screenshot(self,name):
        directory = Path(os.environ.get('KONTAKTLAW_SCREENSHOTS',self.root))
        directory.mkdir(parents=True,exist_ok=True)
        self.page.screenshot(path=str(directory/name),full_page=True)

    def test_risk_navigation_versions_grammar_download_and_responsive(self):
        source=make_docx(self.root/'Nümunə müqavilə.docx', ['Satıcı və Alıcı.', '2. Alıcı  ödənişi etməlidir. 100 AZN.'] +
                         [f'{i}. Sənədin digər müddəaları və tərəflərin yazılı bildirişləri.' for i in range(3,20)] +
                         ['20. Eyni mətn. Eyni mətn.', '21. 🧾 Əmək müqaviləsi. Şərtlər.', '<script>window.injected=true</script>'])
        out=self.root/'review'
        state=r.prepare(source,out,mode='never')
        state=r.select_party(r.apply_grammar(state,grammar_packet(state,[correction('Alıcı  ödənişi','Alıcı ödənişi')])), 'buyer')
        packet=risk_packet(state,'100 AZN','s2')
        packet['findings'][0]['paragraphs']['Problemli bənd']='2-ci bənd · Ödəniş'
        packet['findings'][0]['title']='Ödəniş mətninə keçid'
        second=risk_packet(state,'Eyni mətn.','s20',2)['findings'][0]
        second['paragraphs']['Problemli bənd']='20-ci bənd · İkinci cümlə'
        second['title']='Təkrarlanan mətnə dəqiq keçid'
        packet['findings'].append(second)
        third=risk_packet(state,'Şərtlər.','s21')['findings'][0]
        third['paragraphs']['Problemli bənd']='21-ci bənd · Şərtlər'
        packet['findings'].append(third)
        state=r.finalize_findings(state,packet)
        self.assertTrue(all(not f['link_error'] for f in state['findings']))
        server=self.start(state,out)
        self.assertIsNone(self.page.evaluate('window.injected'))
        self.page.get_by_role('button',name='Problemli bənd: 2-ci bənd · Ödəniş',exact=True).click()
        self.assertEqual(self.page.locator('#span-s2 mark').inner_text(),'100 AZN')
        self.screenshot('viewer-desktop.png')
        self.page.get_by_role('button',name='Orijinal',exact=True).click()
        self.assertEqual(self.page.locator('#span-s2 mark').inner_text(),'100 AZN')
        self.assertIn('Alıcı  ödənişi',self.page.locator('#span-s2').inner_text())
        self.page.get_by_role('button',name='Problemli bənd: 20-ci bənd · İkinci cümlə',exact=True).click()
        self.assertEqual(self.page.locator('.source-span.selected').count(),1)
        self.assertEqual(self.page.locator('#span-s20 mark').inner_text(),'Eyni mətn.')
        self.assertEqual(self.page.locator('#span-s20 .source-text').evaluate('(e)=>e.firstChild.textContent'),'20. Eyni mətn. ')
        self.assertGreater(self.page.locator('#document-scroll').evaluate('(e)=>e.scrollTop'),0)
        self.assertTrue(self.page.locator('#span-s20').evaluate('(e)=>{const a=e.getBoundingClientRect(),b=document.getElementById("document-scroll").getBoundingClientRect();return a.top>=b.top && a.bottom<=b.bottom}'))
        self.page.goto(server.review_url+'#risk-3',wait_until='networkidle')
        self.assertEqual(self.page.locator('#span-s21 mark').inner_text(),'Şərtlər.')
        self.page.get_by_role('button',name='Qrammatika').click()
        self.page.get_by_role('button',name='Sənəddə göstər',exact=True).click()
        self.page.get_by_role('button',name='Düzəldilmiş',exact=True).click()
        self.assertIn('Alıcı ödənişi',self.page.locator('#span-s2 mark').all_text_contents())
        self.page.get_by_role('button',name='Orijinal',exact=True).click()
        self.assertIn('Alıcı  ödənişi',self.page.locator('#span-s2 mark').all_text_contents())
        with self.page.expect_download() as info:
            self.page.get_by_role('link',name='Mətni endir').click()
        self.assertIn('Alıcı ödənişi',Path(info.value.path()).read_text(encoding='utf-8-sig'))
        for width,height,name in [(620,900,'viewer-panel.png'),(390,844,'viewer-mobile.png')]:
            self.page.set_viewport_size({'width':width,'height':height})
            self.page.get_by_role('button',name='Hüquqi risklər',exact=True).click()
            self.page.get_by_role('button',name='Problemli bənd: 2-ci bənd · Ödəniş',exact=True).click()
            self.assertEqual(self.page.locator('#span-s2 mark').inner_text(),'100 AZN')
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            self.screenshot(name)
        self.assertEqual(self.errors,[])

    def test_table_cells_disabled_links_and_coverage(self):
        source=raw_docx(self.root/'Cədvəl.docx','<w:p><w:r><w:t>Satıcı və Alıcı.</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Məbləğ</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>100 AZN</w:t></w:r></w:p></w:tc><w:tc><w:p/></w:tc></w:tr></w:tbl>')
        out=self.root/'table-review'
        state=r.prepare(source,out,mode='never')
        state=r.select_party(r.apply_grammar(state,grammar_packet(state)),'general')
        packet=risk_packet(state,'100 AZN','s3')
        bad=risk_packet(state,'Missing quotation','s3')['findings'][0]
        packet['findings'].append(bad)
        state=r.finalize_findings(state,packet)
        state['coverage']['extraction_complete']=False
        state['coverage']['warnings'].append({'locator':'sınaq','message':'Vizual yoxlama tələb olunur.'})
        self.start(state,out)
        self.assertEqual(self.page.locator('#document td').count(),3)
        self.assertTrue(self.page.locator('#risk-2 button').is_disabled())
        self.assertTrue(self.page.locator('#coverage').is_visible())
        self.page.locator('#risk-1 button').click()
        self.assertEqual(self.page.locator('td mark').inner_text(),'100 AZN')
        self.assertEqual(self.errors,[])


if __name__ == '__main__':
    unittest.main()
