"""
data_io.py — อ่าน/เขียนข้อมูลเรดาร์ในรูปแบบ NetCDF ที่ใช้ในรายวิชา
=====================================================================

ไฟล์ NetCDF ในโฟลเดอร์ ``data/`` ถูกเตรียมโดย ``00_prepare_data.ipynb``
โครงสร้างไฟล์:

* ตัวแปร ``precip(time, y, x)``  [mm/h]  (NaN = นอกรัศมีเรดาร์ / ไม่มีข้อมูล)
* พิกัด ``x``, ``y`` (เมตร, จุดกึ่งกลาง pixel) และ ``time`` (UTC)
* global attributes = metadata ของ pysteps (projection, x1, x2, y1, y2, ...)

ฟังก์ชัน ``load_radar_nc`` คืนค่า ``(precip, metadata)`` ในรูปแบบเดียวกับ
``pysteps.io.read_timeseries`` จึงใช้กับทุกฟังก์ชันของ pysteps ได้ทันที
"""

import datetime as _dt
import json as _json

import numpy as np

_NUMERIC_KEYS = (
    "x1", "x2", "y1", "y2", "xpixelsize", "ypixelsize", "accutime",
    "zerovalue", "threshold", "zr_a", "zr_b",
)
_STRING_KEYS = ("projection", "cartesian_unit", "yorigin", "institution",
                "unit", "transform", "product", "source", "license")


def save_radar_nc(path, precip, metadata, extra_attrs=None,
                  least_significant_digit=2):
    """บันทึก precip (t, y, x) + metadata ลง NetCDF4 แบบบีบอัด (zlib)."""
    import netCDF4

    precip = np.asarray(precip, dtype="float32")
    if precip.ndim == 2:
        precip = precip[None]
    nt, ny, nx = precip.shape

    with netCDF4.Dataset(path, "w", format="NETCDF4") as ds:
        ds.createDimension("time", nt)
        ds.createDimension("y", ny)
        ds.createDimension("x", nx)

        # pixel centres
        xps, yps = float(metadata["xpixelsize"]), float(metadata["ypixelsize"])
        x = float(metadata["x1"]) + xps * (np.arange(nx) + 0.5)
        y = float(metadata["y1"]) + yps * (np.arange(ny) + 0.5)
        if metadata.get("yorigin", "upper") == "upper":
            y = y[::-1]

        vx = ds.createVariable("x", "f8", ("x",))
        vx[:] = x
        vx.units, vx.standard_name = "m", "projection_x_coordinate"
        vy = ds.createVariable("y", "f8", ("y",))
        vy[:] = y
        vy.units, vy.standard_name = "m", "projection_y_coordinate"

        t0 = _dt.datetime(1970, 1, 1)
        secs = [(ts - t0).total_seconds() for ts in metadata["timestamps"]]
        vt = ds.createVariable("time", "f8", ("time",))
        vt[:] = secs
        vt.units = "seconds since 1970-01-01 00:00:00"
        vt.calendar, vt.standard_name = "standard", "time"

        crs = ds.createVariable("crs", "i4")
        crs.proj4 = metadata["projection"]

        vp = ds.createVariable(
            "precip", "f4", ("time", "y", "x"), zlib=True, complevel=6,
            least_significant_digit=least_significant_digit,
            fill_value=np.float32(-999.0), chunksizes=(1, ny, nx),
        )
        vp.units = metadata.get("unit", "mm/h")
        vp.long_name = ("radar reflectivity" if str(metadata.get("unit")) == "dBZ"
                        else "precipitation rate")
        vp.grid_mapping = "crs"
        vp[:] = np.ma.masked_invalid(precip)

        for k in _NUMERIC_KEYS:
            if k in metadata and metadata[k] is not None:
                setattr(ds, k, float(metadata[k]))
        for k in _STRING_KEYS:
            if k in metadata and metadata[k] is not None:
                setattr(ds, k, str(metadata[k]))
        if extra_attrs:
            for k, v in extra_attrs.items():
                setattr(ds, k, v if isinstance(v, (str, int, float))
                        else _json.dumps(v, default=str))
        ds.Conventions = "CF-1.8"
        ds.history = f"created {_dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC"


def load_radar_nc(path):
    """อ่านไฟล์ NetCDF ของรายวิชา คืนค่า (precip [t, y, x], metadata dict)."""
    import netCDF4

    with netCDF4.Dataset(path) as ds:
        precip = ds["precip"][:].filled(np.nan).astype("float64")
        secs = ds["time"][:]
        meta = {}
        for k in ds.ncattrs():
            v = getattr(ds, k)
            if k in _NUMERIC_KEYS:
                v = float(v)
            meta[k] = v
    meta["timestamps"] = np.array(
        [_dt.datetime(1970, 1, 1) + _dt.timedelta(seconds=float(s)) for s in secs]
    )
    if meta.get("transform") in ("None", "", None):
        meta["transform"] = None
    meta.setdefault("zerovalue", 0.0)
    meta.setdefault("threshold", 0.0)
    meta.setdefault("unit", "mm/h")
    meta.setdefault("yorigin", "upper")
    meta.setdefault("cartesian_unit", "m")
    return precip, meta
