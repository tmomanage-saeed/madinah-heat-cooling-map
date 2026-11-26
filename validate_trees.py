# Visual check of the detected trees: Esri World Imagery (zoom 18, ~0.6 m) with the detected treetops on top.
# Writes one PNG per sample area to data/existing_trees/validation/.
import os, sys, io, math, json, urllib.request
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread
OUTD = r"C:\GIS\Madinah_Map\data\existing_trees"; VD = os.path.join(OUTD, "validation"); os.makedirs(VD, exist_ok=True)
d = np.load(os.path.join(OUTD, "existing_trees.npz"))
lon, lat, h = d["lon"], d["lat"], d["h"]
SAMPLES = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {
    "A_residential": [39.585, 24.487], "B_palm_grove": [39.612, 24.432],
    "C_park_avenue": [39.640, 24.472], "D_near_Haram": [39.603, 24.461]}
Z, N = 18, 3            # 3 x 3 tiles of 256 px = ~460 m square
def tile(lo, la, z):
    n = 2 ** z; x = (lo + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(la)) + 1 / math.cos(math.radians(la))) / math.pi) / 2 * n
    return x, y
def ll(x, y, z):
    n = 2 ** z; lo = x / n * 360 - 180; la = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n)))); return lo, la
res = {}
for name, (lo, la) in SAMPLES.items():
    tx, ty = tile(lo, la, Z); x0, y0 = int(tx) - N // 2, int(ty) - N // 2
    img = np.zeros((256 * N, 256 * N, 3))
    for i in range(N):
        for j in range(N):
            u = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{Z}/{y0 + j}/{x0 + i}"
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (GIS validation script)"})
            a = imread(io.BytesIO(urllib.request.urlopen(req, timeout=30).read()), format="jpg")
            img[j * 256:(j + 1) * 256, i * 256:(i + 1) * 256] = a[..., :3] / (255.0 if a.max() > 1 else 1)
    lo0, la0 = ll(x0, y0, Z); lo1, la1 = ll(x0 + N, y0 + N, Z)
    m = (lon >= lo0) & (lon <= lo1) & (lat <= la0) & (lat >= la1)
    px = (lon[m] - lo0) / (lo1 - lo0) * 256 * N
    yy = lambda v: (1 - math.log(math.tan(math.radians(v)) + 1 / math.cos(math.radians(v))) / math.pi) / 2 * 2 ** Z
    py = np.array([(yy(v) - y0) * 256 for v in lat[m]])
    fig, ax = plt.subplots(1, 2, figsize=(16, 8.2), dpi=90)
    for k, a_ in enumerate(ax):
        a_.imshow(img); a_.set_axis_off()
        if k == 1: a_.scatter(px, py, s=26, facecolors="none", edgecolors="#ff2d55", linewidths=1.3)
    ax[0].set_title(f"{name}: imagery"); ax[1].set_title(f"{name}: {m.sum()} detected trees (red)")
    plt.tight_layout(); fp = os.path.join(VD, f"{name}.png"); plt.savefig(fp); plt.close()
    res[name] = int(m.sum()); print(name, m.sum(), fp)
print(res)
