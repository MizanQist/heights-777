#!/usr/bin/env python3
"""Build the print edition of the Heights 777 brochure (A4 landscape, twelve sheets)
from the live index.html and render it to PDF with Chromium through Playwright.

    python3 tools/make_pdf.py            # rebuild print.html and the PDF
    python3 tools/make_pdf.py --maps     # also re-render the neighbourhood map images (needs the network)

The print page reuses the site's design tokens, component rules and drawing code
(the floor stack, the plan markers, the metre site plan), so nothing diverges.
Intermediate files live in tools/print/; the PDF lands in the brochure root.
"""
import re, sys, os, json
from playwright.sync_api import sync_playwright
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(HERE, 'print'); os.makedirs(OUT, exist_ok=True)
PDF = os.path.join(SITE, 'heights-777-brochure.pdf')
A = '../../assets/'
N = 12
WANT_MAPS = '--maps' in sys.argv

src = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
css_all = src[src.find('<style>')+7:src.find('</style>')]
js_all = src[src.rfind('<script>')+8:src.rfind('</script>')]
fonts = re.search(r'<link rel="stylesheet" href="https://fonts.googleapis.com[^"]*">', src).group(0)
tokens = re.search(r':root\{.*?\}', css_all, re.S).group(0)
tone_d = re.search(r'\.page\[data-tone="dark"\]\{[^}]*\}', css_all).group(0).replace('.page[data-tone="dark"]', '.sheet[data-tone="dark"]')
tone_l = re.search(r'\.page\[data-tone="light"\]\{[^}]*\}', css_all).group(0).replace('.page[data-tone="light"]', '.sheet[data-tone="light"]')

KEEP = ('.eyebrow', '.title', '.lede', '.body', '.foot-note', '.stats', '.stat', '.also', '.stack-fig', '.notes', '.note', '.fig', '.plan .labs', '.plan .mk',
        '.plan .north', '.legend', '.rcard', '.facts', '.skeys', '.skey', '.spec', '.drive', '.sp-', '.siteplan', '.close .big', '.close-grid', '.toc', '.who',
        '.contact', '.disc', '.mark', '.cover-sub', '.cred', 'h3,h4', '.sched')
rules = []
for line in css_all.split('\n'):
    t = line.strip()
    if not t or t.startswith('/*') or t.startswith('@') or t.startswith('.js') or t.startswith('*,') or t.startswith('html') or t.startswith('body') or t.startswith('img'):
        continue
    if any(t.startswith(k) for k in KEEP):
        rules.append(t)

def block(start, end):
    i = js_all.find(start); j = js_all.find(end, i+1); assert i >= 0 and j > i, start
    return js_all[i:j]
levels_js = block("  var LEVELS = [", "  var svg = $('#stacksvg')")
stack_js = block("  (function build(){", "  function setLevel(i, user){")
rooms_js = block("  var ROOMS = {", "  var PLANLAB")
site_js = block("  (function buildSite(){", "  /* ——— location map")

spec_html = src[src.find('<div class="spec">'):src.find('</div>\n      </div>\n    </div>\n    <div class="pfoot">', src.find('<div class="spec">'))+6]
spec_html = re.sub(r'(class="[^"]*?) rv" style="--i:\d+"', r'\1"', spec_html)
ci = src.find('<div class="contact" style="margin-top:12px">')
contact_html = src[ci:src.find('</div>', ci)+6]
sk = src.find('<ol class="skeys" id="skeys">')
skeys_html = src[sk:src.find('</ol>', sk)+5]
mapdata = json.loads(re.search(r'window\.COVA_MAP=(\{.*\});', open(os.path.join(SITE, 'assets', 'map-data.js'), encoding='utf-8').read(), re.S).group(1))

# ---- print-tier images
def flat(name, bg=(235, 230, 219), ink=None):
    """Flatten a transparent drawing onto the panel colour; with ink=(r,g,b) the alpha channel is used as the ink mask,
    for drawings whose strokes were coloured light for the site's dark pages."""
    dst = os.path.join(OUT, name + '.png')
    if not os.path.exists(dst):
        im = Image.open(os.path.join(SITE, 'assets', name + '.png')).convert('RGBA')
        if ink:
            a = im.getchannel('A'); im = Image.new('RGBA', im.size, ink + (0,)); im.putalpha(a)
        b = Image.new('RGBA', im.size, bg + (255,)); b.alpha_composite(im)
        b.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=96).save(dst, optimize=True)
    return name + '.png'
def render(name, maxh=1800):
    dst = os.path.join(OUT, name + '.jpg')
    if not os.path.exists(dst):
        im = Image.open(os.path.join(SITE, 'assets', name + '.jpg')).convert('RGB')
        if im.height > maxh: im = im.resize((round(im.width*maxh/im.height), maxh), Image.LANCZOS)
        im.save(dst, quality=82, optimize=True, progressive=True)
    return name + '.jpg'
PLAN_T, PLAN_U, SECTION = flat('plan-typical'), flat('plan-upper'), flat('section', ink=(20, 22, 26))
R = {n: render(n) for n in ('corner-dusk', 'entrance-day', 'entrance-dusk', 'front-overcast', 'front-clear', 'balconies-aerial', 'street-day')}

