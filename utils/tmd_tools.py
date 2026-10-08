"""
tmd_tools.py — ฟังก์ชันเสริมสำหรับข้อมูลเรดาร์กรมอุตุนิยมวิทยา (TMD)
====================================================================

* จุดอ้างอิงของเคสพายุลูกเห็บเชียงของ (23 เม.ย. 2020)
* แปลงพิกัด lon/lat ↔ x/y (UTM) ↔ pixel
* แปลง dBZ → rain rate (Z–R + hail cap)
* อนุกรมเวลา ณ จุด (point time series)
* advection-based temporal interpolation (เช่น 15 → 5 นาที)
* แปลงผล T-DaTing (พิกัด pixel) → GeoDataFrame พิกัด UTM ที่ถูกต้อง
"""

import datetime as _dt

import numpy as np

# ---------------------------------------------------------------------------
# จุดอ้างอิง (ชื่อ, lon, lat, marker)
# ---------------------------------------------------------------------------
RADAR_LONLAT = (99.8821, 19.9632)          # จุดศูนย์กลางของกริด CAPPI (เรดาร์เชียงราย)
CHIANG_KHONG = (100.4054, 20.2633)         # ที่ว่าการอำเภอเชียงของ
CHIANG_SAEN = (100.0870, 20.2750)          # อำเภอเชียงแสน
CHIANG_RAI = (99.8325, 19.9105)            # อำเภอเมืองเชียงราย

POIS = [
    ("CRI radar", *RADAR_LONLAT, "^", (4, -4)),
    ("Chiang Khong", *CHIANG_KHONG, "*", (5, 4)),
    ("Chiang Saen", *CHIANG_SAEN, "o", (-5, 4)),
]


# ---------------------------------------------------------------------------
# พิกัด
# ---------------------------------------------------------------------------
def lonlat_to_xy(metadata, lon, lat):
    """lon/lat (WGS84) → x, y ใน projection ของข้อมูล (เมตร)."""
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", metadata["projection"], always_xy=True)
    return tr.transform(lon, lat)


def xy_to_pixel(metadata, x, y):
    """x, y (เมตร) → (col, row) ของกริด (เลขทศนิยม)."""
    col = (np.asarray(x) - metadata["x1"]) / metadata["xpixelsize"] - 0.5
    row = (metadata["y2"] - np.asarray(y)) / metadata["ypixelsize"] - 0.5
    return col, row


def pixel_to_xy(metadata, col, row):
    """(col, row) → x, y (เมตร) ที่จุดกึ่งกลาง pixel.

    ⚠️ ผลของ T-DaTing (cen_x, cen_y, cont) เป็น *pixel* ต้องแปลงด้วยฟังก์ชันนี้
    ก่อนบันทึกเป็น GIS layer
    """
    x = metadata["x1"] + (np.asarray(col, dtype=float) + 0.5) * metadata["xpixelsize"]
    y = metadata["y2"] - (np.asarray(row, dtype=float) + 0.5) * metadata["ypixelsize"]
    return x, y


def range_box(metadata, radius_km=165.0):
    """กรอบสี่เหลี่ยมรอบเรดาร์ (x1, x2, y1, y2) ครอบคลุมรัศมีใช้งาน."""
    cx = (metadata["x1"] + metadata["x2"]) / 2
    cy = (metadata["y1"] + metadata["y2"]) / 2
    h = radius_km * 1000.0
    return (cx - h, cx + h, cy - h, cy + h)


def zoom_box(metadata, lon, lat, half_width_km):
    """กรอบสี่เหลี่ยม (x1, x2, y1, y2) รอบจุด lon/lat สำหรับซูมแผนที่."""
    x, y = lonlat_to_xy(metadata, lon, lat)
    h = half_width_km * 1000.0
    return (x - h, x + h, y - h, y + h)


