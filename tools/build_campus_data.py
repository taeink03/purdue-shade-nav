"""Convert an Overpass GeoJSON export of central Purdue into campus-data.js for the shade app.

usage: python3 build.py export.geojson out/campus-data.js
"""
import json, math, sys, re, random, collections

SRC, OUT = sys.argv[1], sys.argv[2]
LAT0, LNG0 = 40.4290, -86.9175
phi = math.radians(LAT0)
KY = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
KX = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
S, N, W, E = 40.4215, 40.4365, -86.9282, -86.9073          # clip box (query box + ~50 m)


def inside(lo, la):
    return S <= la <= N and W <= lo <= E


def P(lo, la):
    return (round((lo - LNG0) * KX, 1), round(-(la - LAT0) * KY, 1))


def dseg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l = dx * dx + dy * dy
    t = 0 if l == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / l))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    i, m = 0, -1
    for k in range(1, len(pts) - 1):
        d = dseg(pts[k][0], pts[k][1], a[0], a[1], b[0], b[1])
        if d > m:
            i, m = k, d
    if m <= tol:
        return [a, b]
    return dp(pts[: i + 1], tol)[:-1] + dp(pts[i:], tol)


def simp_ring(r, tol=0.5):
    if r[0] == r[-1]:
        r = r[:-1]
    if len(r) <= 4:
        return r
    # split at the vertex farthest from r[0] so DP works on two open chains
    far = max(range(len(r)), key=lambda k: (r[k][0] - r[0][0]) ** 2 + (r[k][1] - r[0][1]) ** 2)
    a = dp(r[: far + 1], tol)
    b = dp(r[far:] + [r[0]], tol)
    out = a[:-1] + b[:-1]
    return out if len(out) >= 3 else r


def area_centroid(r):
    A = cx = cy = 0
    for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
        c = x1 * y2 - x2 * y1
        A += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    A /= 2
    if abs(A) < 1e-6:
        return 0, r[0]
    return abs(A), (cx / (6 * A), cy / (6 * A))


def pip(x, y, r):
    c = False
    for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


SHORT = [(r'^(North|South|East|West) ', ''), (r'\bStreet\b', 'St'), (r'\bAvenue\b', 'Ave'), (r'\bBoulevard\b', 'Blvd'),
         (r'\bDrive\b', 'Dr'), (r'\bRoad\b', 'Rd'), (r'\bPlace\b', 'Pl'), (r'\bLane\b', 'Ln')]


def short(n):
    o = n
    for a, b in SHORT:
        n = re.sub(a, b, n)
    return o if len(n) < 4 else n


d = json.load(open(SRC))
F = d['features']

# ---------------- buildings ----------------
LEVEL_M = {'university': 4.2, 'school': 4.0, 'retail': 4.5, 'commercial': 4.2}
TYPE_H = {'house': 8, 'detached': 8, 'semidetached_house': 8, 'residential': 12, 'apartments': 14, 'dormitory': 18,
          'university': 15, 'school': 12, 'garage': 3.5, 'shed': 3, 'roof': 4.5, 'retail': 6, 'commercial': 8,
          'church': 14, 'parking': 13, 'stadium': 22, 'industrial': 10, 'greenhouse': 5, 'fire_station': 8, 'yes': 10}
RENAME = {'Purdue Student Union': 'Purdue Memorial Union (PMU)', 'Krannert School of Management': 'Krannert Building (KRAN)',
          'Lilly Hall': 'Lilly Hall of Life Sciences (LILY)', 'Mackey Arena': 'Mackey Arena (MACK)',
          'Purdue Bell Tower': 'Purdue Bell Tower', 'Earhart Hall': 'Earhart Hall (ERHT)', 'Windsor Halls': 'Windsor Halls (WIND)',
          'France A. Córdova Recreational Sports Center': 'Córdova Recreational Sports Center (CREC)',
          'Lawson Hall (LWSN)': 'Lawson Computer Science Building (LWSN)'}