# ---- neighbourhood map images
def render_maps():
    lm_rules = '\n'.join(l.strip() for l in css_all.split('\n') if l.strip().startswith('.lm-map'))
    html = f'''<!DOCTYPE html><html><head><meta charset="utf-8">{fonts}
<link rel="stylesheet" href="{A}leaflet/leaflet.css">
<style>{tokens}
{tone_l.replace('.sheet[data-tone="light"]', '.lm-map[data-tone="light"]')}
body{{margin:0;background:#fff;font-family:var(--font-body)}}
.lm-map{{position:relative;overflow:hidden;background:#ebe6db}}
#m{{width:1000px;height:900px}} #c{{width:520px;height:520px;margin-top:24px}}
#m1,#c1{{width:100%;height:100%}}
{lm_rules}
.lm-map.print .lm-pin b{{opacity:0!important}}
.lm-map.print .lm-pin.lm-site b{{opacity:1!important;font-size:21px;top:-15px;line-height:30px;left:16px}}
.lm-map.print .lm-pin i{{width:30px;height:30px;left:-15px;top:-15px;font-size:12px;line-height:27px;box-shadow:0 2px 8px rgba(13,15,18,.4)}}
.lm-map.print .lm-pin.lm-site i{{width:22px;height:22px;left:-11px;top:-11px}}
.lm-map.print .lm-pin.lm-site i::after{{animation:none;inset:-5px;opacity:.75}}
.lm-map.print .lm-st span{{font-size:12.5px;opacity:.85}}
.lm-map.print .lm-st.ring span{{font-size:15px}}
.lm-map.print .lm-st.near span{{font-size:11.5px}}
.lm-map.print .leaflet-control-container{{display:none}}
</style></head><body>
<div class="lm-map print z-mid" data-tone="light" id="m"><div id="m1"></div></div>
<div class="lm-map print z-near" data-tone="light" id="c"><div id="c1"></div></div>
<script src="{A}leaflet/leaflet.js"></script><script src="{A}map-data.js"></script>
<script>
(function(){{
  var D = window.COVA_MAP, C = {{marine:'#0d0f12', iroko:'#d2ae74', deep:'#a9835a', sea:'#7f9aa0', bone:'#f3efe7'}};
  var LABPOS = {{parakou:[9.079279,7.468153], aminu:[9.0800,7.4720], adetok:[9.0736,7.4880], herbert:[9.0664,7.4600], shehu:[9.0958,7.4753], ahmadu:[9.0250,7.4865], constitution:[9.0500,7.4760], nnamdi:[9.0440,7.4566], umaru:[9.0072,7.4159]}};
  var ST = {{main:{{color:C.marine, weight:3, opacity:.5}}, local:{{color:C.marine, weight:2, opacity:.36}}, close:{{color:C.deep, weight:3.5, opacity:.95}}, bridge:{{color:C.sea, weight:3.5, opacity:.95}}}};
  function build(id, rings){{
    var map = L.map(id, {{zoomControl:false, attributionControl:false, zoomSnap:.5, fadeAnimation:false, zoomAnimation:false, markerZoomAnimation:false}});
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxNativeZoom:19, maxZoom:20}}).addTo(map);
    function label(ll, text, cls, tr){{ return L.marker(ll, {{icon:L.divIcon({{className:'lm-st '+cls, html:'<span style="transform:'+tr+'">'+text+'</span>', iconSize:[0,0]}}), interactive:false, keyboard:false}}).addTo(map); }}
    function m2ll(ll, dxm, dym){{ return [ll[0] + dym/111320, ll[1] + dxm/109930]; }}
    if(rings) [1000,2000,5000].forEach(function(r){{ L.circle(D.site, {{radius:r, color:C.marine, weight:1, opacity:.3, dashArray:'2 7', fill:false, interactive:false}}).addTo(map); label(m2ll(D.site,0,r), (r/1000)+' km', 'ring', 'translate(-50%,-50%)'); }});
    D.streets.forEach(function(s){{
      s.s.forEach(function(seg){{ L.polyline(seg, L.extend({{interactive:false, lineCap:'round', lineJoin:'round'}}, ST[s.c])).addTo(map); }});
      var pref = LABPOS[s.k]; if(!pref) return; var best=null, bd=1e9, ang=0;
      s.s.forEach(function(seg){{ for(var i=0;i<seg.length;i++){{ var p=seg[i], dd=Math.hypot((p[0]-pref[0])*111320,(p[1]-pref[1])*109930); if(dd<bd){{ bd=dd; best=p; var q=seg[i+1]||seg[i-1]||p; ang=-Math.atan2((q[0]-p[0])*111320,(q[1]-p[1])*109930)*180/Math.PI; }} }} }});
      if(ang>90) ang-=180; if(ang<-90) ang+=180;
      label(best, s.n, (s.c==='main'||s.c==='bridge')?'':'near', 'translate(-50%,-50%) rotate('+ang.toFixed(1)+'deg) translateY(-12px)');
    }});
    L.polygon(D.plot, {{color:C.deep, weight:1.5, dashArray:'4 4', fillColor:C.iroko, fillOpacity:.22, className:'lm-plot', interactive:false}}).addTo(map);
    L.circleMarker(D.gate, {{radius:4, color:C.bone, weight:1.2, fillColor:C.deep, fillOpacity:1, className:'lm-plot', interactive:false}}).addTo(map);
    label(D.gate, 'Entrance', 'near', 'translate(8px,-50%)');
    var n = 0;
    D.landmarks.forEach(function(Lm){{ var isSite = Lm.id==='site', num = isSite ? '' : String(++n).padStart(2,'0');
      L.marker(Lm.ll, {{icon:L.divIcon({{className:'lm-pin'+(isSite?' lm-site':''), html:'<i>'+num+'</i><b>'+Lm.n+'</b>', iconSize:[0,0]}}), interactive:false, zIndexOffset:isSite?1000:0}}).addTo(map); }});
    return map;
  }}
  var m1 = build('m1', true), m2 = build('c1', false);
  m1.fitBounds(L.latLngBounds(D.landmarks.filter(function(l){{ return l.id!=='airport'; }}).map(function(l){{ return l.ll; }})), {{padding:[44,44]}});
  m2.setView(D.site, 17.5);
  window.__z = [m1.getZoom(), m2.getZoom()];
  window.__tiles = function(){{ var all = document.querySelectorAll('.leaflet-tile'); return all.length > 8 && document.querySelectorAll('.leaflet-tile:not(.leaflet-tile-loaded)').length === 0; }};
}})();
</script></body></html>'''
    path = os.path.join(OUT, 'map.html'); open(path, 'w', encoding='utf-8').write(html)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1100, 'height': 1500}, device_scale_factor=2)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('file://' + path, wait_until='load', timeout=120000)
        pg.wait_for_function('window.__tiles && window.__tiles()', timeout=90000)
        pg.wait_for_function("document.fonts.status === 'loaded'", timeout=60000)
        pg.wait_for_timeout(1500)
        print('map zooms', pg.evaluate('window.__z'), 'errors:', errs or 'none')
        for el_id, name in (('m', 'map-district'), ('c', 'map-street')):
            png = os.path.join(OUT, name + '.png'); pg.locator('#' + el_id).screenshot(path=png)
            Image.open(png).convert('RGB').save(os.path.join(OUT, name + '.jpg'), quality=88, optimize=True); os.remove(png)
        b.close()
if WANT_MAPS or not os.path.exists(os.path.join(OUT, 'map-district.jpg')):
    render_maps()