def distance_to_radar_km(metadata):
    """ระยะ (km) ของทุก pixel จากจุดศูนย์กลางกริด (ตำแหน่งเรดาร์)."""
    ny = int(round((metadata["y2"] - metadata["y1"]) / metadata["ypixelsize"]))
    nx = int(round((metadata["x2"] - metadata["x1"]) / metadata["xpixelsize"]))
    rr, cc = np.mgrid[0:ny, 0:nx]
    return np.hypot(cc - (nx - 1) / 2, rr - (ny - 1) / 2) * metadata["xpixelsize"] / 1000.0


# ---------------------------------------------------------------------------
# Z–R
# ---------------------------------------------------------------------------
ZR_SETS = {
    "Marshall-Palmer": (200.0, 1.6),
    "Rosenfeld tropical": (250.0, 1.2),
    "WSR-88D convective": (300.0, 1.4),
}


def dbz_to_rainrate(dbz, a=200.0, b=1.6, hail_cap=55.0, min_dbz=15.0):
    """dBZ → rain rate (mm/h) ด้วย Z = a R^b

    * hail_cap : ตัดค่า dBZ ที่สูงกว่านี้ (สัญญาณจากลูกเห็บ) ก่อนแปลง ใส่ None เพื่อไม่ตัด
    * min_dbz  : ค่าต่ำกว่านี้ถือว่าไม่มีฝน (R = 0)
    * NaN (นอกรัศมีเรดาร์) คงเป็น NaN
    """
    dbz = np.asarray(dbz, dtype=float)
    z = dbz if hail_cap is None else np.minimum(dbz, hail_cap)
    with np.errstate(invalid="ignore", over="ignore"):
        r = (10.0 ** (z / 10.0) / a) ** (1.0 / b)
        r = np.where(dbz >= min_dbz, r, 0.0)
    r[~np.isfinite(dbz)] = np.nan
    return r


# ---------------------------------------------------------------------------
# อนุกรมเวลา ณ จุด
# ---------------------------------------------------------------------------
def point_series(cube, metadata, lon, lat, radius_km=3.0, stat="max"):
    """ค่าสถิติ (max/mean) ภายในรัศมี radius_km รอบจุด lon/lat สำหรับทุกเวลา."""
    x, y = lonlat_to_xy(metadata, lon, lat)
    c0, r0 = xy_to_pixel(metadata, x, y)
    ny, nx = cube.shape[-2:]
    rr, cc = np.mgrid[0:ny, 0:nx]
    d = np.hypot(cc - c0, rr - r0) * metadata["xpixelsize"] / 1000.0
    m = d <= radius_km
    f = {"max": np.nanmax, "mean": np.nanmean}[stat]
    sub = cube[..., m]
    return f(sub, axis=-1)


# ---------------------------------------------------------------------------
# Advection interpolation
# ---------------------------------------------------------------------------
def advection_interpolate(cube, metadata, n_sub=3, fill_value=0.0, motion_method="LK",
                          to_dbr=None):
    """เพิ่มความละเอียดเวลาด้วย advection interpolation.

    cube : (t, y, x) — ช่วงเวลาเท่ากัน (metadata["accutime"] นาที)
    n_sub : จำนวนช่วงย่อยต่อ 1 ช่วงเดิม (15 นาที, n_sub=3 → 5 นาที)
    to_dbr : ฟังก์ชันแปลง cube ก่อนหา motion field (เช่น dBZ ใช้ได้เลย, mm/h ควรแปลงเป็น dBR)
    คืนค่า (cube_ใหม่, timestamps_ใหม่, motion_fields)
    """
    from pysteps import motion
    from scipy.ndimage import map_coordinates

    oflow = motion.get_method(motion_method)
    mask = np.all(np.isfinite(cube), axis=0)
    data = np.where(np.isfinite(cube), cube, fill_value)
    mfield = data if to_dbr is None else to_dbr(data)
    ny, nx = data.shape[1:]
    yy, xx = np.mgrid[0:ny, 0:nx].astype(float)
    dt_min = float(metadata["accutime"])
    ts = list(metadata["timestamps"])

    out, times, vels = [data[0]], [ts[0]], []
    for i in range(len(data) - 1):
        i0 = max(0, i - 1)                       # ใช้ภาพก่อนหน้าด้วยถ้ามี (เสถียรกว่า)
        V = oflow(mfield[i0:i + 2], verbose=False)
        vels.append(V)
        for k in range(1, n_sub):
            w = k / n_sub
            a = map_coordinates(data[i], (yy - w * V[1], xx - w * V[0]), order=1,
                                mode="constant", cval=fill_value)
            b = map_coordinates(data[i + 1], (yy + (1 - w) * V[1], xx + (1 - w) * V[0]),
                                order=1, mode="constant", cval=fill_value)
            out.append((1 - w) * a + w * b)
            times.append(ts[i] + _dt.timedelta(minutes=dt_min * w))
        out.append(data[i + 1])
        times.append(ts[i + 1])
    out = np.stack(out)
    out[:, ~mask] = np.nan
    return out, np.array(times), np.stack(vels)


