# Heat zones (land surface temperature classes) -> WGS84 GeoJSON for the web map.
# Polygons are dissolved per class and lightly simplified (12 m, below the 30 m pixel size).
import json
from osgeo import ogr, osr; ogr.UseExceptions()
ds = ogr.Open(r'C:\GIS\Madinah_Map\Madinah_City.gdb')
l = ds.GetLayerByName('Heat_Zones_Madinah')
src = l.GetSpatialRef(); dst = osr.SpatialReference(); dst.ImportFromEPSG(4326)
dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
tr = osr.CoordinateTransformation(src, dst)
by = {}
for f in l:
    g = f.GetGeometryRef().Clone(); c = f.GetField('gridcode')
    by.setdefault(c, []).append(g)
feats = []; nv = 0
for c, gs in sorted(by.items()):
    u = ogr.Geometry(ogr.wkbMultiPolygon)
    for g in gs:
        g = g.MakeValid() if not g.IsValid() else g
        for i in range(g.GetGeometryCount()) if g.GetGeometryType() in (ogr.wkbMultiPolygon, ogr.wkbMultiPolygon25D) else [None]:
            u.AddGeometry(g.GetGeometryRef(i) if i is not None else g)
    s = u.SimplifyPreserveTopology(12.0); s.Transform(tr)
    gj = json.loads(s.ExportToJson())
    def rnd(o): return [rnd(x) for x in o] if isinstance(o[0], list) else [round(o[0], 5), round(o[1], 5)]
    gj['coordinates'] = rnd(gj['coordinates'])
    nv += s.GetPointCount() if s.GetGeometryCount() == 0 else sum(s.GetGeometryRef(i).GetGeometryRef(0).GetPointCount() for i in range(s.GetGeometryCount()) if s.GetGeometryRef(i).GetGeometryCount())
    feats.append({"type": "Feature", "properties": {"h": c, "r": f"{30+5*c}-{35+5*c} °C"}, "geometry": gj})
out = {"type": "FeatureCollection", "features": feats}
json.dump(out, open('heat_zones.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
import os; print('classes', len(feats), 'approx outer vertices', nv, 'MB', round(os.path.getsize('heat_zones.json')/1e6, 2))
