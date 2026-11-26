# Parameter test on the four validation windows: does a lower height cut / smaller window find the missed trees?
# Shows imagery | CHM heights | detections (current vs relaxed).
import os, io, math, urllib.request
import numpy as np
from osgeo import gdal
from scipy import ndimage
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread
gdal.UseExceptions()
ROOT = r"C:\GIS\Madinah_Map"
TILES = [os.path.join(ROOT, "data", "canopy_meta", f"{k}.tif") for k in ("122132133", "122132311", "122133022", "122133200")]
VD = os.path.join(ROOT, "data", "existing_trees", "validation")
vrt = gdal.BuildVRT("/vsimem/c.vrt", TILES); gt = vrt.GetGeoTransform(); b = vrt.GetRasterBand(1)
SAMPLES = {"A_residential": [39.585, 24.487], "B_palm_grove": [39.612, 24.432], "C_park_avenue": [39.640, 24.472], "D_near_Haram": [39.603, 24.461]}
R = 6378137.0; Z, N = 18, 3
def detect(h, min_h, ws, wt, tall=10):
    hf = ndimage.gaussian_filter(h.astype(np.float32), 1.0); can = h >= min_h
    pk = can & (((hf == ndimage.maximum_filter(hf, ws)) & (hf < tall)) | ((hf == ndimage.maximum_filter(hf, wt)) & (hf >= tall)))
    lab, n = ndimage.label(pk, ndimage.generate_binary_structure(2, 2))
    if not n: return np.zeros((0, 2))
    return np.array(ndimage.center_of_mass(pk, lab, range(1, n + 1)))
out = {}
for name, (lo, la) in SAMPLES.items():
    n2 = 2 ** Z; tx = (lo + 180) / 360 * n2; ty = (1 - math.log(math.tan(math.radians(la)) + 1 / math.cos(math.radians(la))) / math.pi) / 2 * n2
    x0, y0 = int(tx) - N // 2, int(ty) - N // 2
    img = np.zeros((256 * N, 256 * N, 3))
    for i in range(N):
        for j in range(N):
            u = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{Z}/{y0 + j}/{x0 + i}"
            a = imread(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()), format="jpg")
            img[j * 256:(j + 1) * 256, i * 256:(i + 1) * 256] = a[..., :3] / 255.0
    # tile pixel -> mercator metres
    res = 2 * math.pi * R / (256 * n2)
    mx0 = x0 * 256 * res - math.pi * R; my0 = math.pi * R - y0 * 256 * res
    span = 256 * N * res
    c0 = int((mx0 - gt[0]) / gt[1]); r0 = int((gt[3] - my0) / -gt[5]); nn = int(span / gt[1])
    h = b.ReadAsArray(c0, r0, nn, nn)
    sc = (256 * N) / nn
    A = detect(h, 3, 5, 7); B = detect(h, 2, 3, 5)
    fig, ax = plt.subplots(1, 3, figsize=(22, 7.6), dpi=80)
    ax[0].imshow(img); ax[0].set_title(f"{name}: imagery")
    ax[1].imshow(np.where(h > 0, h, np.nan), cmap="viridis", vmin=0, vmax=12); ax[1].set_title(f"Meta CHM height (m), max {h.max()}")
    ax[2].imshow(img); ax[2].scatter(A[:, 1] * sc, A[:, 0] * sc, s=30, facecolors="none", edgecolors="#ff2d55", lw=1.3, label=f"current {len(A)}")
    ax[2].scatter(B[:, 1] * sc, B[:, 0] * sc, s=8, c="#00e5ff", label=f"relaxed {len(B)}"); ax[2].legend(loc="lower left")
    for a_ in ax: a_.set_axis_off()
    plt.tight_layout(); plt.savefig(os.path.join(VD, f"tune_{name}.png")); plt.close()
    out[name] = (len(A), len(B)); print(name, len(A), len(B))
print(out)
