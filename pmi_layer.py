# Map 02 colour layer: Pedestrian Movement Index as a smooth 30 m surface (no hexagons, no circles).
# The 250 m PMI grid is rasterised at 30 m and smoothed (Gaussian, sigma 120 m) so the colour follows
# the built-up area instead of cell edges. Added to madinah_data_v4.json as layers["pmi"].
import os, json, math, base64
import numpy as np
from osgeo import gdal, ogr, osr
from scipy.ndimage import gaussian_filter
gdal.UseExceptions(); ogr.UseExceptions()
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(H)
GDB = os.path.join(ROOT, "Madinah_City.gdb"); OUT = os.path.join(H, "madinah_data_v4.json")
PIX = 30.0
UTM = osr.SpatialReference(); UTM.ImportFromEPSG(32637)
ds = ogr.Open(GDB); f = ds.GetLayerByName("Madinah_City_Boundary").GetNextFeature(); g = f.GetGeometryRef()
x0, x1, y0, y1 = g.GetEnvelope()
x0 = math.floor(x0 / PIX) * PIX - PIX; y1 = math.ceil(y1 / PIX) * PIX + PIX
NX = int(math.ceil((x1 - x0) / PIX)) + 2; NY = int(math.ceil((y1 - y0) / PIX)) + 2
GT = (x0, PIX, 0, y1, 0, -PIX)
def mem():
    r = gdal.GetDriverByName("MEM").Create("", NX, NY, 1, gdal.GDT_Float32); r.SetGeoTransform(GT); r.SetProjection(UTM.ExportToWkt()); return r
def ras(layer, attr=None):
    v = gdal.VectorTranslate("", GDB, options=gdal.VectorTranslateOptions(format="Memory", dstSRS="EPSG:32637", layers=[layer]))
    r = mem(); gdal.RasterizeLayer(r, [1], v.GetLayer(0), burn_values=[] if attr else [1], options=[f"ATTRIBUTE={attr}"] if attr else [])
    return r.GetRasterBand(1).ReadAsArray()
mask = ras("Madinah_City_Boundary") > 0
pmi = ras("Pedestrian_Movement_Hex", "PMI")
sm = gaussian_filter(pmi, 4.0)                 # 4 px x 30 m = 120 m
hi = np.percentile(sm[mask & (sm > 0)], 99)
v = np.clip(sm / hi, 0, 1)
valid = mask & (v > 0.03)
# PMI colours (Very Low -> Very High) as a continuous ramp
stops = [(0.0, "#2a2350", 0), (0.06, "#2a2350", 70), (0.25, "#5b2a86", 150), (0.45, "#a3307e", 190), (0.7, "#ec6a4c", 215), (1.0, "#ffd166", 235)]
rgb = lambda h: [int(h[i:i + 2], 16) for i in (1, 3, 5)]
xs = [s[0] for s in stops]
src = mem(); src.GetRasterBand(1).WriteArray(np.where(valid, v, -1).astype(np.float32))
w = gdal.Warp("", src, format="MEM", dstSRS="EPSG:3857", resampleAlg="bilinear", xRes=PIX, yRes=PIX, srcNodata=-1, dstNodata=-1)
a = w.GetRasterBand(1).ReadAsArray(); gt = w.GetGeoTransform()
out = np.zeros(a.shape + (4,), np.uint8)
for ch in range(3): out[..., ch] = np.interp(a, xs, [rgb(s[1])[ch] for s in stops])
out[..., 3] = np.where(a >= 0, np.interp(a, xs, [s[2] for s in stops]), 0)
m = gdal.GetDriverByName("MEM").Create("", a.shape[1], a.shape[0], 4, gdal.GDT_Byte)
for i in range(4): m.GetRasterBand(i + 1).WriteArray(out[..., i])
gdal.GetDriverByName("PNG").CreateCopy("/vsimem/p.png", m, options=["ZLEVEL=9"])
fh = gdal.VSIFOpenL("/vsimem/p.png", "rb"); gdal.VSIFSeekL(fh, 0, 2); n = gdal.VSIFTellL(fh); gdal.VSIFSeekL(fh, 0, 0); b = gdal.VSIFReadL(1, n, fh); gdal.VSIFCloseL(fh)
merc = osr.SpatialReference(); merc.ImportFromEPSG(3857); merc.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326); wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
t = osr.CoordinateTransformation(merc, wgs); h_, w_ = a.shape
xa, xb, ya, yb = gt[0], gt[0] + w_ * gt[1], gt[3], gt[3] + h_ * gt[5]
co = [[round(p[0], 6), round(p[1], 6)] for p in (t.TransformPoint(xa, ya), t.TransformPoint(xb, ya), t.TransformPoint(xb, yb), t.TransformPoint(xa, yb))]
d = json.load(open(OUT, encoding="utf-8"))
d["layers"]["pmi"] = {"img": "data:image/png;base64," + base64.b64encode(b).decode(), "co": co}
json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("pmi layer", round(len(b) / 1e3), "KB", "valid km2", round(valid.sum() * PIX * PIX / 1e6))
