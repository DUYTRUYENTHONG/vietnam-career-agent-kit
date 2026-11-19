#!/usr/bin/env python3
"""Render a private, offline human annotation form; no models or network calls."""
import argparse
from pathlib import Path
import json
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import tailor_benchmark as b


def render(root, preparation, output, reviewer_slot):
    b.require(reviewer_slot in ('A', 'B'), 'Expected reviewer slot A or B')
    folder, _ = b.verify_bundle(root, preparation, 'tailor_benchmark_preparation')
    cases = b.validate_cases(root, b.read_rows(folder/'cases.jsonl'))
    data = json.dumps(cases, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = b.read_rows(folder/f'review_{reviewer_slot}.jsonl')
    rows = json.dumps(template, ensure_ascii=False).replace('<', '\\u003c')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'">
<title>Private source review</title><style>
body{max-width:1000px;margin:32px auto;padding:0 20px;font:16px/1.5 system-ui;color:#162132}
section{border:1px solid #cbd5e1;border-radius:8px;padding:20px;margin:20px 0}
label{display:block;margin:10px 0}input[type=text],textarea,select{font:inherit;padding:8px;max-width:100%;box-sizing:border-box}
textarea{width:100%;min-height:80px}.fact{padding:8px 0;border-bottom:1px solid #eee}small{display:block;color:#475569}
button{font:inherit;padding:10px 16px;background:#163e60;color:white;border:0;border-radius:5px}
.warning{background:#fff7db;padding:16px}output{display:block;margin:14px 0}
</style><h1>Private CV evidence review — reviewer __SLOT__</h1>
<p class="warning">Work independently. No model suggestions or other reviewer answers are shown. Validate the literal requirement, source scope, qualifiers and source-family grouping. Select a fact only if it can support a truthful relevant bullet; partial experience must stay partial. This form does not prove employment or authenticate reviewer identity.</p>
<label>Your stable reviewer ID <input id="reviewer" type="text" autocomplete="off"></label>
<p>The kit cannot create human gold for you. Do not attest to checks you have not performed. Download saves one JSONL locally; no server or upload is used. Keep it private.</p>
<main id="cases"></main><button id="save">Download completed review</button><output id="status"></output>
<script>
const cases=__CASES__, rows=__ROWS__, states=[];
const main=document.getElementById('cases');
function el(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;}
for(let i=0;i<cases.length;i++){
 const c=cases[i], s=el('section');s.append(el('h2',c.case_id),el('p',c.requirement.text),el('small','Family: '+c.source_group+' | '+c.exposure));
 s.append(el('small','Requirement source: '+c.requirement.source.path+' # '+c.requirement.source.locator+' | SHA256: '+c.requirement.source.sha256));
 const detail=el('details'), summary=el('summary','Inspect supplied evidence ('+c.facts.length+' facts)');detail.append(summary);
 const selected=[];
 for(const f of c.facts){const label=el('label');label.className='fact';const box=el('input');box.type='checkbox';box.value=f.id;
 label.append(box,document.createTextNode(' '+f.id+': '+f.text),el('small',f.scope+' | Qualifiers: '+(f.qualifiers.join(', ')||'inspect source scope')),
 el('small','Source: '+f.source.path+' # '+f.source.locator));detail.append(label);selected.push(box);}
 s.append(detail);const decision=el('select');
 for(const v of ['', 'tailored','not_demonstrated']){const o=el('option',v||'Choose after review');o.value=v;decision.append(o);}
 const why=el('textarea');why.placeholder='Explain source coverage, missing scope and material qualifiers.';
 const checked=el('input');checked.type='checkbox';const label=el('label');label.append(checked,document.createTextNode(' I personally checked the requirement, facts, scope/qualifiers and family grouping.'));
 s.append(el('p','Decision'),decision,el('p','Rationale'),why,label);main.append(s);states.push({decision,why,checked,selected});
}
document.getElementById('save').onclick=()=>{
 try{const who=document.getElementById('reviewer').value.trim();if(!who)throw Error('Enter your reviewer ID.');
 const result=rows.map((row,i)=>{const s=states[i],ids=s.selected.filter(x=>x.checked).map(x=>x.value),d=s.decision.value;
 if(!s.checked.checked||!s.why.value.trim()||!d)throw Error(row.case_id+': complete actual source review, decision and rationale.');
 if((d==='tailored')!==(ids.length>0))throw Error(row.case_id+': tailored requires evidence; not_demonstrated requires none.');
 return {...row,reviewer_id:who,reviewer_type:'human',source_checked:true,expected_decision:d,acceptable_fact_ids:ids,rationale:s.why.value.trim()};});
 const blob=new Blob([result.map(x=>JSON.stringify(x)).join('\\n')+'\\n'],{type:'application/x-ndjson'});
 const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download='review___SLOT___completed.jsonl';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 document.getElementById('status').textContent='Downloaded locally. Keep the file private; it is not automatically imported or approved.';
 }catch(e){document.getElementById('status').textContent=e.message;}
};</script></html>'''
    # Substitute only template placeholders, never placeholder-like source text.
    replacements = {'__CASES__': data, '__ROWS__': rows, '__SLOT__': reviewer_slot}
    html = re.sub('__CASES__|__ROWS__|__SLOT__', lambda match: replacements[match[0]], html)
    path = b.inside(root, output); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(html.encode('utf8'))
    return path


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True); p.add_argument('--preparation', required=True)
    p.add_argument('--output', required=True); p.add_argument('--reviewer-slot', choices=['A', 'B'], required=True)
    a = p.parse_args(argv)
    try:
        path = render(a.root, a.preparation, a.output, a.reviewer_slot)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({'outcome': 'blocked', 'reason': str(exc)})); return 1
    print(json.dumps({'outcome': 'ok', 'file': str(path), 'labels_created': 0})); return 0


if __name__ == '__main__':
    raise SystemExit(main())