bld = []
hsrc_count = collections.Counter()
for f in F:
    p = f['properties']
    if 'building' not in p or f['geometry']['type'] != 'Polygon':
        continue
    ring = [P(*q) for q in f['geometry']['coordinates'][0]]
    lo, la = f['geometry']['coordinates'][0][0]
    A, (cx, cy) = area_centroid(ring[:-1] if ring[0] == ring[-1] else ring)
    clat, clng = LAT0 - cy / KY, LNG0 + cx / KX
    if not inside(clng, clat) or A < 6:
        continue
    t = p['building']
    h, src = None, 2
    try:
        if 'height' in p:
            h, src = float(re.sub('[^0-9.]', '', p['height'])), 0
    except ValueError:
        pass
    if h is None and 'building:levels' in p:
        try:
            lv = float(p['building:levels'])
            h, src = lv * LEVEL_M.get(t, 3.4) + 1.5, 1
        except ValueError:
            pass
    if h is None:
        h = TYPE_H.get(t, 10)
        if t in ('university', 'yes') and A > 3500:
            h += 5
    h = round(min(max(h, 2.5), 60), 1)
    hsrc_count[src] += 1
    name = p.get('name', '')
    name = RENAME.get(name, name)
    if name == 'Purdue Memorial Union (PMU)' and not (abs(clat - 40.4248) < .0012 and abs(clng + 86.9110) < .0015):
        name = 'Purdue Student Union'
    if t == 'stadium':
        name = 'Ross–Ade Stadium'
    m = re.match(r'^(.*?)\s*\(([A-Z0-9]{2,6})\)\s*$', name)
    disp, code = (m.group(1), m.group(2)) if m else (name, '')
    camp = 1 if t in ('university', 'dormitory', 'school', 'stadium', 'parking') or name else 0
    r = simp_ring(ring)
    bld.append(dict(n=disp, c=code, t=t, h=h, s=src, camp=camp, r=r, A=A, cx=cx, cy=cy, lat=clat, lng=clng))
print('buildings', len(bld), dict(hsrc_count))

# ---------------- trees ----------------
rnd = random.Random(20261117)
trees = []
for f in F:
    p = f['properties']
    if p.get('natural') == 'tree' and f['geometry']['type'] == 'Point':
        lo, la = f['geometry']['coordinates']
        if not inside(lo, la):
            continue
        x, y = P(lo, la)
        h = round(8 + rnd.random() * 9, 1)
        r = round(min(7, max(3, h * (0.3 + rnd.random() * 0.12))), 1)
        trees.append((x, y, h, r))
print('trees', len(trees))

# ---------------- walking network ----------------
# classes: 0 footway 1 sidewalk 2 crossing 3 steps 4 path/cycle 5 service 6 local road 7 major road 8 indoor/tunnel
MAJOR = {'primary', 'secondary', 'tertiary', 'primary_link', 'secondary_link', 'tertiary_link', 'trunk'}
LOCAL = {'residential', 'unclassified', 'living_street'}
attrs, aidx = [], {}
names, nidx = [], {}


def nameid(n):
    if n not in nidx:
        nidx[n] = len(names); names.append(n)
    return nidx[n]


