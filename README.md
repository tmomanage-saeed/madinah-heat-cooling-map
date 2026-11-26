# Madinah Cooling Map, v4 (surface-heat based)

Two interactive web maps for Madinah, built on the measured land surface temperature map.
There are no circles and no 1 km cells: every layer follows the real 30 m heat pixels, real streets and real buildings.

**Open:** `index.html` (single file, data embedded). The satellite basemap needs an internet connection.

## Map 01: Priority Areas for Cooling (layer by layer)

| Step | Layer | Weight | Source |
|---|---|---|---|
| 1 | Land surface temperature | 40 % | `Heat_Zones_Madinah` (land surface temperature classes, 30 m) |
| 2 | Places people use | 25 % | Mosques and schools 3, bus and malls 2.5, parks 1.5, Masjid an-Nabawi 10, within 300 m |
| 3 | Where people walk | 20 % | Pedestrian Movement Index (footpaths, destinations, built density) |
| 4 | Missing shade | 15 % | 1 − green share within about 270 m (OSM green land use) |
| = | Cooling priority | | All four combined on a 30 m grid |

- The weights are planning weights: heat first, then people.
- **Classes** are set by share of street length:

  | Class | Share of street length |
  |---|---|
  | Critical | Top 5 % |
  | Very High | 85–95 % |
  | High | 65–85 % |
  | Moderate | 40–65 % |
  | Low | Below 40 % |

- **Trees** go on both sides of every walkable street. Spacing is set for each 50 m stretch from the priority under it:

  | Priority | Critical | Very High | High | Moderate | Low |
  |---|---|---|---|---|---|
  | Tree every | 8 m | 10 m | 12 m | 16 m | 24 m |
  | Trees | 32,500 | 79,819 | 142,770 | 145,118 | 169,796 |

  - Crown: 53 m², the mean of 40,800 trees measured in Madinah (Meta/WRI 1 m canopy height).
  - Trees are not placed on buildings, roads, junction corners or the Haram plaza.
- **Result:**
  - 581,824 new trees: 570,010 street trees and 11,814 at sites.
  - Air about 0.37 °C cooler in High+ areas (124 km²) when the trees are mature. This uses +11.3 % canopy × 0.33 °C per 10 % canopy (WRI).
- **Click anywhere** to see the priority class, the four components, the street tree spacing and the expected cooling.

## Map 02: Pedestrian Movement
- The pedestrian movement colour is a smooth 30 m surface of the Pedestrian Movement Index.
- Walking corridors are coloured by flow, from purple (few people) to yellow (many).
- Animated pedestrians, 5/10/15-min walking catchments, and an A→B cool route.

## Rebuild
```
python -I heat_export.py     # heat zones -> heat_zones.json
python -I heat_priority.py   # priority grid, street trees, layers -> madinah_data_v4.json
python -I pmi_layer.py       # Map 02 pedestrian movement colour layer
python -I patch_v4.py        # template_v4.html from ../web/template.html
python -I inject_v4.py       # -> index.html
```
Use the ArcGIS Pro Python (`arcgispro-py3`). Only GDAL, numpy and scipy are needed (no arcpy).
