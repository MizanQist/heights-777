import json, urllib.request, urllib.parse, sys, time
UA = "MizanQist-brochure-build/1.0 (nabildeealee@icloud.com)"
name, q = sys.argv[1], sys.argv[2]
servers = ["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter","https://lz4.overpass-api.de/api/interpreter"]
j=None
for attempt in range(4):
    for s in servers:
        try:
            req = urllib.request.Request(s, data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=150) as r: j = json.load(r)
            break
        except Exception as e:
            print('retry', s, e, file=sys.stderr); time.sleep(3)
    if j: break
json.dump(j, open(name+'.json','w'))
print('###', name, len(j.get('elements',[])), 'elements')
for e in j['elements']:
    t = e.get('tags',{})
    g = e.get('geometry') or ([{'lat':e['lat'],'lon':e['lon']}] if 'lat' in e else [])
    c = e.get('center')
    first = (g[0]['lat'], g[0]['lon']) if g else (c and (c['lat'],c['lon']))
    print(' ', e['type'], e['id'], repr(t.get('name')), '|', t.get('highway') or t.get('building') or t.get('amenity') or t.get('aeroway') or t.get('natural') or t.get('tourism') or t.get('place') or t.get('leisure') or t.get('bridge'), '| pts', len(g), '| first', first)