PRINT_CSS = r"""
@page{size:297mm 210mm;margin:0}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:var(--font-body);font-weight:300;font-size:9pt;line-height:1.5;color:var(--ink);background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}
img{display:block;max-width:100%}
a{color:inherit;text-decoration:none}
ul,ol{margin:0;padding:0;list-style:none}
p{margin:0}
button{font:inherit;color:inherit;background:none;border:0;padding:0}
.sheet{position:relative;width:297mm;height:210mm;overflow:hidden;page-break-after:always;break-after:page;background:var(--bg);color:var(--fg);padding:13mm 15mm 12mm}
.sheet:last-child{page-break-after:auto;break-after:auto}
.foot{position:absolute;left:15mm;right:15mm;bottom:8mm;display:flex;justify-content:space-between;align-items:baseline;padding-top:2mm;border-top:1px solid var(--line);font-size:6.5pt;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);font-weight:500}
.foot b{font-weight:500;color:var(--accent)}
.foot .pn{font-family:var(--font-display);font-size:10pt;letter-spacing:.06em;text-transform:none;color:var(--fg);font-weight:400}
.eyebrow{font-size:7pt;letter-spacing:.26em;margin:0 0 4mm}
.eyebrow .idx{margin-right:.9em}
.title{font-size:24pt;line-height:1.02;margin:0 0 5mm}
.title.sm{font-size:18pt}
.lede{font-size:11pt;line-height:1.4;margin:0 0 4mm;max-width:none}
.body{font-size:8.6pt;line-height:1.6;margin:0 0 3mm;max-width:none}
.body + .body{margin-top:0}
.phead{display:grid;grid-template-columns:1.15fr 1fr;gap:12mm;align-items:end;margin-bottom:6mm}
.phead .title{margin-top:3mm}
.phead .lede{justify-self:end;max-width:none;margin-bottom:0}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12mm;align-items:start}
.stats{margin-top:5mm}
.stat{padding:3.5mm 4mm 3.5mm 0}
.stat .num{font-size:18pt}
.stat .num small{font-size:.42em}
.stat .lab{font-size:6.3pt;margin-top:1.5mm;letter-spacing:.18em}
.also{margin-top:4mm}
.also li{padding:1.8mm 0;font-size:7.8pt;gap:3mm;line-height:1.4}
.also li .num{font-size:13pt;min-width:2.6em}
.facts li{padding:1.9mm 0;gap:3mm;line-height:1.4}
.facts .num{font-size:14pt;min-width:3.2em}
.facts .num small{font-size:6.3pt}
.facts span{font-size:7.9pt}
.drive{margin-top:3mm}
.drive li{padding:1.9mm 0;gap:3mm;line-height:1.4}
.drive .num{font-size:14pt;min-width:2.8em}
.drive .num small{font-size:6.3pt}
.drive span{font-size:7.9pt}
.foot-note{font-size:6.8pt;margin:3mm 0 0;max-width:none}
/* cover */
.sheet.cover{padding:0}
.cov{display:grid;grid-template-columns:1fr 132mm;height:100%}
.covl{position:relative;padding:12mm 12mm 12mm 15mm;display:flex;flex-direction:column;justify-content:flex-end;color:var(--ivory)}
.covr{position:relative;overflow:hidden;background:#0a0b0e}
.covr img{width:100%;height:100%;object-fit:cover;object-position:50% 40%}
.covr::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,var(--ink) 0%,rgba(13,15,18,0) 22%),linear-gradient(0deg,rgba(13,15,18,.55) 0%,rgba(13,15,18,0) 30%)}
.cover .brand{position:absolute;left:15mm;top:11mm;font-family:var(--font-display);font-size:15pt;color:#fff;letter-spacing:.02em}
.cover .brand i{font-style:italic}
.cover .brand b{font-weight:400;color:var(--gold)}
.cover .doc{position:absolute;right:12mm;top:12mm;font-size:6.5pt;letter-spacing:.22em;text-transform:uppercase;color:rgba(243,239,231,.7);text-align:right;line-height:1.8;font-weight:500}
.cover .pre{font-size:7pt;letter-spacing:.26em;text-transform:uppercase;color:var(--gold);font-weight:500;margin:0 0 4mm}
.mark{font-size:54pt;line-height:.9;margin:0 0 5mm;display:flex;align-items:baseline;gap:0 .16em;letter-spacing:-.02em}
.mark .w{font-style:italic;display:inline-block;-webkit-text-fill-color:var(--ivory);color:var(--ivory)}
.mark .n{display:inline-block;background:none;-webkit-background-clip:border-box;background-clip:border-box;-webkit-text-fill-color:var(--gold);color:var(--gold);animation:none;font-variation-settings:"opsz" 36;font-weight:500}
.cover .lightline{height:1px;width:96mm;background:var(--gold);margin:0 0 5mm;box-shadow:0 0 6px rgba(210,174,116,.85)}
.cover-sub{display:block;margin:0 0 5mm}
.cover-sub p{font-size:10.5pt;line-height:1.4;max-width:118mm;color:rgba(243,239,231,.88)}
.cover .stats{grid-template-columns:repeat(4,auto);gap:0;border-top:1px solid rgba(243,239,231,.2);margin-top:2mm}
.cover .stat{padding:3.5mm 5mm 3.5mm 0;border-right:1px solid rgba(243,239,231,.2);margin-right:5mm}
.cover .stat:last-child{border-right:0}
.cover .stat .num{font-size:19pt;color:var(--ivory)}
.cover .stat .lab{color:rgba(243,239,231,.6)}
.creds{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin-top:5mm;padding-top:4mm;border-top:1px solid rgba(243,239,231,.14)}
.cred .k{font-size:6pt;letter-spacing:.22em;margin-bottom:1.2mm}
.cred .v{font-size:8pt;color:var(--ivory)}
.cred .s{font-size:6.8pt;color:#9a9da5;margin-top:.5mm}
.covr .side{position:absolute;right:10mm;bottom:11mm;z-index:2;text-align:right;font-size:6.5pt;letter-spacing:.24em;text-transform:uppercase;color:rgba(243,239,231,.85);font-weight:500}
.covr .side .k{display:block;font-family:var(--font-display);font-size:10pt;letter-spacing:.14em;color:var(--ivory);margin-bottom:1.5mm;font-weight:400}
/* at a glance: the floor stack */
.stackbox{border:1px solid var(--line);border-radius:2mm;background:var(--bg-2);padding:4mm 5mm 4mm}
.sitehead{display:flex;justify-content:space-between;margin-bottom:2mm;font-size:6.5pt;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);font-weight:500}
.stackin{display:grid;grid-template-columns:62mm 1fr;gap:6mm;align-items:start}
.stack-fig{position:static}
.stack-fig svg{width:100%;height:auto;display:block;overflow:visible}
.stack-fig .slab{fill:var(--accent-soft);stroke:var(--line-2);stroke-width:1}
.stack-fig .led{opacity:1;stroke-width:1.6;filter:none}
.stack-fig .lvl-lab{font-size:9px}
.levels{border-top:1px solid var(--line)}
.lvl{display:grid;grid-template-columns:8mm 1fr auto;gap:2.5mm;align-items:baseline;width:100%;text-align:left;padding:2mm 0;border-bottom:1px solid var(--line);font-size:7.6pt}
.lvl::before{display:none}
.lvl .c{font-family:var(--font-display);font-size:10pt;color:var(--accent)}
.lvl .n{font-size:7.8pt;font-weight:400;color:var(--fg)}
.lvl .t{font-size:6pt;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:500;white-space:nowrap}
/* the elevation */
.elevgrid{display:grid;grid-template-columns:76mm 76mm 1fr;gap:7mm;align-items:start}
.fig .img{border-radius:2mm;overflow:hidden;background:var(--bg-2)}
.fig .img img{width:100%;height:auto;aspect-ratio:5/7;object-fit:cover;filter:none}
.fig figcaption{font-size:7pt;margin-top:1.6mm}
.fig figcaption b{font-size:10.5pt}
.fig figcaption i{font-size:6.3pt}
.notes{margin-top:1mm}
.note{padding:2.6mm 0;gap:3mm;grid-template-columns:8mm 1fr}
.note .num{font-size:13pt}
.note h4{font-size:11.5pt;margin:0 0 1mm}
.note p{font-size:7.6pt;line-height:1.5}
/* visualisation plate */
.plate{display:grid;grid-template-columns:126mm 1fr;gap:12mm;align-items:stretch;height:176mm}
.plate .pic{border-radius:2.5mm;overflow:hidden;background:var(--bg-2)}
.plate .pic img{width:100%;height:100%;object-fit:cover}
.plate .txt{display:flex;flex-direction:column;justify-content:flex-end;min-width:0}
.plate .txt .body{color:var(--muted)}
.plate .facts{margin-top:4mm}
/* the residences */
.planpg{display:grid;grid-template-columns:1fr 90mm;gap:9mm;align-items:start}
.pbox{border:1px solid var(--line);border-radius:2mm;background:var(--bg-2);padding:4mm 5mm}
.plan{position:relative;width:150mm;margin:0 auto;aspect-ratio:auto}
.plan img{position:static;width:100%;height:auto;object-fit:fill}
.plan .mk{opacity:1;width:4mm;height:4mm;font-size:5.6pt;transition:none;transform:translate(-50%,-50%)}
.plan .mk::before{inset:.3mm;box-shadow:0 0 0 .3mm var(--bg-2)}
.plan .mk .tip{display:none}
.plan .north{width:8mm;height:8mm;right:1mm;top:1mm}
.pcap{display:flex;justify-content:space-between;margin-top:2mm;font-size:6.5pt;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);font-weight:500}
.legend{display:block;columns:2;column-gap:5mm}
.legend .lg{break-inside:avoid;margin-bottom:2.5mm}
.legend h4{font-size:6.3pt;letter-spacing:.22em;margin:0 0 1mm}
.legend li{grid-template-columns:4.6mm 1fr;gap:1.8mm;padding:.7mm 0;font-size:6.7pt;line-height:1.3}
.legend li .ln{width:3.8mm;height:3.8mm;font-size:5.4pt}
.legend li .ln::before{inset:.3mm}
.rcards{display:grid;grid-template-columns:repeat(3,1fr);gap:7mm;margin-top:4mm}
.rcard{border-top:1px solid var(--line-2);padding-top:2.5mm}
.rcard .rh{margin-bottom:1.2mm;gap:3mm}
.rcard h3{font-size:12pt}
.rcard .rt{font-size:6.2pt;letter-spacing:.18em}
.rcard .rsum{font-size:7pt;line-height:1.45;min-height:0;margin:0 0 1.2mm}
.rlist li{font-size:6.8pt;color:var(--muted);padding:.55mm 0;border-top:1px solid var(--line);line-height:1.3}
.rlist li b{color:var(--fg);font-weight:400}
/* seven views */
.vgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:5mm;margin-top:1mm}
.vgrid .vt{display:flex;flex-direction:column;justify-content:flex-end;padding-bottom:6mm}
.vgrid .fig .img img{aspect-ratio:auto;height:76mm}
/* section and levels */
.secgrid{display:grid;grid-template-columns:150mm 1fr;gap:12mm;align-items:start}
.secbox{border:1px solid var(--line);border-radius:2mm;background:var(--bg-2);padding:4mm 5mm 3mm;margin-bottom:4mm}
.secbox img{width:100%;height:auto}
.lvlist{margin-top:2mm}
.lvrow{display:grid;grid-template-columns:9mm 1fr;gap:3mm;padding:1.5mm 0;border-top:1px solid var(--line);font-size:6.8pt;line-height:1.38;color:var(--muted)}
.lvrow:last-child{border-bottom:1px solid var(--line)}
.lvrow .c{font-family:var(--font-display);font-size:10pt;color:var(--accent)}
.lvrow b{font-weight:400;color:var(--fg)}
.lvrow i{font-style:normal;font-size:6pt;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-left:1.5mm;font-weight:500}
/* site */
.sitegridp{display:grid;grid-template-columns:128mm 1fr;gap:11mm;align-items:start}
.siteplan{padding:3mm 4mm 2mm;border-radius:2mm;overflow:visible}
.siteplan svg{width:100%;height:auto;display:block;overflow:visible}
.sp-hot,.sp-route,.sp-route-dot{display:none}
.sp-tree{transform:none}
.skeys{border-top:1px solid var(--line)}
.skeys li{border-bottom:1px solid var(--line)}
.skey{grid-template-columns:5mm 1fr auto;gap:2.5mm;padding:1.7mm 0;font-size:7.4pt;line-height:1.4;align-items:baseline}
.skey .k{width:3.8mm;height:3.8mm;font-size:5.4pt;align-self:center}
.skey .k::before{inset:.3mm}
.skey b{color:var(--fg);font-weight:400}
.skey .a{font-family:var(--font-display);font-size:9pt;color:var(--fg);white-space:nowrap}
.reachh{font-family:var(--font-display);font-weight:400;font-size:16pt;line-height:1.05;margin:5mm 0 2mm}
/* the neighbourhood */
.mapgrid{display:grid;grid-template-columns:1fr 78mm;gap:10mm;align-items:start}
.mapframe{position:relative;border-radius:2.5mm;overflow:hidden;border:1px solid var(--line);background:#ebe6db;height:176mm}
.mapframe img.main{width:100%;height:100%;object-fit:cover}
.mapframe .inset{position:absolute;right:5mm;bottom:5mm;width:54mm;height:54mm;border-radius:2mm;overflow:hidden;border:1.5px solid var(--ivory);box-shadow:0 4mm 12mm rgba(13,15,18,.4)}
.mapframe .inset img{width:100%;height:100%;object-fit:cover}
.mapframe .inset span{position:absolute;left:0;right:0;bottom:0;padding:1.5mm 2.5mm;background:rgba(13,15,18,.82);color:var(--ivory);font-size:6pt;letter-spacing:.2em;text-transform:uppercase;font-weight:500}
.mapcap{position:absolute;left:3mm;bottom:3mm;font-size:6pt;letter-spacing:.08em;color:#0d0f12;background:rgba(243,239,231,.88);padding:1mm 2mm;border-radius:1mm}
.lmlist{margin-top:1mm}
.lmlist .g{display:flex;justify-content:space-between;align-items:baseline;font-size:6.2pt;letter-spacing:.24em;text-transform:uppercase;color:var(--muted);padding:2.4mm 0 .8mm;font-weight:500}
.lmlist .g b{font-family:var(--font-display);font-size:9.5pt;font-weight:400;letter-spacing:.02em;text-transform:none;color:var(--fg)}
.lmlist .g b small{font-family:var(--font-body);font-size:6pt;letter-spacing:.08em;color:var(--muted);margin-left:1mm}
.lmrow{display:grid;grid-template-columns:5.5mm 1fr auto;gap:2.5mm;align-items:center;padding:1.1mm 0;border-top:1px solid var(--line);font-size:7.6pt;line-height:1.3}
.lmrow .i{width:5mm;height:5mm;border-radius:50%;background:var(--ink);color:var(--ivory);border:1px solid var(--ivory);font:500 5.4pt/4.6mm var(--font-body);text-align:center;letter-spacing:.04em}
.lmrow.site .i{background:var(--gold-deep)}
.lmrow .t small{display:block;font-size:6.2pt;color:var(--muted);line-height:1.3;margin-top:.2mm}
.lmrow .d{font-family:var(--font-display);font-size:10pt;white-space:nowrap}
.lmrow .d small{font-family:var(--font-body);font-size:6pt;color:var(--muted);margin-left:.5mm}
/* specification */
.spec{margin-top:0;display:grid;grid-template-columns:1fr 1fr;gap:2mm 12mm}
.spec-group{padding:3mm 0 2mm}
.spec-group h4{font-size:6.5pt;margin:0 0 1.5mm}
.spec-row{grid-template-columns:24mm 1fr;gap:3mm;padding:1.6mm 0;font-size:7.4pt}
.spec-row dd{line-height:1.5}
/* closing */
.close .big{font-size:36pt;line-height:.96;margin:2mm 0 4mm}
.close-grid{grid-template-columns:1fr 1fr 1.25fr;gap:10mm;margin-top:5mm;padding-top:4mm}
.close-grid h4{font-size:6.5pt;letter-spacing:.24em;margin:0 0 2mm}
.closetop{display:grid;grid-template-columns:1fr 1fr;gap:12mm;align-items:center}
.close .frame{border-radius:2.5mm;overflow:hidden;aspect-ratio:16/7;position:relative;background:var(--bg-2)}
.close .frame img{width:100%;height:100%;object-fit:cover;object-position:50% 45%}
.close .lede{font-size:10.5pt;color:rgba(243,239,231,.85)}
.toc li a{grid-template-columns:9mm 1fr;padding:1.1mm 0;font-size:7.5pt}
.toc li a .num{font-size:9.5pt}
.who{font-size:8pt;line-height:1.55}
.who + .who{margin-top:2mm}
.contact a{display:flex;justify-content:space-between;align-items:center;gap:3mm;padding:1.4mm 0;font-size:8pt}
.contact .v{font-family:var(--font-display);font-size:11pt;line-height:1.1}
.contact .chip{display:inline-flex;align-items:center;gap:1.5mm;font-size:6pt;letter-spacing:.2em;text-transform:uppercase;font-weight:500;padding:1.4mm 2.6mm;border:1px solid var(--line-2);border-radius:999px;color:var(--muted)}
.contact .chip svg{width:3mm;height:3mm;fill:none;stroke:currentColor;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.disc{font-size:6.3pt;margin:4mm 0 0;max-width:none;line-height:1.45}
"""

