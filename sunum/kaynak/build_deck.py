#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2_template.html + deck_data.json  ->  sunum/v2.html  (+ headless doğrulama koşumu)"""
import pathlib, re, subprocess, sys

SP = pathlib.Path(r"C:/Users/darkb/AppData/Local/Temp/claude/C--Users-darkb-Desktop-hb-final/e7189315-fed6-416f-988d-d776129e0973/scratchpad")
DEST = pathlib.Path(r"C:/Users/darkb/Desktop/hb-final/sunum/v2.html")

tpl = (SP / "v2_template.html").read_text(encoding="utf-8")
data = (SP / "deck_data.json").read_text(encoding="utf-8")
assert "__DATA__" in tpl, "şablonda __DATA__ yer tutucusu yok"
out = tpl.replace("__DATA__", data)
DEST.write_text(out, encoding="utf-8")

js = re.search(r"<script>(.*)</script>", out, re.S).group(1)
(SP / "deck.js").write_text(js, encoding="utf-8")

cut = js.index("/* ══════════════ kurulum ══════════════ */")
names = re.findall(r"^function (chart\w+)\(", js[:cut], re.M)
reg = ",".join(f"{n[5:].lower()}:{n}" for n in names)
harness = js[:cut] + f"""
const CH={{{reg}}};
const NAMES=Object.keys(CH);
let bad=0;
for(const n of NAMES){{
  let o; try{{o=CH[n]()}}catch(e){{console.log('HATA',n,e.message);bad++;continue}}
  const nan=(o.match(/NaN|undefined|Infinity/g)||[]);
  console.log((nan.length?'X ':'OK'),n.padEnd(10),String(o.length).padStart(6),
              nan.length?('<< '+[...new Set(nan)].join(',')):'');
  if(nan.length)bad++;
}}
console.log('slayt:',SL.length);
SL.forEach((s,i)=>{{ if(!s.notes||s.notes.length<80) console.log('X kisa not:',i+1,s.title);
                    if(!s.use||s.use.length<40) console.log('X kisa kullanim:',i+1,s.title); }});
const used=new Set([...SL.map(s=>s.html).join('').matchAll(/data-c="(\\w+)"/g)].map(m=>m[1]));
console.log('kullanilmayan:',NAMES.filter(n=>!used.has(n)).join(', ')||'(yok)');
console.log('tanimsiz    :',[...used].filter(n=>!NAMES.includes(n)).join(', ')||'(yok)');
console.log(bad?('SORUN: '+bad):'TEMIZ');
"""
(SP / "harness.js").write_text(harness, encoding="utf-8")
print(f"build ok  {DEST}  {len(out)} bayt  ·  {len(names)} grafik")
r = subprocess.run(["node", str(SP / "harness.js")], capture_output=True, text=True, encoding="utf-8")
print(r.stdout or r.stderr)
sys.exit(0 if "TEMIZ" in (r.stdout or "") else 1)
