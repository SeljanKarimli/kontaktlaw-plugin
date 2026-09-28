'use strict';
const $ = id => document.getElementById(id);
const labels = ['Problemli bənd', 'Problemli mətn', 'Riskin izahı', 'Hüquqi əsas', 'Qısa düzəliş təklifi', 'Risk səviyyəsi'];
let review, version = 'corrected', selection = null;
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function pressed(id, value) { $(id).setAttribute('aria-pressed', String(value)); }
function locationLabel(value) {
  return value.replace('word/document.xml','Əsas mətn')
    .replace(/word\/header(\d+)\.xml/,'Üstbilgi $1').replace(/word\/footer(\d+)\.xml/,'Altbilgi $1')
    .replace('word/footnotes.xml','Səhifə qeydləri').replace('word/endnotes.xml','Son qeydlər')
    .replace(/table (\d+)/g,'cədvəl $1').replace(/row (\d+)/g,'sətir $1')
    .replace(/cell (\d+)/g,'xana $1').replace(/paragraph (\d+)/g,'abzas $1')
    .replace(/page (\d+)/g,'səhifə $1').replace(/block (\d+)/g,'mətn hissəsi $1')
    .replace(/image region (\d+)/g,'şəkil sahəsi $1').replace(/image (\d+)/g,'şəkil $1');
}
const coverageMessages = {
  ocr_disabled:'Şəkildəki mətn oxunmayıb; OCR yoxlaması tələb olunur.',
  ocr_unverified:'OCR ilə oxunan mətn orijinal görüntü ilə yoxlanmalıdır.',
  unreadable_image:'Şəkildəki mətn oxuna bilmədi.',
  merged_table:'Birləşdirilmiş cədvəl xanalarının əlaqələri vizual yoxlanmalıdır.',
  complex_table:'Mürəkkəb cədvəl quruluşu vizual yoxlanmalıdır.',
  external_image:'Xarici şəkil yüklənməyib; yerli nüsxə tələb olunur.',
  missing_image:'Sənəddəki şəkil açıla bilmədi.',
  unsupported_image:'Bu şəkil ayrıca vizual yoxlama tələb edir.',
  text_box_order:'Mətn qutularının oxunma ardıcıllığı yoxlanmalıdır.',
  unsupported_content:'Əlavə edilmiş obyekt ayrıca yoxlanmalıdır.',
  unsupported_drawing:'Diaqram və ya təsvir ayrıca yoxlanmalıdır.',
  automatic_numbering:'Avtomatik bənd nömrələri orijinal sənəddə yoxlanmalıdır.',
  field_values:'Avtomatik sahələrin göstərilən dəyərləri orijinal sənəddə yoxlanmalıdır.',
  unreadable_page:'Bu səhifədə oxunaqlı mətn əldə edilməyib.',
  broken_encoding:'Bəzi simvollar düzgün oxunmayıb; OCR və vizual yoxlama tələb olunur.',
  pdf_annotations:'Sənəd qeydləri və forma sahələri ayrıca yoxlanmalıdır.',
  no_readable_text:'Oxunaqlı mətn əldə edilməyib; yoxlama tamamlanmayıb.'
};
function showSelection(anchors, id, title) {
  selection = {anchors, id, title};
  for (const el of document.querySelectorAll('.finding')) el.classList.toggle('active', el.id === id);
  renderDocument();
  $('selection-status').textContent = `${version === 'corrected' ? 'Düzəldilmiş' : 'Orijinal'} · ${title}`;
  const first = anchors[0];
  if (first) {
    const target = $(`span-${first.span_id}`);
    if (target) {
      target.scrollIntoView({block:'center', behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
      target.focus({preventScroll:true});
    }
  }
}
function sourceElement(span) {
  const el = node('section', undefined, 'source-span');
  el.id = `span-${span.id}`; el.tabIndex = -1;
  el.append(node('div', locationLabel(span.locator), 'source-location'));
  const p = node('p', undefined, 'source-text');
  // Python offsets count Unicode code points; Array.from preserves those offsets.
  const chars = Array.from(span.text);
  let ranges = (selection?.anchors || []).filter(a => a.span_id === span.id).map(a => a[version]);
  ranges = ranges.filter(r => chars.slice(r.start, r.end).join('') === r.quote).sort((a,b) => a.start-b.start);
  const merged = [];
  for (const r of ranges) {
    if (merged.length && r.start <= merged[merged.length-1].end) merged[merged.length-1].end = Math.max(r.end, merged[merged.length-1].end);
    else merged.push({...r});
  }
  let cursor = 0;
  for (const r of merged) {
    p.append(document.createTextNode(chars.slice(cursor,r.start).join('')));
    p.append(node('mark',chars.slice(r.start,r.end).join(''))); cursor = r.end;
  }
  p.append(document.createTextNode(chars.slice(cursor).join(''))); el.append(p);
  el.classList.toggle('selected', merged.length > 0);
  if (span.method === 'ocr') el.append(node('div', review.verified_ocr.includes(span.id) ? 'OCR · vizual yoxlanılıb' : 'OCR · vizual yoxlama tələb olunur', 'ocr-label'));
  return el;
}
function renderDocument() {
  const root = $('document'); root.replaceChildren();
  let lastTable = null, table = null, cells = new Map();
  for (const span of review[version]) {
    const match = span.locator.match(/^(.*?, table \d+), row (\d+), cell (\d+), paragraph/);
    if (!match) { lastTable = null; root.append(sourceElement(span)); continue; }
    if (lastTable !== match[1]) {
      lastTable = match[1]; cells = new Map();
      const wrap = node('div',undefined,'table-scroll'); table = node('table');
      table.setAttribute('aria-label',locationLabel(match[1])); wrap.append(table); root.append(wrap);
      const shape = review.tables?.find(t => t.locator === match[1]);
      for (const size of shape?.row_sizes || []) {
        const row = table.insertRow(); for (let i=0;i<size;i++) row.insertCell();
      }
    }
    const rowNumber = Number(match[2]), cellNumber = Number(match[3]);
    while (table.rows.length < rowNumber) table.insertRow();
    const row = table.rows[rowNumber-1];
    while (row.cells.length < cellNumber) row.insertCell();
    const key = `${rowNumber}-${cellNumber}`;
    if (!cells.has(key)) cells.set(key,row.cells[cellNumber-1]);
    cells.get(key).append(sourceElement(span));
  }
  if (!review[version].length) root.append(node('p','Oxunaqlı mətn əldə edilməyib. Oxunma məhdudiyyətlərinə baxın.','empty'));
}
function renderFindings() {
  const root = $('risks'); root.replaceChildren();
  $('risk-count').textContent = `${review.findings.length} risk`;
  if (!review.findings.length) {
    const text = review.stage === 'complete' ? 'Mövcud mətn üzrə əhəmiyyətli hüquqi risk aşkarlanmayıb.' : review.stage === 'extracted' ? 'Əvvəlcə qrammatika yoxlanılır.' : review.stage === 'grammar_complete' ? 'Davam etmək üçün Codex-də təhlil ediləcək tərəfi seçin.' : 'Seçilmiş tərəfin maraqları baxımından hüquqi təhlil hazırlanır.';
    root.append(node('p',text,'empty'));
  }
  review.findings.forEach((risk,i) => {
    const card = node('section',undefined,'finding'); card.id = risk.id;
    card.append(node('h3',`${i+1}. ${risk.title}`));
    for (const label of labels) {
      const p = node('p'); p.append(node('strong',label));
      if (label === 'Problemli bənd') {
        const button = node('button',risk.paragraphs[label],'clause-link');
        button.setAttribute('aria-label',`Problemli bənd: ${risk.paragraphs[label]}`);
        button.disabled = !risk.anchors.length;
        button.addEventListener('click',() => showSelection(risk.anchors,risk.id,risk.paragraphs[label]));
        p.append(button);
        if (risk.link_error) p.append(node('span',' · Dəqiq yer təsdiqlənməyib; keçid deaktivdir.','link-warning'));
      } else p.append(node('span',risk.paragraphs[label],label === 'Risk səviyyəsi' ? 'severity' : undefined));
      card.append(p);
    }
    root.append(card);
  });
}
function renderGrammar() {
  $('grammar-count').textContent = `(${review.corrections.length})`;
  const root = $('grammar'); root.replaceChildren();
  if (!review.corrections.length) root.append(node('p',review.stage === 'extracted' ? 'Qrammatika yoxlanılır.' : 'Tətbiq ediləcək dəqiq qrammatik səhv aşkarlanmayıb.','empty'));
  review.corrections.forEach((change,i) => {
    const card = node('section',undefined,'finding'); card.id = `grammar-${i}`;
    card.append(node('h3',`${i+1}. Qrammatik düzəliş`));
    card.append(node('p',change.quote,'grammar-before'),node('p',change.replacement,'grammar-after'),node('p',change.reason));
    const button = node('button','Sənəddə göstər','clause-link');
    const anchor = {span_id:change.span_id, original:{start:change.start,end:change.end,quote:change.quote},corrected:{start:change.corrected_start,end:change.corrected_end,quote:change.replacement}};
    button.addEventListener('click',() => showSelection([anchor],card.id,`Qrammatik düzəliş ${i+1}`));
    card.append(button); root.append(card);
  });
}
function setVersion(next) {
  version = next; pressed('corrected-tab',next === 'corrected'); pressed('original-tab',next === 'original');
  if (selection) showSelection(selection.anchors,selection.id,selection.title); else renderDocument();
}
function selectHash() {
  const risk = review?.findings.find(r => r.id === location.hash.slice(1));
  if (risk?.anchors.length) {
    $('risks-tab').click();
    showSelection(risk.anchors,risk.id,risk.paragraphs['Problemli bənd']);
  }
}
window.addEventListener('hashchange',selectHash);
$('corrected-tab').addEventListener('click',() => setVersion('corrected'));
$('original-tab').addEventListener('click',() => setVersion('original'));
for (const kind of ['risks','grammar']) $(kind+'-tab').addEventListener('click',() => {
  $('risks').hidden = kind !== 'risks'; $('grammar').hidden = kind !== 'grammar';
  pressed('risks-tab',kind === 'risks'); pressed('grammar-tab',kind === 'grammar');
});
async function init() {
  try {
    const response = await fetch('review.json',{cache:'no-store'});
    if (!response.ok) throw new Error('load');
    review = await response.json(); $('filename').textContent = review.name;
    const party = review.parties.find(p => p.id === review.selected_party);
    $('perspective').textContent = party ? `Müqavilə ${party.name} (${party.role}) maraqları baxımından ${review.stage === 'complete' ? 'təhlil edilmişdir' : 'təhlil edilir'}.` : review.selected_party === 'general' ? 'Ümumi baxış · Hər riskdə təsirə məruz qalan tərəf göstərilir.' : 'Tərəf seçimi Codex-də aparılır.';
    if (!review.coverage.extraction_complete || review.coverage.warnings.length) {
      $('coverage').hidden = false;
      for (const warning of review.coverage.warnings) $('warnings').append(node('li',`${locationLabel(warning.locator)}: ${coverageMessages[warning.code] || warning.message}`));
    }
    renderFindings(); renderGrammar(); renderDocument();
    selectHash();
  } catch (_) {
    $('filename').textContent = 'Sənəd açılmadı'; $('error').hidden = false;
    $('error').textContent = 'Yerli baxış xidməti dayandırılıb və ya sənəd hazır deyil. Codex-dən sənəd baxışını yenidən açmasını istəyin.';
  }
}
init();