def sheet(n, tone, cls, inner):
    foot = f'<div class="foot"><span><b>Heights 777</b> · Plot 777 CAD Zone A07 · Parakou Street · Wuse II</span><span class="pn">{n:02d} / {N}</span></div>' if n > 1 else ''
    return f'<section class="sheet {cls}" data-tone="{tone}">{inner}{foot}</section>'
def eyebrow(idx, text): return f'<p class="eyebrow"><span class="idx">{idx}</span>{text}</p>'

S1 = f'''<div class="cov">
  <div class="covl">
    <div class="brand"><i>Heights</i> <b>777</b></div>
    <div class="doc">Proposed residential development<br>Plot 777 CAD Zone A07 · Wuse II · Abuja FCT</div>
    <p class="pre">Parakou Street · Wuse II</p>
    <h1 class="mark"><span class="w">Heights</span><span class="n">777</span></h1>
    <div class="lightline"></div>
    <div class="cover-sub"><p>Eighteen residences, seven storeys, one quiet street in Wuse II. Curved white slabs edged in light, three residences to a floor, and two penthouse floors to the west.</p></div>
    <ul class="stats">
      <li class="stat"><div class="num">07</div><div class="lab">Storeys</div></li>
      <li class="stat"><div class="num">18</div><div class="lab">Residences</div></li>
      <li class="stat"><div class="num">1–2</div><div class="lab">Bedrooms</div></li>
      <li class="stat"><div class="num">21</div><div class="lab">Parking bays</div></li>
    </ul>
    <div class="creds">
      <div class="cred"><div class="k">Development</div><div class="v">Wrace Group</div><div class="s">Heights 777 · Plot 777, Wuse II</div></div>
      <div class="cred"><div class="k">Architect</div><div class="v">A365 Designs</div><div class="s">Abuja, FCT · Drawings dated October 2025</div></div>
      <div class="cred"><div class="k">Document</div><div class="v">Compiled by Mizan Qist Limited</div><div class="s">2026 · Confidential</div></div>
    </div>
  </div>
  <div class="covr"><img src="{R['corner-dusk']}" alt=""><div class="side"><span class="k">01 / {N}</span>Corner at dusk · visualisation</div></div>
</div>'''

