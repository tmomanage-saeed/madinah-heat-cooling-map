# -*- coding: utf-8 -*-
"""
Existing trees of Madinah: one point per tree from the Meta/WRI 1 m canopy height map.

Data   : Meta & WRI Global Canopy Height 1 m (Tolan et al. 2024, Remote Sensing of Environment 300:113888),
         tiles 122132133, 122132311, 122133022, 122133200 (EPSG:3857, 1.194 m pixels, height in whole metres).
Method : local-maxima treetop detection on the canopy height model (standard CHM method,
         e.g. Popescu & Wynne 2004; Dalponte & Coomes 2016):
  1. smooth the CHM with a Gaussian (sigma 1 px) to split integer-height plateaus;
  2. a pixel is a treetop if it is the highest point in its window and the tree is >= 3 m tall;
     window 5 px (~5.4 m) for trees < 10 m, 7 px (~7.6 m) for taller trees (taller trees have wider crowns);
  3. every canopy pixel (>= 3 m) is given to its nearest treetop within 9 m -> crown area per tree.
Output : C:\\GIS\\Madinah_Map\\data\\existing_trees\\Existing_Trees_Meta1m.gpkg (points, WGS84) + summary JSON.
RUN    : "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" -I existing_trees.py
"""
import os, json, math, time
import numpy as np
from osgeo import gdal, ogr, osr
from scipy import ndimage
gdal.UseExceptions(); ogr.UseExceptions()

ROOT = r"C:\GIS\Madinah_Map"
TILES = [os.path.join(ROOT, "data", "canopy_meta", f"{k}.tif") for k in ("122132133", "122132311", "122133022", "122133200")]
OUTD = os.path.join(ROOT, "data", "existing_trees"); os.makedirs(OUTD, exist_ok=True)
GDB = os.path.join(ROOT, "Madinah_City.gdb")
MIN_H, SIGMA, WIN_S, WIN_T, TALL, CROWN_R = 3, 1.0, 5, 7, 10, 8      # CROWN_R in px (~9 m)
BLK, PAD = 2048, 16
R = 6378137.0
def log(m): print(m, flush=True)

vrt = gdal.BuildVRT("/vsimem/chm.vrt", TILES)
gt = vrt.GetGeoTransform(); band = vrt.GetRasterBand(1)
W3857 = osr.SpatialReference(); W3857.ImportFromEPSG(3857); W3857.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
WGS = osr.SpatialReference(); WGS.ImportFromEPSG(4326); WGS.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

# boundary masks (city boundary and built-up area) on a 12 m grid in EPSG:3857
gds = ogr.Open(GDB)
def layer_geom(name):
    l = gds.GetLayerByName(name)
    if l is None: return None
    f = l.GetNextFeature(); g = f.GetGeometryRef().Clone(); g.TransformTo(W3857); return g
bnd = layer_geom("Madinah_City_Boundary"); bu = layer_geom("Madinah_BuiltUp_Boundary")
x0, x1, y0, y1 = bnd.GetEnvelope()
c0 = int((x0 - gt[0]) / gt[1]); c1 = int(math.ceil((x1 - gt[0]) / gt[1]))
r0 = int((gt[3] - y1) / -gt[5]); r1 = int(math.ceil((gt[3] - y0) / -gt[5]))
c0, r0 = max(c0, 0), max(r0, 0); c1, r1 = min(c1, vrt.RasterXSize), min(r1, vrt.RasterYSize)
log(f"Window {c1 - c0} x {r1 - r0} px")
MS = 12.0
mgt = (gt[0] + c0 * gt[1], MS, 0, gt[3] + r0 * gt[5], 0, -MS)
mw, mh = int((c1 - c0) * gt[1] / MS) + 2, int((r1 - r0) * -gt[5] / MS) + 2
def mask_of(g):
    m = gdal.GetDriverByName("MEM").Create("", mw, mh, 1, gdal.GDT_Byte); m.SetGeoTransform(mgt); m.SetProjection(W3857.ExportToWkt())
    drv = ogr.GetDriverByName("Memory"); ds = drv.CreateDataSource(""); l = ds.CreateLayer("b", W3857, ogr.wkbMultiPolygon)
    f = ogr.Feature(l.GetLayerDefn()); f.SetGeometry(g); l.CreateFeature(f)
    gdal.RasterizeLayer(m, [1], l, burn_values=[1]); return m.GetRasterBand(1).ReadAsArray().astype(bool)
MB = mask_of(bnd); MU = mask_of(bu) if bu is not None else None

