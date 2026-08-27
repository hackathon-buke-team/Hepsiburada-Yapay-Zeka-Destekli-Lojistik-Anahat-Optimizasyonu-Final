#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2_template.html + deck_data.json + net_data.json + foto/*.jpg  ->  sunum/v2.html
   (+ headless doğrulama koşumu: grafikler, pop-up'lar, konuşma notları)"""
import base64, json, pathlib, re, subprocess, sys, tempfile

SRC = pathlib.Path(__file__).resolve().parent          # sunum/kaynak
DEST = SRC.parent / "v2.html"                          # sunum/v2.html
TMP = pathlib.Path(tempfile.mkdtemp(prefix="deckbuild-"))
PHOTOS = {"melih": "melih_bg.jpg", "eren": "eren_bg.jpg",      # takım slaydı
          "serhat": "serhat_bg.jpg", "mert": "mert_bg.jpg",
          "hb": "hepsiburada.png"}                     # kapak logosu

tpl = (SRC / "v2_template.html").read_text(encoding="utf-8")
data = (SRC / "deck_data.json").read_text(encoding="utf-8")
net = (SRC / "net_data.json").read_text(encoding="utf-8")
photos = json.dumps({
    k: ("data:image/" + ("png" if f.endswith(".png") else "jpeg") + ";base64,"
        + base64.b64encode((SRC / "foto" / f).read_bytes()).decode("ascii"))
    for k, f in PHOTOS.items()}, ensure_ascii=False, separators=(",", ":"))
for ph in ("__DATA__", "__NET__", "__PHOTOS__"):
    assert ph in tpl, f"şablonda {ph} yer tutucusu yok"
out = (tpl.replace("__DATA__", data).replace("__NET__", net)
          .replace("__PHOTOS__", photos))
DEST.write_text(out, encoding="utf-8")
WEB = SRC.parent / "web" / "index.html"          # vercel deploy kopyasi
WEB.parent.mkdir(exist_ok=True)
WEB.write_text(out, encoding="utf-8")

js = re.search(r"<script>(.*)</script>", out, re.S).group(1)
(TMP / "deck.js").write_text(js, encoding="utf-8")

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
for(const k of Object.keys(POP)){{
  let h; try{{h=POP[k].b()}}catch(e){{console.log('HATA pop',k,e.message);bad++;continue}}
  const nan=(h.match(/NaN|undefined|Infinity/g)||[]);
  console.log((nan.length?'X ':'OK'),('pop:'+k).padEnd(14),String(h.length).padStart(6),
              nan.length?('<< '+[...new Set(nan)].join(',')):'');
  if(nan.length)bad++;
}}
console.log('slayt:',SL.length);
SL.forEach((s,i)=>{{ if(!s.notes||s.notes.length<80) console.log('X kisa not:',i+1,s.title);
                    if(!s.use||s.use.length<40) console.log('X kisa kullanim:',i+1,s.title); }});
const html=SL.map(s=>s.html).join('');
const used=new Set([...html.matchAll(/data-c="(\\w+)"/g)].map(m=>m[1]));
console.log('kullanilmayan:',NAMES.filter(n=>!used.has(n)).join(', ')||'(yok)');
console.log('tanimsiz    :',[...used].filter(n=>!NAMES.includes(n)).join(', ')||'(yok)');
const pk=new Set([...html.matchAll(/data-pop="([\\w-]+)"/g)].map(m=>m[1]));
const pmiss=[...pk].filter(k=>!POP[k]);
const punused=Object.keys(POP).filter(k=>!pk.has(k));
console.log('pop bagli   :',pk.size);
console.log('pop tanimsiz:',pmiss.join(', ')||'(yok)');
console.log('pop bagsiz  :',punused.join(', ')||'(yok)');
if(pmiss.length||punused.length)bad++;
console.log('merkez:',NET.centres.length,'hat:',NET.lanes.length,
            'talep goruleni:',NET.lanes.filter(l=>l[4]).length);
if(NET.centres.length!==18||NET.lanes.length!==306||NET.lanes.filter(l=>l[4]).length!==289){{
  console.log('X ag verisi beklenenden farkli');bad++;}}
console.log(bad?('SORUN: '+bad):'TEMIZ');
"""
(TMP / "harness.js").write_text(harness, encoding="utf-8")
print(f"build ok  {DEST}  {len(out)} bayt  ·  {len(names)} grafik")
r = subprocess.run(["node", str(TMP / "harness.js")], capture_output=True, text=True,
                   encoding="utf-8")
print(r.stdout or r.stderr)
sys.exit(0 if "TEMIZ" in (r.stdout or "") else 1)