S2 = f'''<div class="two" style="grid-template-columns:1fr 1.05fr;gap:12mm">
  <div>
    {eyebrow('02', 'At a glance')}
    <h2 class="title">Seven storeys of soft white lines, <em>edged in light.</em></h2>
    <p class="lede">Heights 777 is a seven-storey residential building on Parakou Street, in the heart of Wuse II. Eighteen one- and two-bedroom residences occupy six floors above a covered parking level, served by two lifts and three stairs.</p>
    <p class="body">Every residence opens onto a planted balcony behind a frameless glass balustrade, and every slab edge carries a continuous strip of warm light. The building reads at dusk the way it reads at noon: a stack of curved white trays, floating off a charcoal core.</p>
    <p class="body">Interiors are finished to a single standard throughout: <strong>polished granite</strong> in living rooms and lobbies, vitrified tile in bedrooms, full-height glass sliding doors onto the balconies, and composite pivot security doors at every entrance.</p>
    <ul class="stats">
      <li class="stat"><div class="num">1,136<small>m²</small></div><div class="lab">Site area</div></li>
      <li class="stat"><div class="num">514<small>m²</small></div><div class="lab">Building footprint</div></li>
      <li class="stat"><div class="num">46<small>%</small></div><div class="lab">Built · 54% open</div></li>
      <li class="stat"><div class="num">3.15<small>m</small></div><div class="lab">Floor to floor</div></li>
    </ul>
    <ul class="also">
      <li><span class="num">21</span><span><b>Parking bays</b> on the plot, beneath the building and along its edges</span></li>
      <li><span class="num">13<small style="font-size:6.3pt;color:var(--muted)"> m²</small></span><span><b>Gate house</b> on the Parakou Street frontage, with a screened entrance</span></li>
      <li><span class="num">2 + 3</span><span><b>Two lifts and three stairs</b>: a lift and main stair at each end of the lobby, and a back stair by the courtyard</span></li>
      <li><span class="num">23.5<small style="font-size:6.3pt;color:var(--muted)"> m</small></span><span><b>Parapet height</b> above the ground-floor slab</span></li>
    </ul>
  </div>
  <div>
    <div class="stackbox"><div class="sitehead"><span>The floor stack · eight levels</span><span>Not to scale</span></div>
      <div class="stackin"><div class="stack-fig"><svg viewBox="0 0 300 520" id="stacksvg"></svg></div><div><ol class="levels" id="levels"></ol><p class="foot-note" style="margin-top:3mm">Three residences on every floor from 01 to 06. The west wing of floors 05 and 06 is a one-bedroom penthouse; on the sixth floor its lounge opens onto a private infinity pool. Each level is described on sheet 08.</p></div></div>
    </div>
  </div>
</div>'''

