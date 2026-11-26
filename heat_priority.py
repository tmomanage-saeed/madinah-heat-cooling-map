# -*- coding: utf-8 -*-
"""
Madinah Cooling Map v4: cooling priority on the real surface-heat map (no circles, no 1 km cells).

Inputs
  Madinah_City.gdb : Heat_Zones_Madinah (land surface temperature classes, 30 m pixels),
                     Madinah_City_Boundary, Mosques, Schools, Bus_Stations, Shopping_Malls, Parks,
                     Pedestrian_Movement_Hex (250 m PMI), Trees_OSM
  Madinah_Analysis.gdb : Proposed_Site_Trees (trees at mosques, schools, parks ...; kept from v3)
  geofabrik_unzip : OSM roads, buildings, landuse
  ../web/madinah_data.json : v3 web data (sites, walking network, Map 02 layers are reused)

Method (30 m analysis grid, same pixel size as the heat data)
  Cooling priority = 40 % Surface heat + 25 % Places people use + 20 % People walking + 15 % Missing shade
    Surface heat      : heat class 35-40 C = 0 ... 65-70 C = 1
    Places people use : 300 m kernel around mosques/schools (3), bus/malls (2.5), parks (1.5), Masjid an-Nabawi (10)
    People walking    : Pedestrian Movement Index (footpaths + destinations + built density)
    Missing shade     : 1 - green share within ~270 m (OSM green land use; 30 % green = fully shaded)
  Classes by share of street length: Critical = top 5 %, Very High 85-95 %, High 65-85 %, Moderate 40-65 %, Low < 40 %.
  Street trees on both kerbs, spacing per 50 m stretch of street from the class under it:
    Critical 8 m, Very High 10 m, High 12 m, Moderate 16 m, Low 24 m  (8 m crown / target footpath shade).
RUN: "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" -I heat_priority.py
"""
import os, json, math, base64, datetime
import numpy as np
from osgeo import ogr, osr, gdal
from scipy.spatial import cKDTree
from scipy.signal import fftconvolve
from scipy.ndimage import uniform_filter
from matplotlib.path import Path as MPath

ogr.UseExceptions(); gdal.UseExceptions()
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GDB = os.path.join(ROOT, "Madinah_City.gdb")
AGDB = os.path.join(ROOT, "Madinah_Analysis.gdb")
GF = os.path.join(ROOT, "geofabrik_unzip")
V3 = os.path.join(ROOT, "web", "madinah_data.json")
OUT = os.path.join(HERE, "madinah_data_v4.json")
def log(m): print(m, flush=True)
def gf(n): return os.path.join(GF, f"gis_osm_{n}_free_1.shp")

# ---------------- settings ----------------
PIX = 30.0
W_HEAT, W_SENS, W_PED, W_SHADE = 0.40, 0.25, 0.20, 0.15
SENS_W = {"Mosques": 3.0, "Schools": 3.0, "Bus_Stations": 2.5, "Shopping_Malls": 2.5}
PARK_W, NABAWI_W, SENS_R = 1.5, 10.0, 300.0
GREEN_FULL, GREEN_WIN = 0.30, 9          # 9 px x 30 m = 270 m window
BRK_PCT = [40, 65, 85, 95]
TREE_M2, TREE_SP = 53.0, 8.0             # mean measured crown (Meta/WRI 1 m canopy height), ~8 m across
SP_CLS = {5: 8.0, 4: 10.0, 3: 12.0, 2: 16.0, 1: 24.0, 0: 24.0}
PIECE = 50.0
ST_OFF, HARAM_EXIST_M = 2.5, 420
HARAM = (39.6111, 24.4672)
HW = {"motorway": 12, "motorway_link": 6, "trunk": 12, "trunk_link": 6, "primary": 10, "primary_link": 5,
      "secondary": 8, "secondary_link": 5, "tertiary": 6, "tertiary_link": 4, "residential": 4,
      "unclassified": 4, "living_street": 3, "service": 3}
FOOT = ("footway", "pedestrian", "path", "steps")
GREEN_FC = ('park', 'grass', 'forest', 'orchard', 'recreation_ground', 'meadow', 'allotments', 'nature_reserve', 'scrub')
LBL = {5: "Critical", 4: "Very High", 3: "High", 2: "Moderate", 1: "Low", 0: "Outside"}

