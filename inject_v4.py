# template_v4.html + madinah_data_v4.json -> index.html (single file, data embedded)
import os, json
H = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(H, "madinah_data_v4.json"), encoding="utf-8"))
d.setdefault("umb", {"type": "FeatureCollection", "features": []})
d.setdefault("suit", {"o": [39.3, 24.2], "p": []})
js = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
t = open(os.path.join(H, "template_v4.html"), encoding="utf-8").read()
t = t.replace("<title>", "<title>v4 · ", 1) if "<title>v4" not in t else t
out = os.path.join(H, "index.html")
open(out, "w", encoding="utf-8").write(t.replace("/*__DATA__*/null", js))
print(out, round(os.path.getsize(out) / 1e6, 1), "MB")