S3 = f'''<div class="phead">
  <div>{eyebrow('03', 'The elevation')}<h2 class="title">Drawn twice: once by the sun, <em>once by its own light.</em></h2></div>
  <p class="lede">The same arrival view under two skies: at noon, and at dusk when the slab edges take over from the daylight.</p>
</div>
<div class="elevgrid">
  <figure class="fig"><div class="img"><img src="{R['entrance-day']}" alt=""></div><figcaption><span><b>Noon</b></span><i>Arrival · visualisation 05</i></figcaption></figure>
  <figure class="fig"><div class="img"><img src="{R['entrance-dusk']}" alt=""></div><figcaption><span><b>Dusk</b></span><i>Arrival · visualisation 04</i></figcaption></figure>
  <div>
    <p class="body">The plan is simple: three residences to a floor, two lift cores between them, and balconies wrapping the corners. The elevation makes that plan legible. Each floor is a single white slab with rounded ends. The glazing sits well back from the slab edge, so the trays read as continuous, and the planting on every balcony softens the line without breaking it.</p>
    <ol class="notes">
      <li class="note"><span class="num">01</span><div><h4>Curved slab edges</h4><p>Every balcony slab rounds its corners and carries a recessed LED strip along its full length. At dusk the building is outlined floor by floor, with no visible fittings.</p></div></li>
      <li class="note"><span class="num">02</span><div><h4>Glass, set back and planted</h4><p>Floor-to-ceiling glazing behind frameless glass balustrades. Planters run along the balcony edge on every floor, so the greenery of the street continues up the building.</p></div></li>
      <li class="note"><span class="num">03</span><div><h4>A charcoal core</h4><p>The lift and stair cores are clad dark, with a tall fluted glass panel and slender vertical light lines. Against it, the white wings appear to float.</p></div></li>
    </ol>
  </div>
</div>'''

def plate(img, idx, view, title, paras, facts):
    ps = ''.join(f'<p class="body">{p}</p>' for p in paras)
    fs = ''.join(f'<li><span class="num">{v}<small>{u}</small></span><span>{t}</span></li>' for v, u, t in facts)
    return f'''<div class="plate"><div class="pic"><img src="{img}" alt=""></div>
<div class="txt">{eyebrow(idx, 'Visualisation · ' + view)}<h2 class="title sm">{title}</h2>{ps}<ul class="facts">{fs}</ul></div></div>'''

S4 = plate(R['balconies-aerial'], '04', '06 / 07', 'The balconies from above, <em>planted on every floor.</em>',
    ['Looking down the front of the building, the slabs stack as a run of curved white trays. Each carries a planter along its edge and a frameless glass balustrade behind it, so the greenery of Parakou Street continues up all six residential floors.',
     'The glazing sits well back from the edge. From the street the balconies read as one continuous line per floor; from the rooms, the planting frames the view without interrupting it.'],
    [('18', '', '<b>Balconies</b>, front and rear, one pair to every residence'), ('3.15', 'm', '<b>Floor to floor</b> on every level'), ('23.5', 'm', '<b>Parapet height</b> above the ground-floor slab')])

def rcard(h, rt, sum_, items):
    li = ''.join(f'<li>{x}</li>' for x in items)
    return f'<article class="rcard"><div class="rh"><h3>{h}</h3><span class="rt">{rt}</span></div><p class="rsum">{sum_}</p><ul class="rlist">{li}</ul></article>'

def plan_sheet(idx, floor, img, title, lede, cap, cards):
    return f'''<div class="phead" style="margin-bottom:3mm">
  <div>{eyebrow(idx, 'The residences')}<h2 class="title sm">{title}</h2></div>
  <p class="lede" style="font-size:9.5pt">{lede}</p>
</div>
<div class="planpg">
  <div>
    <div class="pbox"><div class="plan" data-floor="{floor}"><img src="{img}" alt=""><div class="labs"></div><div class="north"><svg viewBox="0 0 34 34"><circle cx="17" cy="17" r="15"/><path d="M17 5l4 12-4-3-4 3z"/><text x="17" y="30" text-anchor="middle">N</text></svg></div></div><div class="pcap"><span>{cap}</span><span>North to the top · Parakou Street along the bottom edge</span></div></div>
    <div class="rcards">{''.join(cards)}</div>
  </div>
  <div class="legend" data-floor="{floor}"></div>
</div>'''

CARD_W = rcard('West residence', 'Two bedrooms', 'The largest of the three, wrapping the north-west corner. The living room and a separate kitchen open onto the deepest of the front balconies; both bedrooms have their own dressing room and bath.', ['<b>Living room</b>', '<b>Kitchen</b>, separate, with its own balcony', '<b>Bedroom 1</b> with dressing room and bath', '<b>Bedroom 2</b> with dressing room and bath', '<b>Entrance lobby</b> and guest WC', '<b>Balconies</b>, front and rear'])
CARD_C = rcard('Centre residence', 'Two bedrooms', 'Entered from the main lobby beside the lift. The living room faces the street; the kitchen and both bedrooms sit along the quiet rear elevation, each with its own balcony.', ['<b>Living room</b>, facing the street', '<b>Kitchen</b>, on the rear elevation', '<b>Bedroom 1</b> with dressing room and bath', '<b>Bedroom 2</b> with dressing room and bath', '<b>Entrance lobby</b> and guest WC', '<b>Balconies</b>, front and rear'])
CARD_E = rcard('East residence', 'Two bedrooms', 'Mirrors the west plan at the north-east corner. A living room with a deep front balcony, a separate kitchen, and two bedrooms of equal standing, each with a dressing room and bath.', ['<b>Living room</b>', '<b>Kitchen</b>, separate, with its own balcony', '<b>Bedroom 1</b> with dressing room and bath', '<b>Bedroom 2</b> with dressing room and bath', '<b>Entrance lobby</b> and guest WC', '<b>Balconies</b>, front and rear'])
CARD_P = rcard('West penthouse', 'One bedroom · pool', 'The west wing reconfigured: a living room, a bedroom suite, a small kitchen and a second, larger lounge that opens, on the top floor, onto a private infinity pool at the corner of the building.', ['<b>Living room</b>', '<b>Lounge</b>, with the infinity pool on the top floor', '<b>Kitchen</b>', '<b>Bedroom suite</b> with dressing room and bath', '<b>Entrance lobby</b> and guest WC', '<b>Balconies</b>, front and rear'])
CARD_CE = rcard('Centre and east residences', 'Two bedrooms each', 'On the upper floors the centre and east residences keep the typical plan: a street-facing living room and a rear kitchen at the centre, and the mirrored corner residence to the east, every bedroom with its dressing room and bath.', ['<b>Living rooms</b> on the front elevation', '<b>Kitchens</b>, separate', '<b>Two bedrooms</b> each, with dressing rooms and baths', '<b>Entrance lobbies</b> and guest WCs', '<b>Balconies</b>, front and rear'])
CARD_6 = rcard('The sixth floor', 'Crowning level', 'The crowning floor: the west penthouse with its lounge opening onto a private infinity pool at the corner, and two two-bedroom residences at the centre and east.', ['<b>Infinity pool</b> at the north-west corner', '<b>Lounge</b> opening onto the pool', '<b>Roof slab</b> at +22.05 m · parapet at +23.55 m'])