# ---------------------------------------------------------------------------
# T-DaTing → GIS
# ---------------------------------------------------------------------------
def track_table(track_list, metadata):
    """ตารางสรุปของแต่ละ track: เวลา, อายุ, ระยะทาง, ความเร็ว, ทิศ, dBZ สูงสุด."""
    import pandas as pd
    rows = []
    px_km = metadata["xpixelsize"] / 1000.0
    for k, tr in enumerate(track_list):
        x, y = pixel_to_xy(metadata, tr.cen_x.values, tr.cen_y.values)
        t = pd.to_datetime(tr.time.values)
        life = (t[-1] - t[0]).total_seconds() / 60.0
        dist = np.sum(np.hypot(np.diff(x), np.diff(y))) / 1000.0
        dx, dy = x[-1] - x[0], y[-1] - y[0]
        rows.append({
            "track_id": k + 1,
            "start_utc": t[0], "end_utc": t[-1],
            "n_frames": len(tr), "lifetime_min": life,
            "path_km": dist,
            "speed_kmh": dist / (life / 60.0) if life > 0 else np.nan,
            "direction_to_deg": (np.degrees(np.arctan2(dx, dy)) + 360) % 360,
            "max_dbz": float(np.nanmax(tr.max_ref)),
            "max_area_km2": float(np.nanmax(tr.area)) * px_km ** 2,
        })
    return pd.DataFrame(rows)


def tracks_to_gdf(track_list, metadata):
    """คืนค่า (points_gdf, lines_gdf) ในพิกัดของข้อมูล (เช่น UTM 47N) — เปิดใน QGIS ได้ทันที."""
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import LineString, Point

    pts, lines = [], []
    for k, tr in enumerate(track_list):
        x, y = pixel_to_xy(metadata, tr.cen_x.values, tr.cen_y.values)
        for xi, yi, (_, row) in zip(x, y, tr.iterrows()):
            pts.append({"track_id": k + 1, "time_utc": pd.Timestamp(row.time).isoformat(),
                        "max_dbz": float(row.max_ref),
                        "area_km2": float(row.area) * (metadata["xpixelsize"] / 1000) ** 2,
                        "geometry": Point(float(xi), float(yi))})
        if len(x) >= 2:
            lines.append({"track_id": k + 1,
                          "start_utc": pd.Timestamp(tr.time.iloc[0]).isoformat(),
                          "end_utc": pd.Timestamp(tr.time.iloc[-1]).isoformat(),
                          "max_dbz": float(np.nanmax(tr.max_ref)), "n_frames": len(tr),
                          "geometry": LineString(list(zip(x, y)))})
    crs = metadata["projection"]
    return (gpd.GeoDataFrame(pts, geometry="geometry", crs=crs),
            gpd.GeoDataFrame(lines, geometry="geometry", crs=crs))


def contour_xy(cont, metadata):
    """แปลง contour ของ T-DaTing (list ของ array [row, col]) → list ของ (x, y) เมตร."""
    out = []
    for c in cont:
        c = np.asarray(c)
        x, y = pixel_to_xy(metadata, c[:, 1], c[:, 0])
        out.append((x, y))
    return out
