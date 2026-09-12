#!/usr/bin/env python3
"""Build assets/map-data.js for the Heights 777 brochure map.
Run from anywhere:  python3 tools/map/build_data.py
Sources: OSM street geometry in streets.json / far.json (fetched with op.py, an Overpass helper:
python3 op.py <name> '<overpass query>'), OSRM demo-server driving routes fetched with curl at
build time, plot outline from site plan sheet A101 (41.5 x 28 m, fronting the street)."""
import json, math, subprocess, time, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'assets', 'map-data.js')
LAT0 = 9.079
M_LAT = 1/111320.0
M_LON = 1/(111320.0*math.cos(math.radians(LAT0)))

def load(n):
    p = os.path.join(HERE, n)
    return json.load(open(p))['elements'] if os.path.exists(p) else []
elements = load('streets.json') + load('far.json') + load('near.json')
byid = {e['id']: e for e in elements if e['type'] == 'way' and 'geometry' in e}
def geom(wid): return [(p['lat'], p['lon']) for p in byid[wid]['geometry']]

def dp(pts, tol):
    if len(pts) < 3: return pts
    def d(p, a, b):
        ax, ay = (a[1]-p[1])/M_LON, (a[0]-p[0])/M_LAT
        bx, by = (b[1]-a[1])/M_LON, (b[0]-a[0])/M_LAT
        L2 = bx*bx+by*by
        if L2 == 0: return math.hypot(ax, ay)
        t = max(0, min(1, -(ax*bx+ay*by)/L2))
        return math.hypot(ax+t*bx, ay+t*by)
    imax, dmax = 0, 0
    for i in range(1, len(pts)-1):
        dd = d(pts[i], pts[0], pts[-1])
        if dd > dmax: imax, dmax = i, dd
    if dmax > tol:
        return dp(pts[:imax+1], tol)[:-1] + dp(pts[imax:], tol)
    return [pts[0], pts[-1]]
def r5(pts): return [[round(a,5), round(b,5)] for a,b in pts]
def ways_named(name, pred=lambda e: True):
    return [e['id'] for e in elements if e['type']=='way' and e.get('tags',{}).get('name')==name and 'geometry' in e and pred(e)]

STREETS = [
  ('parakou',   'Parakou Street',              'close',  1, ways_named('Parakou Crescent')),
  ('aminu',     'Aminu Kano Crescent',         'main',   4, ways_named('Aminu Kano Crescent')),
  ('adetok',    'Adetokunbo Ademola Crescent', 'local',  4, ways_named('Adetokunbo Ademola Crescent')),
  ('herbert',   'Herbert Macaulay Way',        'main',   5, ways_named('Herbert Macaulay Way')),
  ('shehu',     'Shehu Shagari Way',           'main',   5, ways_named('Shehu Shagari Way')),
  ('ahmadu',    'Ahmadu Bello Way',            'main',   6, ways_named('Ahmadu Bello Way')),
  ('constitution', 'Constitution Avenue',      'main',   6, ways_named('Constitution Avenue', lambda e: e['tags'].get('highway') != 'construction')),
  ('nnamdi',    'Nnamdi Azikiwe Expressway',   'main',   8, ways_named('Nnamdi Azikiwe Expressway')),
  ('umaru',     'Umaru Musa Yar’Adua Expressway', 'main', 8, ways_named("Umaru Musa Yar'Adua Expressway")),
]
street_out = []
for key, label, cls, tol, ids in STREETS:
    segs = [r5(dp(geom(w), tol)) for w in ids]
    print(f'{key:12s} {len(ids):2d} ways -> {sum(len(s) for s in segs)} pts')
    street_out.append({'k': key, 'n': label, 'c': cls, 's': segs})

def nearest_on(ids, lat, lon):
    best, bd = None, 1e9
    for w in ids:
        for p in geom(w):
            dd = math.hypot((p[0]-lat)/M_LAT, (p[1]-lon)/M_LON)
            if dd < bd: best, bd = p, dd
    return best

# ---- the plot (indicative): 41.5 m of frontage on the north-east side of the crescent's straight north-west leg,
# 28 m deep, drawn parallel to the road as on sheet A101 (north up there, the street along the bottom edge)
A = (9.0803829, 7.4663499); B = (9.0792790, 7.4681534)          # the straight leg, north-west to south-east
mid = ((A[0]+B[0])/2, (A[1]+B[1])/2)
dx, dy = (B[1]-A[1])/M_LON, (B[0]-A[0])/M_LAT                     # metres east, north
L = math.hypot(dx, dy); u = (dx/L, dy/L); nrm = (-u[1], u[0])     # u along the road (to the south-east), nrm to the north-east
def at(s, t):  # s metres along the road from the midpoint, t metres from the centreline towards the plot
    x = s*u[0] + t*nrm[0]; y = s*u[1] + t*nrm[1]
    return (round(mid[0] + y*M_LAT, 6), round(mid[1] + x*M_LON, 6))