S5 = plan_sheet('05', 'typical', PLAN_T, 'Three to a floor. Every bedroom with its own <em>dressing room and bath.</em>',
    'Sixteen two-bedroom residences fill floors 01 to 06: west, centre and east around two lift cores, each with a guest WC and balconies front and rear. The numbered markers sit where the rooms are labelled on the drawings.',
    'Typical floor · 01 – 04', [CARD_W, CARD_C, CARD_E])
S6 = plan_sheet('06', 'upper', PLAN_U, 'The upper floors: <em>a penthouse to the west, a pool on top.</em>',
    'On floors 05 and 06 the west wing becomes a one-bedroom penthouse with a second lounge and, on the crowning floor, a private infinity pool at the corner of the building. The centre and east residences keep the typical plan.',
    'Upper floors · 05 – 06', [CARD_P, CARD_CE, CARD_6])

def vfig(name, b, i): return f'<figure class="fig"><div class="img"><img src="{R[name]}" alt=""></div><figcaption><span><b>{b}</b></span><i>{i}</i></figcaption></figure>'
S7 = f'''<div class="vgrid">
  <div class="vt">{eyebrow('07', 'Visualisations')}<h2 class="title sm">Seven views, <em>two skies.</em></h2><p class="body">The front elevation under overcast and clear skies, the corner at dusk, the arrival by day and by night, the balconies from above and the approach along the street. Artists’ impressions; finishes and planting indicative.</p></div>
  {vfig('front-overcast', 'Front elevation', 'Overcast · 01')}
  {vfig('front-clear', 'Front elevation', 'Clear sky · 02')}
  {vfig('corner-dusk', 'Corner', 'Dusk · 03')}
  {vfig('entrance-dusk', 'Arrival', 'Dusk · 04')}
  {vfig('entrance-day', 'Arrival', 'Noon · 05')}
  {vfig('balconies-aerial', 'Balconies', 'From above · 06')}
  {vfig('street-day', 'Street approach', 'Day · 07')}
</div>'''

S8 = f'''<div class="secgrid">
  <div>
    {eyebrow('08', 'Section A–A · through the lift core')}
    <h2 class="title">Six floors of living <em>over one of arrival.</em></h2>
    <div class="secbox"><div class="sitehead"><span>Long section · the lifts and stairs at the centre</span><span>From the drawings of October 2025</span></div><img src="{SECTION}" alt=""></div>
    <ul class="facts">
      <li><span class="num">3.15<small>m</small></span><span><b>Floor to floor</b>, every level, with 350 mm reinforced-concrete beams</span></li>
      <li><span class="num">0.45<small>m</small></span><span><b>Ground level</b> sits this far below the parking slab; the first residences begin at +3.15 m</span></li>
      <li><span class="num">22.05<small>m</small></span><span><b>Roof slab</b>, with a PU-insulated longspan aluminium roof on a steel truss above</span></li>
      <li><span class="num">2 + 3</span><span><b>Two lifts, three stairs</b>: a core at each end of the lobby, and a back stair beside the courtyard</span></li>
    </ul>
  </div>
  <div>
    <p class="eyebrow" style="margin-top:14mm"><span class="idx">Level by level</span>Roof to ground</p>
    <div class="lvlist" id="lvlist"></div>
  </div>
</div>'''

S9 = f'''<div class="phead" style="margin-bottom:5mm">
  <div>{eyebrow('09', 'Location')}<h2 class="title">Wuse II, on a street that <em>stays quiet.</em></h2></div>
  <p class="lede">Parakou Street runs through the residential heart of Wuse II, a few minutes from the restaurants and shops of Aminu Kano Crescent, with Maitama to the north and the Central Business District to the south-east. The plot fronts the street along its full southern edge; drawn here in metres from the site plan sheet.</p>
</div>
<div class="sitegridp">
  <div>
    <div class="siteplan" id="siteplan"><svg id="sitesvg" viewBox="-3 -3.6 48 40.6"></svg><button id="routebtn" hidden></button><button id="duskbtn" hidden></button></div>
    <p class="foot-note">Indicative, redrawn from site plan sheet A101 (1:150, October 2025). Bay positions are approximate; the plot, the building footprint and the gate house are shown as on the sheet.</p>
  </div>
  <div>
    {skeys_html}
    <h3 class="reachh">Between Maitama and the city.</h3>
    <ul class="drive">
      <li><span class="num">5<small>min</small></span><span><b>Maitama</b>, across Aminu Kano Crescent: embassies, Transcorp Hilton, banks</span></li>
      <li><span class="num">10<small>min</small></span><span><b>Central Business District</b>, Wuse Market and Banex Plaza</span></li>
      <li><span class="num">15<small>min</small></span><span><b>Jabi Lake Mall</b> and the Jabi lakefront</span></li>
      <li><span class="num">40<small>min</small></span><span><b>Nnamdi Azikiwe International Airport</b> by the airport road</span></li>
    </ul>
    <p class="foot-note">Drive times are approximate and off-peak.</p>
  </div>
</div>'''

GROUPS = {'street': ('The street', ''), 'maitama': ('Maitama', '5'), 'city': ('The city', '10'), 'jabi': ('Jabi', '15'), 'airport': ('The airport', '40')}
rows, last, n = [], None, 0
for Lm in mapdata['landmarks']:
    if Lm['g'] != last:
        last = Lm['g']; gname, gt = GROUPS[Lm['g']]
        rows.append(f'<div class="g"><span>{gname}</span>' + (f'<b>{gt}<small>min</small></b>' if gt else '') + '</div>')
    is_site = Lm['id'] == 'site'; num = '' if is_site else f'{(n := n + 1):02d}'
    dist = '<span class="d">1,136<small>m²</small></span>' if is_site else f'<span class="d">{Lm["km"]:.1f}<small>km</small></span>'
    rows.append(f'<div class="lmrow{" site" if is_site else ""}"><span class="i">{num}</span><span class="t"><b>{Lm["n"]}</b><small>{Lm["s"]}</small></span>{dist}</div>')