UTM = osr.SpatialReference(); UTM.ImportFromEPSG(32637); UTM.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
WGS = osr.SpatialReference(); WGS.ImportFromEPSG(4326); WGS.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
to_utm = osr.CoordinateTransformation(WGS, UTM); to_wgs = osr.CoordinateTransformation(UTM, WGS)

# ---------------- grid ----------------
gds = ogr.Open(GDB)
bnd_l = gds.GetLayerByName("Madinah_City_Boundary")
_bf = bnd_l.GetNextFeature(); bnd = _bf.GetGeometryRef().Clone()
x0, x1, y0, y1 = bnd.GetEnvelope()
x0 = math.floor(x0 / PIX) * PIX - PIX; y1 = math.ceil(y1 / PIX) * PIX + PIX
NX = int(math.ceil((x1 - x0) / PIX)) + 2; NY = int(math.ceil((y1 - y0) / PIX)) + 2
GT = (x0, PIX, 0, y1, 0, -PIX)
log(f"Grid {NX} x {NY} at {PIX:.0f} m")

def mem_raster(dtype=gdal.GDT_Float32):
    r = gdal.GetDriverByName("MEM").Create("", NX, NY, 1, dtype)
    r.SetGeoTransform(GT); r.SetProjection(UTM.ExportToWkt()); return r

def to_utm_layer(src, layer=None, where=None):
    """Copy a layer into memory in UTM 37N, limited to the grid extent."""
    opts = gdal.VectorTranslateOptions(format="Memory", dstSRS="EPSG:32637", layers=[layer] if layer else None,
                                       where=where, spatFilter=None, geometryType="PROMOTE_TO_MULTI")
    ds = gdal.VectorTranslate("", src, options=opts)
    return ds

def rasterize(ds, attr=None, burn=1, all_touched=False, dtype=gdal.GDT_Float32):
    r = mem_raster(dtype)
    o = ["ALL_TOUCHED=TRUE"] if all_touched else []
    if attr: o.append(f"ATTRIBUTE={attr}")
    gdal.RasterizeLayer(r, [1], ds.GetLayer(0), burn_values=[] if attr else [burn], options=o)
    return r.GetRasterBand(1).ReadAsArray().astype(np.float32)

def px(x, y):
    c = ((np.asarray(x) - x0) / PIX).astype(int); r = ((y1 - np.asarray(y)) / PIX).astype(int)
    return np.clip(r, 0, NY - 1), np.clip(c, 0, NX - 1)

mask = rasterize(to_utm_layer(GDB, "Madinah_City_Boundary")) > 0
heat = rasterize(to_utm_layer(GDB, "Heat_Zones_Madinah"), attr="gridcode")
inside = mask & (heat > 0)
log(f"Boundary {mask.sum() * PIX * PIX / 1e6:.0f} km2, with heat data {inside.sum() * PIX * PIX / 1e6:.0f} km2")
H = np.where(heat > 0, (heat - 1) / 6.0, 0)

def norm(v, m, pct=99):
    pos = v[m & (v > 0)]
    hi = np.percentile(pos, pct) if len(pos) else 1
    return np.clip(v / hi, 0, 1)