HALF_ROAD = 5.0; W = 41.5; D = 28.0
plot = [at(-W/2, HALF_ROAD), at(W/2, HALF_ROAD), at(W/2, HALF_ROAD+D), at(-W/2, HALF_ROAD+D)]
gate = at(-W/2 + 15.65, HALF_ROAD + 0.5)       # the screened vehicle entrance, x 12.1–19.2 m from the west corner
site = at(0, HALF_ROAD + D/2)

LANDMARKS = [
  dict(id='site', g='street', n='Heights 777', s='Plot 777, Parakou Street, Wuse II', ll=site, route=False),
  dict(id='aminu', g='street', n='Aminu Kano Crescent', s='Wuse II’s main street of restaurants, shops and banks, a short walk from the plot', ll=nearest_on(ways_named('Aminu Kano Crescent'), site[0], site[1]), route=True),
  dict(id='maitama', g='maitama', n='Maitama', s='The diplomatic district north of Aminu Kano Crescent: embassies, ministers’ residences, banks', ll=(9.0868, 7.4915), route=True),
  dict(id='hilton', g='maitama', n='Transcorp Hilton', s='Abuja’s landmark hotel on Zambezi Crescent, at the edge of Maitama', ll=(9.07497, 7.49476), route=True),
  dict(id='cbd', g='city', n='Central Business District', s='The Central Area: ministries, the National Mosque and Eagle Square', ll=(9.05371, 7.48835), route=True),
  dict(id='wusemkt', g='city', n='Wuse Market', s='The city’s main market, on Douala Street in Wuse', ll=(9.06862, 7.46601), route=True),
  dict(id='banex', g='city', n='Banex Plaza', s='The electronics and phone market at the top of Aminu Kano Crescent', ll=(9.08394, 7.46886), route=True),
  dict(id='jabi', g='jabi', n='Jabi Lake Mall', s='Shops, cinemas and restaurants on the Jabi lakefront', ll=(9.07631, 7.42563), route=True),
  dict(id='airport', g='airport', n='Nnamdi Azikiwe International Airport', s='The international terminal, by the airport road', ll=(9.00484, 7.26935), route=True),
]

routes = {}
for Lm in LANDMARKS:
    if not Lm['route']: continue
    la, lo = Lm['ll']
    url = f"https://router.project-osrm.org/route/v1/driving/{gate[1]},{gate[0]};{lo},{la}?overview=full&geometries=geojson"
    rt = None
    for attempt in range(3):
        try:
            raw = subprocess.run(['curl','-s','-m','60','-A','MizanQist-brochure-build/1.0', url], capture_output=True, text=True, check=True).stdout
            j = json.loads(raw); rt = j['routes'][0]; break
        except Exception as e:
            print('retry', Lm['id'], e); time.sleep(3)
    if not rt: print('NO ROUTE', Lm['id']); continue
    pts = [(c[1], c[0]) for c in rt['geometry']['coordinates']]
    simp = r5(dp(pts, 6 if rt['distance'] > 10000 else 3))
    routes[Lm['id']] = {'km': round(rt['distance']/1000, 1), 'pts': simp}
    Lm['km'] = round(rt['distance']/1000, 1)
    print(f"route {Lm['id']:10s} {rt['distance']/1000:5.2f} km  {len(pts)} -> {len(simp)} pts")
    time.sleep(1)

for Lm in LANDMARKS: Lm['ll'] = [round(Lm['ll'][0],6), round(Lm['ll'][1],6)]; Lm.pop('route', None)
data = {'site': list(site), 'gate': list(gate), 'exit': None, 'plot': [list(p) for p in plot], 'landmarks': LANDMARKS, 'routes': routes, 'streets': street_out}
js = 'window.COVA_MAP=' + json.dumps(data, separators=(',',':'), ensure_ascii=False) + ';\n'
open(OUT, 'w', encoding='utf-8').write(js)
print('wrote', OUT, len(js.encode('utf-8')), 'bytes'); print('site', site, 'gate', gate, 'plot', plot)