S10 = f'''<div class="mapgrid">
  <div class="mapframe"><img class="main" src="map-district.jpg" alt=""><div class="inset"><img src="map-street.jpg" alt=""><span>Parakou Street · the entrance</span></div><div class="mapcap">Map © OpenStreetMap contributors</div></div>
  <div>
    {eyebrow('10', 'The neighbourhood')}
    <h2 class="title sm">The street, the district, <em>and every place named here.</em></h2>
    <p class="body">The plot and the landmarks of the previous page on the map of Abuja, with rings at one, two and five kilometres from the gate; the inset shows Parakou Street itself and the entrance.</p>
    <div class="lmlist">{''.join(rows)}</div>
    <p class="foot-note" style="margin-top:2mm">Road distances from the gate by OpenStreetMap routing; drive times approximate and off-peak; plot outline indicative. The street appears on some maps as Parakou Crescent.</p>
  </div>
</div>'''

S11 = f'''<div class="phead" style="margin-bottom:5mm">
  <div>{eyebrow('11', 'Specification')}<h2 class="title">One standard, <em>every floor.</em></h2></div>
  <p class="lede">Finishes and systems as set out in the architectural drawings and schedules of October 2025. Selections shown in the visualisations are indicative of quality and tone.</p>
</div>
{spec_html}
<ul class="stats" style="margin-top:8mm;padding-top:0">
  <li class="stat"><div class="num">1,136<small>m²</small></div><div class="lab">Site area</div></li>
  <li class="stat"><div class="num">514<small>m²</small></div><div class="lab">Building footprint</div></li>
  <li class="stat"><div class="num">21</div><div class="lab">Parking bays</div></li>
  <li class="stat"><div class="num">2 + 3</div><div class="lab">Lifts · stairs</div></li>
</ul>'''

S12 = f'''{eyebrow('12', 'Next step')}
<div class="closetop">
  <div>
    <h2 class="big">Reserve a <em>residence.</em></h2>
    <p class="lede">Eighteen residences across six floors, three to a floor, with the two penthouse floors to the west. Plans, areas and the specification are settled at design stage; the drawings are available on request.</p>
    <p class="body" style="color:#9a9da5">Every residence is entered from a lift lobby, and every bedroom has its own dressing room and bath. A walk-through of the drawings and a visit to the plot can be arranged through Mizan Qist.</p>
  </div>
  <div class="frame"><img src="{R['front-overcast']}" alt=""></div>
</div>
<div class="close-grid">
  <div><h4>In this document</h4><ol class="toc">
    <li><a><span class="num">02</span><span>At a glance · the floor stack</span></a></li>
    <li><a><span class="num">03</span><span>The elevation · noon to dusk</span></a></li>
    <li><a><span class="num">05</span><span>The residences · plans</span></a></li>
    <li><a><span class="num">07</span><span>Visualisations</span></a></li>
    <li><a><span class="num">08</span><span>Section · level by level</span></a></li>
    <li><a><span class="num">09</span><span>Location · site plan</span></a></li>
    <li><a><span class="num">10</span><span>The neighbourhood · map</span></a></li>
    <li><a><span class="num">11</span><span>Specification</span></a></li>
  </ol></div>
  <div><h4>Project</h4>
    <p class="who"><b>Heights 777</b>Plot 777, CAD Zone A07<br>Parakou Street, Wuse II, Abuja FCT</p>
    <p class="who"><b>Development</b>Wrace Group</p>
    <p class="who"><b>Architect</b>A365 Designs<br>Drawings dated October 2025</p>
    <p class="who"><b>Web brochure</b>mizanqist.github.io/heights-777</p></div>
  <div><h4>Enquiries</h4><p class="who"><b>Mizan Qist Limited</b>Document compiled 2026</p>{contact_html}</div>
</div>
<p class="disc">The information in this brochure has been prepared with care from the architectural drawings dated October 2025 and the visualisations supplied for the project. Visualisations are artists' impressions. Areas are indicative and measured from the drawings; layouts, finishes, planting and lighting remain subject to final design, statutory approvals and construction. Map data © OpenStreetMap contributors. Nothing here forms part of an offer or contract.</p>'''

sheets = [sheet(1, 'dark', 'cover', S1), sheet(2, 'light', '', S2), sheet(3, 'dark', '', S3), sheet(4, 'dark', '', S4), sheet(5, 'light', '', S5), sheet(6, 'light', '', S6),
          sheet(7, 'dark', '', S7), sheet(8, 'light', '', S8), sheet(9, 'light', '', S9), sheet(10, 'dark', '', S10), sheet(11, 'light', '', S11), sheet(12, 'dark', 'close', S12)]
assert len(sheets) == N

PRINT_JS = r"""
(function(){
  var d = document;
  var $ = function(s, c){ return (c||d).querySelector(s); };
  var $$ = function(s, c){ return Array.prototype.slice.call((c||d).querySelectorAll(s)); };
""" + levels_js + """
  var svg = $('#stacksvg'), list = $('#levels');
""" + stack_js + """
  var lv = $('#lvlist');
  LEVELS.forEach(function(L){ var r = d.createElement('div'); r.className = 'lvrow'; r.innerHTML = '<span class="c">'+L.code+'</span><span><b>'+L.h+'</b><i>'+L.sub+'</i><br>'+L.text+'</span>'; lv.appendChild(r); });
""" + rooms_js + """
  $$('.plan[data-floor]').forEach(function(pl){
    var f = pl.dataset.floor, labs = $('.labs', pl), lg = $('.legend[data-floor="'+f+'"]'), k = 0;
    ROOMS[f].forEach(function(grp){
      var box = d.createElement('div'); box.className = 'lg'; box.innerHTML = '<h4>'+grp.g+'</h4><ul></ul>'; var ul = box.querySelector('ul');
      grp.r.forEach(function(r){ k++; var m = d.createElement('span'); m.className = 'mk on'; m.style.left = r[1]+'%'; m.style.top = r[2]+'%'; m.innerHTML = '<span>'+k+'</span>'; labs.appendChild(m);
        var li = d.createElement('li'); li.innerHTML = '<span class="ln">'+k+'</span><span>'+r[0]+'</span>'; ul.appendChild(li); });
      lg.appendChild(box);
    });
  });
""" + site_js + """
  window.__ready = true;
})();
"""

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Heights 777 · Brochure</title>
{fonts}
<style>
{tokens}
{tone_d}
{tone_l}
{chr(10).join(rules)}
{PRINT_CSS}
</style></head><body>
{''.join(sheets)}
<script>{PRINT_JS}</script>
</body></html>"""
html_path = os.path.join(OUT, 'print.html')
open(html_path, 'w', encoding='utf-8').write(html)
print('print.html written:', len(html)//1024, 'KB')

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1123, 'height': 794})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('file://' + html_path, wait_until='load', timeout=120000)
    pg.wait_for_function("window.__ready === true && document.fonts.status === 'loaded'", timeout=60000)
    pg.wait_for_function('Array.from(document.images).every(i => i.complete)', timeout=60000)
    pg.wait_for_timeout(800)
    pg.emulate_media(media='print')
    pg.pdf(path=PDF, prefer_css_page_size=True, print_background=True, width='297mm', height='210mm', margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
    print('page errors:', errs or 'none')
    b.close()
print('pdf:', PDF, os.path.getsize(PDF)//1024, 'KB')