ways = []
for f in F:
    p = f['properties']
    hw = p.get('highway')
    if not hw or f['geometry']['type'] != 'LineString' or hw in ('construction', 'proposed', 'motorway', 'motorway_link'):
        continue
    if p.get('foot') in ('no', 'private') or p.get('access') in ('no', 'private') and p.get('foot') not in ('yes', 'designated'):
        continue
    fw = p.get('footway')
    if hw == 'corridor' or p.get('indoor') == 'yes':
        cls = 8
    elif hw == 'steps':
        cls = 3
    elif hw in MAJOR:
        cls = 7
    elif hw in LOCAL:
        cls = 6
    elif hw == 'service':
        cls = 5
    elif hw in ('cycleway', 'path', 'track', 'bridleway'):
        cls = 4
    elif fw == 'sidewalk':
        cls = 1
    elif fw == 'crossing':
        cls = 2
    else:
        cls = 0
    try:
        layer = float(p.get('layer', 0))
    except ValueError:
        layer = 0
    cov = 1 if (cls == 8 or p.get('covered') in ('yes', 'arcade', 'colonnade') or p.get('tunnel') in ('yes', 'building_passage') or layer < 0) else 0
    nm = p.get('name', '')
    ways.append(dict(cls=cls, cov=cov, name=short(nm) if nm else '', svc=p.get('service', ''),
                     pts=f['geometry']['coordinates']))

# name unnamed sidewalks after the nearest named road
roads = []
for w in ways:
    if w['cls'] in (6, 7) and w['name']:
        pts = [P(*q) for q in w['pts']]
        for a, b in zip(pts, pts[1:]):
            roads.append((a, b, w['name']))