# ---------------- places people use ----------------
def kern(r):
    n = int(r // PIX); yy, xx = np.mgrid[-n:n + 1, -n:n + 1] * PIX
    d2 = (xx ** 2 + yy ** 2) / r ** 2
    return np.where(d2 < 1, (1 - d2) ** 2, 0)
pts = np.zeros((NY, NX), np.float32); hx, hy, _ = to_utm.TransformPoint(*HARAM)
nab = 0
for fc, w in SENS_W.items():
    for f in gds.GetLayerByName(fc):
        g = f.GetGeometryRef(); nm = (f.GetField("name") or "")
        ww = w
        if fc == "Mosques" and ("النبوي" in nm or "nabawi" in nm.lower()): ww = NABAWI_W; nab += 1
        r, c = px(g.GetX(), g.GetY()); pts[r, c] += ww
for f in gds.GetLayerByName("Parks"):
    p = f.GetGeometryRef().PointOnSurface(); r, c = px(p.GetX(), p.GetY()); pts[r, c] += PARK_W
sens = fftconvolve(pts, kern(SENS_R), mode="same")
hp = np.zeros_like(pts); r, c = px(hx, hy); hp[r, c] = NABAWI_W
sens += fftconvolve(hp, kern(SENS_R * 2), mode="same")
sens[sens < 1e-6] = 0
S = norm(sens, inside)
log(f"Places: Nabawi entries {nab}")

# ---------------- people walking ----------------
pmi = rasterize(to_utm_layer(GDB, "Pedestrian_Movement_Hex"), attr="PMI")
Wk = norm(pmi, inside)

# ---------------- missing shade ----------------
# existing tree canopy (Meta/WRI 1 m canopy height, treetops + crowns from existing_trees.py) + OSM parks / green land use
ET = np.load(os.path.join(ROOT, "data", "existing_trees", "existing_trees.npz"))
_ex = np.array([to_utm.TransformPoint(float(a), float(b))[:2] for a, b in zip(ET["lat"] * 0 + ET["lon"], ET["lat"])])
er, ec = px(_ex[:, 0], _ex[:, 1])
can_m2 = np.zeros((NY, NX), np.float32); np.add.at(can_m2, (er, ec), ET["crown"].astype(np.float32))
can_share = uniform_filter(np.clip(can_m2 / (PIX * PIX), 0, 1), GREEN_WIN)       # tree canopy share within ~270 m
green = rasterize(to_utm_layer(gf("landuse_a"), where="fclass IN (%s)" % ",".join(f"'{x}'" for x in GREEN_FC)))
gshare = uniform_filter((green > 0).astype(np.float32), GREEN_WIN)
# 30 % canopy within the neighbourhood = fully shaded (the "30" of the 3-30-300 urban forestry rule, Konijnendijk 2021)
D = 1 - np.clip(np.maximum(can_share, gshare) / GREEN_FULL, 0, 1)
log(f"Existing trees {len(_ex)}; canopy {can_m2[mask].sum() / 1e6:.1f} km2 in boundary")

P = np.where(inside, W_HEAT * H + W_SENS * S + W_PED * Wk + W_SHADE * D, 0).astype(np.float32)

# ---------------- roads ----------------
log("Roads ...")
rds = to_utm_layer(gf("roads"))
bnd_buf = bnd.Buffer(50)
roads = []
for f in rds.GetLayer(0):
    g = f.GetGeometryRef()
    if g is None or not g.Intersects(bnd_buf): continue
    fc = f.GetField("fclass") or "unknown"
    gi = g.Intersection(bnd_buf) if not bnd_buf.Contains(g) else g
    for k in range(max(gi.GetGeometryCount(), 1)):
        part = gi.GetGeometryRef(k) if gi.GetGeometryCount() else gi
        if part is None or part.GetGeometryType() not in (ogr.wkbLineString, ogr.wkbLineString25D): continue
        P_ = np.array(part.GetPoints())[:, :2]
        if len(P_) >= 2: roads.append((fc, P_))
log(f"  road parts {len(roads)}")
rv, rh, jdeg = [], [], {}
for fc, pts_ in roads:
    hw = 0.0 if fc in FOOT else float(HW.get(fc, 3.0))
    wk = fc not in ("motorway", "motorway_link", "trunk", "trunk_link")
    if hw > 0 and wk:
        for q, (x, y) in enumerate(pts_):
            kk = (round(x), round(y)); d0 = jdeg.get(kk, (0, 0.0))
            jdeg[kk] = (d0[0] + (1 if q in (0, len(pts_) - 1) else 2), max(d0[1], hw))
    for (xa, ya), (xb, yb) in zip(pts_[:-1], pts_[1:]):
        n = max(1, int(math.hypot(xb - xa, yb - ya) // 4)); fr = np.arange(n) / n
        rv.append(np.c_[xa + (xb - xa) * fr, ya + (yb - ya) * fr]); rh += [hw] * n
rv = np.vstack(rv); rh = np.array(rh); rtree = cKDTree(rv)
_jxy = np.array([k for k, (d, _) in jdeg.items() if d >= 3], float); jtree = cKDTree(_jxy)

def street_ok(fc):
    return not (fc in FOOT or fc in ("motorway", "motorway_link", "trunk", "trunk_link", "service", "unknown")
                or fc.startswith("track") or fc in ("cycleway", "bridleway"))

# class breaks by share of street length (samples every 10 m)
samp = []
for fc, pts_ in roads:
    if not street_ok(fc): continue
    seg = np.hypot(*np.diff(pts_, axis=0).T); cum = np.r_[0, np.cumsum(seg)]
    if cum[-1] < 1: continue
    d = np.arange(5, cum[-1], 10.0)
    k = np.clip(np.searchsorted(cum, d) - 1, 0, len(seg) - 1); fr = (d - cum[k]) / np.maximum(seg[k], 1e-6)
    samp.append(np.c_[pts_[k, 0] + (pts_[k + 1, 0] - pts_[k, 0]) * fr, pts_[k, 1] + (pts_[k + 1, 1] - pts_[k, 1]) * fr])
samp = np.vstack(samp); sr, sc = px(samp[:, 0], samp[:, 1])
sP = P[sr, sc]; sP = sP[inside[sr, sc]]
brk = np.percentile(sP, BRK_PCT)
C = np.where(inside, np.digitize(P, brk) + 1, 0).astype(np.uint8)
log("Breaks " + ", ".join(f"{b:.3f}" for b in brk) + f"  (street samples {len(sP)})")
for c in range(5, 0, -1): log(f"  {LBL[c]:<10} {(C == c).sum() * PIX * PIX / 1e6:7.1f} km2")

# ---------------- street trees ----------------
log("Street trees ...")
cand, km_cls = [], {}
for fc, pts_ in roads:
    if not street_ok(fc): continue
    hw = float(HW.get(fc, 3.0))
    seg = np.hypot(*np.diff(pts_, axis=0).T); cum = np.r_[0, np.cumsum(seg)]; L = cum[-1]
    if L < 8: continue
    npc = max(1, int(round(L / PIECE))); edges = np.linspace(0, L, npc + 1)
    ds_ = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (a + b) / 2; k = min(np.searchsorted(cum, m) - 1, len(seg) - 1); k = max(k, 0)
        fr = (m - cum[k]) / max(seg[k], 1e-6)
        mx = pts_[k, 0] + (pts_[k + 1, 0] - pts_[k, 0]) * fr; my = pts_[k, 1] + (pts_[k + 1, 1] - pts_[k, 1]) * fr
        r_, c_ = px(mx, my); cl = int(C[r_, c_]) if mask[r_, c_] else -1
        if cl < 0: continue
        sp = SP_CLS[cl]; km_cls[cl] = km_cls.get(cl, 0) + (b - a) / 1000
        ds_.append(np.arange(a + sp / 2, b, sp))
    if not ds_: continue
    d = np.concatenate(ds_)
    k = np.clip(np.searchsorted(cum, d) - 1, 0, len(seg) - 1); fr = (d - cum[k]) / np.maximum(seg[k], 1e-6)
    X = pts_[k, 0] + (pts_[k + 1, 0] - pts_[k, 0]) * fr; Y = pts_[k, 1] + (pts_[k + 1, 1] - pts_[k, 1]) * fr
    ux = (pts_[k + 1, 0] - pts_[k, 0]) / np.maximum(seg[k], 1e-6); uy = (pts_[k + 1, 1] - pts_[k, 1]) / np.maximum(seg[k], 1e-6)
    o = hw + ST_OFF
    for sg in (1, -1): cand.append(np.c_[X - sg * uy * o, Y + sg * ux * o])
SP_ = np.vstack(cand); log(f"  candidates {len(SP_)} on {sum(km_cls.values()):.0f} km")
r_, c_ = px(SP_[:, 0], SP_[:, 1]); ok = mask[r_, c_]
ok &= np.hypot(SP_[:, 0] - hx, SP_[:, 1] - hy) > HARAM_EXIST_M
jd, _ = jtree.query(SP_); ok &= jd > 12
dd, jj = rtree.query(SP_, k=12, distance_upper_bound=40)
v_ = np.isfinite(dd); jj_ = np.where(v_, jj, 0)
ok &= ~(v_ & (rh[jj_] > 0) & (dd < rh[jj_] + 1.0)).any(1)
ot = []
for f in gds.GetLayerByName("Trees_OSM"):
    g = f.GetGeometryRef(); ot.append((g.GetX(), g.GetY()))
if ot: od, _ = cKDTree(np.array(ot)).query(SP_); ok &= od > 8
SP_ = SP_[ok]; log(f"  after road / junction / Haram checks {len(SP_)}")
# buildings
bt = cKDTree(SP_); hit = np.zeros(len(SP_), bool); nb = 0
bds = to_utm_layer(gf("buildings_a"))
for f in bds.GetLayer(0):
    g = f.GetGeometryRef()
    if g is None: continue
    ex = g.GetEnvelope(); cx_, cy_ = (ex[0] + ex[1]) / 2, (ex[2] + ex[3]) / 2
    rad = math.hypot(ex[1] - ex[0], ex[3] - ex[2]) / 2 + 0.5
    ids = bt.query_ball_point((cx_, cy_), rad)
    if not ids: continue
    nb += 1; ids = np.array(ids)
    for k in range(g.GetGeometryCount()):
        poly = g.GetGeometryRef(k)
        if poly.GetGeometryType() in (ogr.wkbPolygon, ogr.wkbPolygon25D):
            ring = poly.GetGeometryRef(0)
        else:
            ring = poly
        R = np.array(ring.GetPoints())[:, :2]
        if len(R) >= 3: hit[ids[MPath(R).contains_points(SP_[ids])]] = True
SP_ = SP_[~hit]; log(f"  excluded on buildings {hit.sum()}")
# site trees (kept from v3) occupy their spots first
site = []
ads = ogr.Open(AGDB)
for f in ads.GetLayerByName("Proposed_Site_Trees"):
    g = f.GetGeometryRef(); site.append((g.GetX(), g.GetY()))
site = np.array(site)
store = {}
def free(x, y):
    cx_, cy_ = int(x // TREE_SP), int(y // TREE_SP)
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            for (u, v) in store.get((cx_ + a, cy_ + b), ()):
                if (u - x) ** 2 + (v - y) ** 2 < TREE_SP ** 2: return False
    return True
def put(x, y): store.setdefault((int(x // TREE_SP), int(y // TREE_SP)), []).append((x, y))
for x, y in site: put(x, y)
for x, y in _ex: put(x, y)          # existing trees: no new tree within 8 m of one
street = []
for x, y in SP_:
    if free(x, y): put(x, y); street.append((x, y))
street = np.array(street); log(f"  street trees {len(street)}  + site trees {len(site)}")

# ---------------- per-class figures ----------------
allT = np.vstack([street, site]); tr, tc = px(allT[:, 0], allT[:, 1]); tcls = C[tr, tc]
sr_, sc_ = px(street[:, 0], street[:, 1]); scls = C[sr_, sc_]
tiers = {}
for c in range(5, -1, -1):
    a_ = (C == c).sum() * PIX * PIX if c > 0 else 0
    n_ = int((scls == c).sum()); nall = int((tcls == c).sum())
    pp = 100 * nall * TREE_M2 / a_ if a_ else 0
    tiers[c] = {"sp": SP_CLS[c], "km": round(km_cls.get(c, 0)), "n": n_, "km2": round(a_ / 1e6, 1),
                "canopy_pp": round(pp, 2), "dT": round(-0.33 * pp / 10, 2)}
    log(f"  {LBL[c]:<10} every {SP_CLS[c]:>4.0f} m  {n_:>7} trees  {km_cls.get(c, 0):6.0f} km  +{pp:.2f} pp  {-0.33 * pp / 10:.2f} C")
hiA = (C >= 3).sum() * PIX * PIX; hiN = int((tcls >= 3).sum())
canopy_pp = 100 * hiN * TREE_M2 / hiA; air_dT = -0.33 * canopy_pp / 10
log(f"High+ {hiA / 1e6:.0f} km2: +{canopy_pp:.2f} pp canopy -> air {air_dT:.2f} C")

# ---------------- web layers (EPSG:3857 PNG overlays) ----------------
def warp(arr, resample):
    src = mem_raster(gdal.GDT_Float32); src.GetRasterBand(1).WriteArray(arr.astype(np.float32))   # (setting a band nodata on a MEM source empties the warp output)
    out = gdal.Warp("", src, format="MEM", dstSRS="EPSG:3857", resampleAlg=resample, xRes=PIX, yRes=PIX, srcNodata=-1, dstNodata=-1)
    a = out.GetRasterBand(1).ReadAsArray(); gt = out.GetGeoTransform()
    return a, gt
def corners(gt, shape):
    m = osr.SpatialReference(); m.ImportFromEPSG(3857); m.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    t = osr.CoordinateTransformation(m, WGS); h, w = shape
    xs = [gt[0], gt[0] + w * gt[1]]; ys = [gt[3], gt[3] + h * gt[5]]
    c = [t.TransformPoint(xs[0], ys[0]), t.TransformPoint(xs[1], ys[0]), t.TransformPoint(xs[1], ys[1]), t.TransformPoint(xs[0], ys[1])]
    return [[round(p[0], 6), round(p[1], 6)] for p in c]
def hex2rgb(h): h = h.lstrip('#'); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
def png(rgba):
    h, w, _ = rgba.shape
    m = gdal.GetDriverByName("MEM").Create("", w, h, 4, gdal.GDT_Byte)
    for i in range(4): m.GetRasterBand(i + 1).WriteArray(rgba[:, :, i])
    gdal.GetDriverByName("PNG").CreateCopy("/vsimem/o.png", m, options=["ZLEVEL=9"])
    f = gdal.VSIFOpenL("/vsimem/o.png", "rb"); gdal.VSIFSeekL(f, 0, 2); n = gdal.VSIFTellL(f); gdal.VSIFSeekL(f, 0, 0)
    b = gdal.VSIFReadL(1, n, f); gdal.VSIFCloseL(f); gdal.Unlink("/vsimem/o.png")
    return "data:image/png;base64," + base64.b64encode(b).decode()
def ramp(v, valid, stops):
    v = np.clip(v, 0, 1); out = np.zeros(v.shape + (4,), np.uint8)
    xs = [s[0] for s in stops]
    for ch in range(3): out[..., ch] = np.interp(v, xs, [hex2rgb(s[1])[ch] for s in stops])
    out[..., 3] = np.where(valid, np.interp(v, xs, [s[2] for s in stops]), 0)
    return out

CPI_COL = {1: "#fde68a", 2: "#fbbf24", 3: "#f97316", 4: "#dc2626", 5: "#7f1d1d"}
layers = {}
cw, gt = warp(np.where(inside, C, -1), "near")
rgba = np.zeros(cw.shape + (4,), np.uint8)
for c, col in CPI_COL.items():
    m = cw == c; rgba[m, :3] = hex2rgb(col); rgba[m, 3] = 255
layers["prio"] = {"img": png(rgba), "co": corners(gt, cw.shape)}
for k, arr, stops in [
    ("sens", S, [(0, "#ecfeff", 0), (0.02, "#a5f3fc", 90), (0.3, "#22d3ee", 190), (1, "#0e7490", 240)]),
    ("walk", Wk, [(0, "#fef9c3", 0), (0.05, "#fde68a", 90), (0.4, "#f59e0b", 190), (1, "#b45309", 240)]),
    ("shade", D, [(0, "#dcfce7", 0), (0.3, "#d6d3d1", 40), (0.9, "#a8a29e", 150), (1, "#78716c", 200)])]:
    a, gt2 = warp(np.where(inside, arr, -1), "bilinear")
    layers[k] = {"img": png(ramp(a, a >= 0, stops)), "co": corners(gt2, a.shape)}
for k, v in layers.items(): log(f"  layer {k}: {len(v['img']) / 1e6:.2f} MB")

# click lookup grid (~90 m, EPSG:3857): heat class, places, walking, missing shade, priority, class
LOOK = 3
def look(arr, res):
    a, g = warp(np.where(inside, arr, -1), res)
    return a[::LOOK, ::LOOK], g
lk = {}
for k, arr, sc_, res in [("h", heat, 1, "near"), ("s", S, 100, "bilinear"), ("w", Wk, 100, "bilinear"),
                         ("d", D, 100, "bilinear"), ("p", P, 250, "bilinear"), ("c", C, 1, "near")]:
    a, g = look(arr, res)
    b = np.where(a < 0, 255, np.clip(np.round(a * sc_), 0, 254)).astype(np.uint8)
    lk[k] = base64.b64encode(b.tobytes()).decode()
lk_gt = [g[0], g[1] * LOOK, g[3], g[5] * LOOK]; lk_shape = list(a.shape)
rank = [round(float(x) * 250) for x in np.percentile(sP, np.arange(0, 101))]

# ---------------- web data ----------------
log("Writing web data ...")
d = json.load(open(V3, encoding="utf-8"))
for k in ("zcpi", "ztree", "zpmi", "umb", "suit"): d.pop(k, None)
heatj = json.load(open(os.path.join(HERE, "heat_zones.json"), encoding="utf-8"))
d["heat"] = heatj
d["layers"] = layers
d["look"] = {"gt": lk_gt, "shape": lk_shape, **lk, "rank": rank}
def pack(xy):
    out = []
    for x, y in xy:
        lon, lat, _ = to_wgs.TransformPoint(float(x), float(y))
        out += [int(round((lon - 39.3) * 1e5)), int(round((lat - 24.2) * 1e5))]
    return {"o": [39.3, 24.2], "p": out}
d["stree"] = pack(street)
# existing trees for the web map: position, height (m), crown (m2)
_e = pack(_ex); d["etree"] = {"o": _e["o"], "p": _e["p"], "h": [int(v) for v in ET["h"]], "c": [int(round(v)) for v in ET["crown"]]}
d["plan"]["existing"] = {"n": int(len(_ex)), "canopy_km2": round(float(can_m2[mask].sum() / 1e6), 1)}
pl = d["plan"]
pl["tiers"] = {str(c): v for c, v in tiers.items()}
pl["street"] = {"n": int(len(street)), "km": round(sum(km_cls.values()))}
pl["site_tree"] = int(len(site))
pl["tot_tree"] = int(len(street) + len(site))
pl["canopy_pp"] = round(canopy_pp, 2); pl["air_dT"] = round(air_dT, 2); pl["hot_km2"] = round(hiA / 1e6, 1)
pl["tree_sp"] = TREE_SP; pl["crown_m2"] = TREE_M2
pl["weights"] = {"heat": 40, "places": 25, "walking": 20, "shade": 15}
st = d["stats"]
st["cpi_km2"] = {str(c): round(float((C == c).sum() * PIX * PIX / 1e6), 1) for c in range(1, 6)}
st["cpi_counts"] = {str(c): int((C == c).sum()) for c in range(1, 6)}
st["cpi_breaks"] = [round(float(b), 3) for b in brk]
st["heat_km2"] = {str(int(k)): round(float(((heat == k) & mask).sum() * PIX * PIX / 1e6), 1) for k in range(1, 8)}
st["generated"] = datetime.date.today().isoformat()
# site tiers from the new priority at the site location
for f in d["sites"]["features"]:
    lon, lat = f["geometry"]["coordinates"]; x, y, _ = to_utm.TransformPoint(lon, lat); r_, c_ = px(x, y)
    pr = f["properties"]; pr["c"] = int(C[r_, c_]) or 1; pr["h"] = int(heat[r_, c_])
    pr["v"] = round(float(P[r_, c_]), 3); pr["s"] = round(float(S[r_, c_]), 2); pr["p"] = round(float(Wk[r_, c_]), 2); pr["sh"] = round(float(D[r_, c_]), 2)
json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
log(f"{OUT}  {os.path.getsize(OUT) / 1e6:.1f} MB")
# GIS copies for ArcGIS Pro
np.save(os.path.join(HERE, "street_trees_v4_utm.npy"), street)