xs, ys, hs_, cr_ = [], [], [], []
canopy_px = 0
fp = ndimage.generate_binary_structure(2, 2)
t0 = time.time()
for rb in range(r0, r1, BLK):
    ra, rz = max(rb - PAD, 0), min(rb + BLK + PAD, r1)
    strip = band.ReadAsArray(c0, ra, c1 - c0, rz - ra)
    for cb in range(0, c1 - c0, BLK):
        ca, cz = max(cb - PAD, 0), min(cb + BLK + PAD, c1 - c0)
        h = strip[:, ca:cz]
        if h.max() < MIN_H: continue
        hf = ndimage.gaussian_filter(h.astype(np.float32), SIGMA)
        can = h >= MIN_H
        peak = can & (((hf == ndimage.maximum_filter(hf, WIN_S)) & (hf < TALL)) | ((hf == ndimage.maximum_filter(hf, WIN_T)) & (hf >= TALL)))
        lab, n = ndimage.label(peak, fp)                     # merge tied neighbours into one top
        if n == 0: continue
        com = np.array(ndimage.center_of_mass(peak, lab, range(1, n + 1)))
        pr, pc = np.round(com[:, 0]).astype(int), np.round(com[:, 1]).astype(int)
        # crowns: canopy pixels -> nearest top within CROWN_R
        mk = np.zeros(h.shape, np.int32); mk[pr, pc] = np.arange(1, n + 1)
        dist, (ir, ic) = ndimage.distance_transform_edt(mk == 0, return_indices=True)
        own = np.where(can & (dist <= CROWN_R), mk[ir, ic], 0)
        crown = np.bincount(own.ravel(), minlength=n + 1)[1:]
        # keep tops in the core of this block (no double counting in the overlap)
        gr = ra + pr; gc = c0 + ca + pc
        core = (gr >= rb) & (gr < min(rb + BLK, r1)) & (ca + pc >= cb) & (ca + pc < min(cb + BLK, c1 - c0))
        # canopy area counted on the core only
        rr0, cc0 = rb - ra, cb - ca
        canopy_core = can[rr0:rr0 + min(BLK, r1 - rb), cc0:cc0 + min(BLK, c1 - c0 - cb)]
        X = gt[0] + (gc + 0.5) * gt[1]; Y = gt[3] + (gr + 0.5) * gt[5]
        mi = ((Y - mgt[3]) / -MS).astype(int); mj = ((X - mgt[0]) / MS).astype(int)
        inb = core & MB[np.clip(mi, 0, mh - 1), np.clip(mj, 0, mw - 1)]
        xs.append(X[inb]); ys.append(Y[inb]); hs_.append(h[pr, pc][inb]); cr_.append(crown[inb])
        # canopy area inside boundary (approximate with block-level mask lookup on 12 m cells)
        if canopy_core.any():
            cr_r, cr_c = np.nonzero(canopy_core)
            Xc = gt[0] + (c0 + cb + cr_c + 0.5) * gt[1]; Yc = gt[3] + (rb + cr_r + 0.5) * gt[5]
            canopy_px += int(MB[np.clip(((Yc - mgt[3]) / -MS).astype(int), 0, mh - 1), np.clip(((Xc - mgt[0]) / MS).astype(int), 0, mw - 1)].sum())
    log(f"  rows {rb - r0:>6}/{r1 - r0}  trees so far {sum(len(a) for a in xs):,}  {time.time() - t0:.0f}s")

X = np.concatenate(xs); Y = np.concatenate(ys); Hh = np.concatenate(hs_).astype(int)
lat_c = 24.47; px_m2 = (gt[1] * math.cos(math.radians(lat_c))) ** 2
CA = np.concatenate(cr_) * px_m2
lon = np.degrees(X / R); lat = np.degrees(2 * np.arctan(np.exp(Y / R)) - math.pi / 2)
in_bu = None
if MU is not None:
    in_bu = MU[np.clip(((Y - mgt[3]) / -MS).astype(int), 0, mh - 1), np.clip(((X - mgt[0]) / MS).astype(int), 0, mw - 1)]

# write GeoPackage
gp = os.path.join(OUTD, "Existing_Trees_Meta1m.gpkg")
if os.path.exists(gp): os.remove(gp)
ds = ogr.GetDriverByName("GPKG").CreateDataSource(gp)
l = ds.CreateLayer("Existing_Trees", WGS, ogr.wkbPoint)
for nm, tp in [("height_m", ogr.OFTInteger), ("crown_m2", ogr.OFTReal), ("built_up", ogr.OFTInteger)]:
    l.CreateField(ogr.FieldDefn(nm, tp))
l.StartTransaction()
for i in range(len(X)):
    f = ogr.Feature(l.GetLayerDefn())
    f.SetField("height_m", int(Hh[i])); f.SetField("crown_m2", round(float(CA[i]), 1)); f.SetField("built_up", int(in_bu[i]) if in_bu is not None else -1)
    g = ogr.Geometry(ogr.wkbPoint); g.AddPoint_2D(float(lon[i]), float(lat[i])); f.SetGeometry(g); l.CreateFeature(f)
l.CommitTransaction(); ds = None
np.savez_compressed(os.path.join(OUTD, "existing_trees.npz"), lon=lon, lat=lat, h=Hh, crown=CA, bu=in_bu if in_bu is not None else np.zeros(0))

q = lambda v, p: round(float(np.percentile(v, p)), 1)
summ = {"source": "Meta/WRI Global Canopy Height 1 m (Tolan et al. 2024)", "method": "local-maxima treetop detection, sigma 1 px, window 5 px (<10 m) / 7 px (>=10 m), min height 3 m",
        "trees_in_city_boundary": int(len(X)),
        "trees_in_built_up": int(in_bu.sum()) if in_bu is not None else None,
        "canopy_km2_in_city_boundary": round(canopy_px * px_m2 / 1e6, 2),
        "height_m": {"median": q(Hh, 50), "p25": q(Hh, 25), "p75": q(Hh, 75)},
        "crown_m2": {"mean": round(float(CA.mean()), 1), "median": q(CA, 50), "p25": q(CA, 25), "p75": q(CA, 75)},
        "by_height": {f"{a}-{b} m": int(((Hh >= a) & (Hh < b)).sum()) for a, b in [(3, 5), (5, 8), (8, 12), (12, 99)]},
        "generated": time.strftime("%Y-%m-%d")}
json.dump(summ, open(os.path.join(OUTD, "Existing_Trees_summary.json"), "w"), indent=1)
log(json.dumps(summ, indent=1))