for w in ways:
    if w['name']:
        continue
    if w['cls'] == 1 or w['cls'] == 2:
        pts = [P(*q) for q in w['pts']]
        mx, my = pts[len(pts) // 2]
        best, bn = 35, ''
        for a, b, n in roads:
            if abs(a[0] - mx) > 300 and abs(b[0] - mx) > 300:
                continue
            dd = dseg(mx, my, a[0], a[1], b[0], b[1])
            if dd < best:
                best, bn = dd, n
        if bn:
            w['name'] = ('Sidewalk, ' if w['cls'] == 1 else 'Crosswalk, ') + bn
GENERIC = {0: 'Campus walk', 1: 'Sidewalk', 2: 'Crosswalk', 3: 'Stairs', 4: 'Shared path', 5: 'Service drive', 6: 'Street',
           7: 'Street', 8: 'Indoor corridor'}
for w in ways:
    if not w['name']:
        w['name'] = 'Parking lot' if w['svc'] == 'parking_aisle' else 'Tunnel' if (w['cov'] and w['cls'] != 8 and w['cls'] != 0) else GENERIC[w['cls']]
        if w['cls'] == 0 and w['cov']:
            w['name'] = 'Covered walkway'

nodes, nkey = [], {}


def node(q):
    k = (round(q[0], 7), round(q[1], 7))
    if k not in nkey:
        nkey[k] = len(nodes); nodes.append(P(*q))
    return nkey[k]


segs = []
for w in ways:
    key = (w['cls'], w['cov'], nameid(w['name']))
    if key not in aidx:
        aidx[key] = len(attrs); attrs.append(list(key))
    a = aidx[key]
    pts = w['pts']
    for q1, q2 in zip(pts, pts[1:]):
        if not (inside(*q1) and inside(*q2)):
            continue
        i, j = node(q1), node(q2)
        if i != j:
            segs.append((i, j, a))

# largest connected component
adj = collections.defaultdict(list)
for k, (i, j, a) in enumerate(segs):
    adj[i].append(j); adj[j].append(i)
comp, best = {}, None
for s in list(adj):
    if s in comp:
        continue
    stack, members = [s], [s]
    comp[s] = s
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v not in comp:
                comp[v] = s; stack.append(v); members.append(v)
    if best is None or len(members) > len(best):
        best = members
keep = set(best)
remap, out_nodes = {}, []
for i in sorted(keep):
    remap[i] = len(out_nodes); out_nodes.append(nodes[i])
seen, out_segs = set(), []
for i, j, a in segs:
    if i in keep and j in keep:
        k = (min(i, j), max(i, j))
        if k in seen:
            continue
        seen.add(k)
        out_segs.append((remap[i], remap[j], a))
tot = sum(math.hypot(out_nodes[i][0] - out_nodes[j][0], out_nodes[i][1] - out_nodes[j][1]) for i, j, a in out_segs)
print('network nodes', len(out_nodes), 'segments', len(out_segs), 'length km', round(tot / 1000, 1), 'dropped nodes', len(nodes) - len(out_nodes))

# ---------------- destinations ----------------
NX = [n[0] for n in out_nodes]; NY = [n[1] for n in out_nodes]


def doors_for(ring, px=None, py=None):
    xs = [q[0] for q in ring]; ys = [q[1] for q in ring]
    x0, x1, y0, y1 = min(xs) - 60, max(xs) + 60, min(ys) - 60, max(ys) + 60
    cand = []
    for k in range(len(out_nodes)):
        x, y = NX[k], NY[k]
        if x < x0 or x > x1 or y < y0 or y > y1:
            continue
        if px is not None:
            dd = math.hypot(x - px, y - py)
        elif pip(x, y, ring):
            dd = 0
        else:
            dd = min(dseg(x, y, a[0], a[1], b[0], b[1]) for a, b in zip(ring, ring[1:] + ring[:1]))
        cand.append((dd, k))
    cand.sort()
    if not cand:
        return []
    near = [c for c in cand if c[0] <= 14] or cand[:1]
    pick = [near[0][1]]
    while len(pick) < 6 and len(pick) < len(near):        # spread doors around the building
        bestk, bestd = None, -1
        for dd, k in near:
            if k in pick:
                continue
            m = min(math.hypot(NX[k] - NX[q], NY[k] - NY[q]) for q in pick)
            if m > bestd:
                bestk, bestd = k, m
        if bestd < 18:
            break
        pick.append(bestk)
    return pick


dest = []
byname = collections.defaultdict(list)
for bi, b in enumerate(bld):
    if b['n']:
        byname[(b['n'], b['c'])].append(bi)
for (n, c), idxs in byname.items():
    doors = []
    for bi in idxs:
        doors += doors_for(bld[bi]['r'])
    doors = list(dict.fromkeys(doors))[:8]
    if not doors:
        continue
    big = max(idxs, key=lambda k: bld[k]['A'])
    b = bld[big]
    dest.append(dict(n=n, c=c, b=idxs, d=doors, x=round(b['cx'], 1), y=round(b['cy'], 1), lat=round(b['lat'], 6), lng=round(b['lng'], 6)))
fx, fy = P(-86.91378, 40.42864)
dest.append(dict(n='Engineering Fountain', c='', b=[], d=doors_for([(fx, fy)], fx, fy)[:4], x=fx, y=fy, lat=40.42864, lng=-86.91378))
dest.sort(key=lambda o: o['n'])
print('destinations', len(dest))

plazas = []
for f in F:
    p = f['properties']
    if p.get('highway') == 'pedestrian' and f['geometry']['type'] == 'Polygon':
        plazas.append([c for q in simp_ring([P(*q) for q in f['geometry']['coordinates'][0]]) for c in q])

data = dict(
    o=[LAT0, LNG0, round(KY, 3), round(KX, 3)],
    src=d.get('copyright', ''), ts=d.get('timestamp', ''),
    b=[[b['n'], b['c'], b['t'], b['h'], b['s'], b['camp'], [c for q in b['r'] for c in q]] for b in bld],
    t=[c for t in trees for c in t],
    n=[c for q in out_nodes for c in q],
    e=[c for s in out_segs for c in s],
    a=attrs, nm=names,
    d=[[o['n'], o['c'], o['b'], o['d'], o['x'], o['y'], o['lat'], o['lng']] for o in dest],
    pl=plazas,
)
js = '/* Generated from OpenStreetMap data (c) OpenStreetMap contributors, ODbL. See README. */\nwindow.CAMPUS=' + json.dumps(data, separators=(',', ':'), ensure_ascii=False) + ';\n'
open(OUT, 'w').write(js)
print('wrote', OUT, round(len(js.encode()) / 1024), 'KB')
