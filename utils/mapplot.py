"""
mapplot.py — ฟังก์ชันทำแผนที่เรดาร์คุณภาพระดับตีพิมพ์ (publication-quality)
==========================================================================

ออกแบบให้ใช้ร่วมกับ pysteps:
* ใช้ map projection ของข้อมูลจริง (อ่านจาก metadata["projection"])
* ใช้ colormap มาตรฐานของ pysteps (pysteps / STEPS-BE / BOM-RF3)
* มี coastline, borders, lakes, gridline พร้อม label lon/lat, scale bar,
  north arrow, panel label (a), (b), (c) และ colorbar ร่วม
* บันทึกรูปเป็น PNG (300 dpi) และ PDF (vector) สำหรับ journal

ตัวอย่างการใช้งาน
-----------------
>>> fig, axs = map_panels(1, 2, metadata)
>>> im = radar_map(axs[0], precip[-1], metadata, title="Observed")
>>> radar_map(axs[1], nowcast[5], metadata, title="+30 min")
>>> add_colorbar(fig, im, axs)
>>> save_figure(fig, "fig01_obs_vs_nowcast")
"""

import os
import string

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from pysteps.visualization.precipfields import get_colormap
from pysteps.visualization.utils import proj4_to_cartopy

FIG_DIR = "figures"

# ---------------------------------------------------------------------------
# 1) สไตล์รูปแบบ journal
# ---------------------------------------------------------------------------

def set_style(base_fontsize=9):
    """ตั้งค่า matplotlib ให้เหมาะกับการตีพิมพ์ (ฟอนต์ sans-serif, เส้นบาง)."""
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": base_fontsize,
        "axes.titlesize": base_fontsize + 1,
        "axes.labelsize": base_fontsize,
        "xtick.labelsize": base_fontsize - 1,
        "ytick.labelsize": base_fontsize - 1,
        "legend.fontsize": base_fontsize - 1,
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "grid.linewidth": 0.4,
        "grid.alpha": 0.5,
        "figure.dpi": 110,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,      # ฝังฟอนต์แบบ TrueType (journal ต้องการ)
        "ps.fonttype": 42,
    })


# ---------------------------------------------------------------------------
# 2) projection และการสร้าง panel
# ---------------------------------------------------------------------------

def get_crs(metadata):
    """แปลง proj4 string ใน metadata เป็น cartopy CRS."""
    return proj4_to_cartopy(metadata["projection"])


def map_panels(nrows, ncols, metadata, panel_width=3.2, extra_height=0.0, zoom=None):
    """สร้าง figure ที่มีหลาย panel ซึ่งทุก panel ใช้ projection ของข้อมูล.

    คืนค่า (fig, axs) โดย axs เป็น array 1 มิติเสมอ
    """
    crs = get_crs(metadata)
    if zoom is None:
        aspect = (metadata["y2"] - metadata["y1"]) / (metadata["x2"] - metadata["x1"])
    else:
        aspect = (zoom[3] - zoom[2]) / (zoom[1] - zoom[0])
    fig, axs = plt.subplots(
        nrows, ncols,
        figsize=(panel_width * ncols, panel_width * aspect * nrows + 0.6 + extra_height),
        subplot_kw={"projection": crs},
        squeeze=False,
        layout="constrained",
    )
    return fig, axs.ravel()


# ---------------------------------------------------------------------------
# 3) องค์ประกอบแผนที่
# ---------------------------------------------------------------------------

# ค่าตั้งต้นของ basemap (แก้ได้จาก notebook เช่น mp.BASEMAP["provinces"] = True)
BASEMAP = {"lakes": True, "provinces": False, "rivers": False}
# จุดสำคัญที่จะวาดบนทุกแผนที่: list ของ (ชื่อ, lon, lat, marker)
POINTS = []


def add_basemap(ax, resolution="10m", gridlines=True, labels=("left", "bottom"),
                lakes=None, provinces=None, rivers=None):
    """เพิ่ม coastline, พรมแดน, (จังหวัด, แม่น้ำ, ทะเลสาบ) และ gridline lon/lat."""
    lakes = BASEMAP["lakes"] if lakes is None else lakes
    provinces = BASEMAP["provinces"] if provinces is None else provinces
    rivers = BASEMAP["rivers"] if rivers is None else rivers
    ax.add_feature(cfeature.COASTLINE.with_scale(resolution),
                   linewidth=0.6, edgecolor="0.15", zorder=3)
    if provinces:
        ax.add_feature(cfeature.NaturalEarthFeature(
            "cultural", "admin_1_states_provinces_lines", "10m"),
            facecolor="none", edgecolor="0.45", linewidth=0.35, linestyle=":", zorder=3)
    ax.add_feature(cfeature.BORDERS.with_scale(resolution),
                   linewidth=0.7, edgecolor="0.2", linestyle="-", zorder=3)
    if rivers:
        ax.add_feature(cfeature.RIVERS.with_scale("10m"),
                       facecolor="none", edgecolor="#4a90c2", linewidth=0.6, zorder=3)
    if lakes:
        ax.add_feature(cfeature.LAKES.with_scale("50m"),
                       facecolor="none", edgecolor="0.6", linewidth=0.2, zorder=3)
    if gridlines:
        gl = ax.gridlines(draw_labels=True, linewidth=0.35, color="0.4",
                          alpha=0.6, linestyle="--", x_inline=False,
                          y_inline=False, zorder=4)
        gl.top_labels = "top" in labels
        gl.right_labels = "right" in labels
        gl.left_labels = "left" in labels
        gl.bottom_labels = "bottom" in labels
        gl.xlabel_style = {"size": mpl.rcParams["xtick.labelsize"], "color": "0.2"}
        gl.ylabel_style = {"size": mpl.rcParams["ytick.labelsize"], "color": "0.2"}
        gl.rotate_labels = False
        # เลือกระยะห่างของเส้นกริดให้มีประมาณ 3–5 เส้น (ป้ายไม่ซ้อนกัน)
        import matplotlib.ticker as mticker
        lon0, lon1, lat0, lat1 = ax.get_extent(ccrs.PlateCarree())
        span = max(lon1 - lon0, lat1 - lat0)
        steps = np.array([0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10])
        step = steps[np.argmin(np.abs(span / steps - 4))]
        gl.xlocator = mticker.MultipleLocator(step)
        gl.ylocator = mticker.MultipleLocator(step)
    return ax


def add_points(ax, points=None, fontsize=None, color="k"):
    """วาดจุดสำคัญ จาก list ของ (ชื่อ, lon, lat, marker[, (dx, dy) offset เป็น point])."""
    points = POINTS if points is None else points
    fs = fontsize or mpl.rcParams["font.size"] - 1
    pc = ccrs.PlateCarree()
    x0, x1, y0, y1 = ax.get_extent(pc)
    for pt in points:
        name, lon, lat, marker = pt[:4]
        off = pt[4] if len(pt) > 4 else (4, 3)
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        ax.plot(lon, lat, marker=marker, ms=6 if marker == "*" else 5,
                mfc="w" if marker == "^" else color, mec=color, mew=1.0,
                transform=pc, zorder=9)
        if name:
            ax.annotate(name, xy=(lon, lat), xycoords=pc._as_mpl_transform(ax),
                        xytext=off, textcoords="offset points", fontsize=fs,
                        ha="left" if off[0] >= 0 else "right",
                        va="bottom" if off[1] >= 0 else "top", zorder=9, color=color,
                        bbox=dict(boxstyle="round,pad=0.1", fc="w", ec="none", alpha=0.7))


def add_range_rings(ax, metadata, radii_km=(50, 100, 150), centre_xy=None,
                    color="0.35", label=True):
    """วงรัศมีรอบเรดาร์ (ค่า default: ศูนย์กลางของกริด)."""
    if centre_xy is None:
        centre_xy = ((metadata["x1"] + metadata["x2"]) / 2,
                     (metadata["y1"] + metadata["y2"]) / 2)
    crs = get_crs(metadata)
    th = np.linspace(0, 2 * np.pi, 361)
    for r in radii_km:
        ax.plot(centre_xy[0] + r * 1000 * np.cos(th), centre_xy[1] + r * 1000 * np.sin(th),
                color=color, lw=0.5, ls="--", transform=crs, zorder=4)
        if label:
            ax.text(centre_xy[0] + r * 1000 * np.cos(np.radians(60)),
                    centre_xy[1] + r * 1000 * np.sin(np.radians(60)), f"{r} km",
                    transform=crs, fontsize=6, color=color, zorder=4,
                    ha="left", va="bottom")


def add_scalebar(ax, length_km=None, location=(0.05, 0.05), linewidth=3):
    """วาด scale bar (หน่วย km) ในพิกัดของ projection (เมตร)."""
    x0, x1, y0, y1 = ax.get_extent(ax.projection)
    width_km = (x1 - x0) / 1000.0
    if length_km is None:
        # เลือกความยาวที่ "สวย" ประมาณ 1/5 ของความกว้างแผนที่
        cand = np.array([10, 20, 25, 50, 100, 150, 200, 250, 500])
        length_km = cand[np.argmin(np.abs(cand - width_km / 5))]
    bx = x0 + location[0] * (x1 - x0)
    by = y0 + location[1] * (y1 - y0)
    L = length_km * 1000.0
    kw = dict(transform=ax.projection, zorder=6, solid_capstyle="butt")
    ax.plot([bx, bx + L], [by, by], color="k", linewidth=linewidth, **kw)
    ax.plot([bx, bx + L / 2], [by, by], color="w", linewidth=linewidth - 1.6, **kw)
    ax.text(bx + L / 2, by + 0.015 * (y1 - y0), f"{length_km:g} km",
            ha="center", va="bottom", fontsize=mpl.rcParams["font.size"] - 1,
            transform=ax.projection, zorder=6,
            bbox=dict(boxstyle="round,pad=0.15", fc="w", ec="none", alpha=0.7))


def add_north_arrow(ax, xy=(0.94, 0.86), length_pt=18):
    """ลูกศรทิศเหนืออย่างง่าย (มุมขวาบน) ความยาวคงที่เป็น point."""
    ax.annotate("", xy=xy, xycoords="axes fraction",
                xytext=(0, -length_pt), textcoords="offset points",
                arrowprops=dict(arrowstyle="-|>,head_width=0.25,head_length=0.5",
                                color="k", lw=1.3), zorder=7)
    ax.annotate("N", xy=xy, xycoords="axes fraction", xytext=(0, 2),
                textcoords="offset points", ha="center", va="bottom",
                fontsize=mpl.rcParams["font.size"], fontweight="bold", zorder=7)


def add_panel_label(ax, label, loc="upper left"):
    """ป้าย (a), (b), (c) ที่มุมของ panel."""
    x, ha = (0.02, "left") if "left" in loc else (0.98, "right")
    y, va = (0.98, "top") if "upper" in loc else (0.02, "bottom")
    ax.text(x, y, label, transform=ax.transAxes, ha=ha, va=va,
            fontsize=mpl.rcParams["font.size"] + 1, fontweight="bold", zorder=8,
            bbox=dict(boxstyle="round,pad=0.2", fc="w", ec="0.6", lw=0.5, alpha=0.9))


def panel_labels(axs, start=0):
    """ใส่ป้าย (a), (b), ... ให้ทุก panel ตามลำดับ."""
    for i, ax in enumerate(np.ravel(axs)):
        add_panel_label(ax, f"({string.ascii_lowercase[start + i]})")


# ---------------------------------------------------------------------------
# 4) แผนที่ฝน / ความน่าจะเป็น
# ---------------------------------------------------------------------------

def radar_map(ax, field, metadata, units="mm/h", ptype="intensity",
              colorscale="pysteps", probthr=None, title=None,
              basemap=True, scalebar=True, north=True, nodata_color="0.80",
              gridline_labels=("left", "bottom"), resolution="10m", zoom=None,
              points=True):
    """วาดแผนที่ฝน (หรือความน่าจะเป็น) บน cartopy axis.

    Parameters
    ----------
    field : 2D array
        ค่าฝน (mm/h), dBZ, หรือความน่าจะเป็น (0-1)
    units : "mm/h" | "mm" | "dBZ"
    ptype : "intensity" | "depth" | "prob"
    คืนค่า artist ของภาพ (ใช้ต่อกับ add_colorbar)
    """
    crs = get_crs(metadata)
    extent = (metadata["x1"], metadata["x2"], metadata["y1"], metadata["y2"])
    origin = "upper" if metadata.get("yorigin", "upper") == "upper" else "lower"

    ax.set_extent(extent, crs=crs)
    # พื้นหลัง = นอกรัศมีเรดาร์ (no data)
    ax.set_facecolor(nodata_color)
    valid = np.isfinite(field).astype(float)
    ax.imshow(np.where(valid > 0, 1.0, np.nan), extent=extent, origin=origin,
              transform=crs, cmap=mpl.colors.ListedColormap(["white"]),
              interpolation="nearest", zorder=1)

    if ptype == "prob":
        cmap = mpl.colormaps["OrRd"].copy()
        clevs = np.linspace(0, 1, 11)
        norm = mpl.colors.BoundaryNorm(clevs, cmap.N)
        data = np.ma.masked_where(~np.isfinite(field) | (field < 0.05), field)
        im = ax.imshow(data, extent=extent, origin=origin, transform=crs,
                       cmap=cmap, norm=norm, interpolation="nearest", zorder=2)
        im._clevs = clevs
        im._label = f"P(R > {probthr} mm h$^{{-1}}$)" if probthr else "Probability"
    else:
        cmap, norm, clevs, clevs_str = get_colormap(ptype, units, colorscale)
        cmap = cmap.copy()
        cmap.set_bad((0, 0, 0, 0))      # ให้ no-data ใช้สีพื้นหลังเดียวกันทุกแผนที่
        data = np.ma.masked_invalid(field)
        im = ax.imshow(data, extent=extent, origin=origin, transform=crs,
                       cmap=cmap, norm=norm, interpolation="nearest", zorder=2)
        im._clevs, im._clevs_str = clevs, clevs_str
        unit_tex = {"mm/h": "mm h$^{-1}$", "mm": "mm", "dBZ": "dBZ"}[units]
        im._label = {"intensity": "Rain rate", "depth": "Rainfall"}.get(ptype, "") \
            + f" ({unit_tex})" if units != "dBZ" else "Reflectivity (dBZ)"

    if zoom is not None:
        ax.set_extent(zoom, crs=crs)
    if basemap:
        add_basemap(ax, resolution=resolution, labels=gridline_labels)
    if points:
        add_points(ax)
    if scalebar:
        add_scalebar(ax)
    if north:
        add_north_arrow(ax)
    if title:
        ax.set_title(title, loc="left", fontsize=mpl.rcParams["axes.titlesize"])
    return im


def field_map(ax, field, metadata, cmap="RdBu_r", vmin=None, vmax=None,
              levels=None, label="", title=None, basemap=True, scalebar=True,
              north=False, nodata_color="0.80", gridline_labels=("left", "bottom"),
              zoom=None, points=True):
    """แผนที่ของตัวแปรทั่วไป (เช่น ผลต่าง, dBR, ฝนสะสม) ด้วย colormap ใดก็ได้.

    ถ้าให้ ``levels`` จะใช้สีแบบไม่ต่อเนื่อง (BoundaryNorm) ซึ่งอ่านค่าง่ายกว่าในบทความ
    """
    crs = get_crs(metadata)
    extent = (metadata["x1"], metadata["x2"], metadata["y1"], metadata["y2"])
    origin = "upper" if metadata.get("yorigin", "upper") == "upper" else "lower"
    ax.set_extent(extent, crs=crs)
    ax.set_facecolor(nodata_color)
    cm = mpl.colormaps[cmap] if isinstance(cmap, str) else cmap
    norm = None
    if levels is not None:
        norm = mpl.colors.BoundaryNorm(levels, cm.N, extend="both")
        vmin = vmax = None
    im = ax.imshow(np.ma.masked_invalid(field), extent=extent, origin=origin,
                   transform=crs, cmap=cm, norm=norm, vmin=vmin, vmax=vmax,
                   interpolation="nearest", zorder=2)
    im._label = label
    if zoom is not None:
        ax.set_extent(zoom, crs=crs)
    if basemap:
        add_basemap(ax, labels=gridline_labels)
    if points:
        add_points(ax)
    if scalebar:
        add_scalebar(ax)
    if north:
        add_north_arrow(ax)
    if title:
        ax.set_title(title, loc="left")
    return im


def obs_contour(ax, field, metadata, level=1.0, color="k", linewidth=0.7,
                label=None):
    """วาดเส้น contour ของค่าสังเกต (เช่น ขอบเขตฝน 1 mm/h) ทับบนแผนที่."""
    crs = get_crs(metadata)
    ny, nx = field.shape
    x = metadata["x1"] + metadata["xpixelsize"] * (np.arange(nx) + 0.5)
    y = metadata["y2"] - metadata["ypixelsize"] * (np.arange(ny) + 0.5)
    cs = ax.contour(x, y, np.nan_to_num(field), levels=[level], colors=color,
                    linewidths=linewidth, transform=crs, zorder=5)
    if label:
        from matplotlib.lines import Line2D
        ax.legend(handles=[Line2D([], [], color=color, lw=linewidth, label=label)],
                  loc="lower right", frameon=True, framealpha=0.8, fontsize=7)
    return cs


def _default_extend(im):
    if hasattr(im, "_clevs_str"):
        return "max"
    e = getattr(im.norm, "extend", "neither")
    return e if e in ("both", "min", "max") else "neither"


def add_colorbar(fig, im, axs, orientation="horizontal", label=None,
                 shrink=0.6, pad=0.02, aspect=40, extend=None):
    """colorbar ร่วมสำหรับหลาย panel (ใช้ระดับสีแบบไม่ต่อเนื่องของ pysteps)."""
    cb = fig.colorbar(im, ax=list(np.ravel(axs)), orientation=orientation,
                      shrink=shrink, pad=pad, aspect=aspect,
                      extend=extend or _default_extend(im),
                      spacing="uniform")
    if hasattr(im, "_clevs_str"):
        clevs, labs = list(im._clevs), list(im._clevs_str)
        if len(clevs) > 10:          # ป้ายถี่เกินไป → แสดงทุก 2 ระดับ
            labs = [l if i % 2 == 0 else "" for i, l in enumerate(labs)]
        cb.set_ticks(clevs)
        cb.set_ticklabels(labs)
    if not hasattr(im, "_clevs_str"):
        cb.formatter = mpl.ticker.FuncFormatter(lambda v, p: f"{v:g}")
        cb.update_ticks()
    cb.set_label(label or getattr(im, "_label", ""))
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(labelsize=mpl.rcParams["xtick.labelsize"], length=2)
    return cb


def motion_arrows(ax, velocity, metadata, step=25, scale=None, color="0.1",
                  key_length=None, key_label=True, timestep_min=5.0, mask=None):
    """วาดลูกศร motion field (หน่วย pixel/timestep) บนแผนที่.

    ลูกศร key แสดงความเร็วเป็น km/h เพื่อให้อ่านทางกายภาพได้ง่าย
    """
    crs = get_crs(metadata)
    ny, nx = velocity.shape[1:]
    xps, yps = metadata["xpixelsize"], metadata["ypixelsize"]
    x = metadata["x1"] + xps * (np.arange(nx) + 0.5)
    y = metadata["y2"] - yps * (np.arange(ny) + 0.5)
    X, Y = np.meshgrid(x, y)
    # pysteps: velocity[0] = u (x, ขวา), velocity[1] = v (y แถว, ลงล่าง)
    # แปลงเป็น m ต่อ timestep และกลับทิศ v เพื่อให้แกน y ชี้ขึ้นเหนือ
    U = velocity[0] * xps
    V = -velocity[1] * yps
    if mask is not None:          # แสดงลูกศรเฉพาะในรัศมีเรดาร์
        U = np.where(mask, U, np.nan)
        V = np.where(mask, V, np.nan)
    s = (slice(step // 2, None, step), slice(step // 2, None, step))
    q = ax.quiver(X[s], Y[s], U[s], V[s], transform=crs, color=color,
                  scale=scale, scale_units="xy" if scale else None,
                  angles="xy", width=0.0028, headwidth=3.5, zorder=5)
    if key_label:
        speed_kmh = np.nanpercentile(np.hypot(U, V), 90) / 1000.0 * (60.0 / timestep_min)
        k = key_length or max(10, int(round(speed_kmh / 10.0)) * 10)
        L = k * 1000.0 * timestep_min / 60.0   # m per timestep
        ax.quiverkey(q, 0.80, 0.04, L, f"{k} km h$^{{-1}}$", labelpos="N",
                     coordinates="axes", fontproperties={"size": 7},
                     color=color, labelcolor=color)
    return q


# ---------------------------------------------------------------------------
# 5) กราฟ verification และการบันทึกรูป
# ---------------------------------------------------------------------------

def skill_axes(ax, xlabel="Lead time (min)", ylabel="", ylim=None, title=None):
    """จัดรูปแบบแกนของกราฟ skill score ให้สอดคล้องกันทุก notebook."""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.grid(True, linewidth=0.4, alpha=0.5)
    if title:
        ax.set_title(title, loc="left")
    return ax


def save_figure(fig, name, folder=None, formats=("png", "pdf")):
    """บันทึกรูปเป็น PNG 300 dpi และ PDF (vector) ไว้ในโฟลเดอร์ figures/."""
    folder = folder or FIG_DIR
    os.makedirs(folder, exist_ok=True)
    paths = []
    for fmt in formats:
        p = os.path.join(folder, f"{name}.{fmt}")
        fig.savefig(p, dpi=300, bbox_inches="tight")
        paths.append(p)
    print("บันทึกรูปแล้ว:", ", ".join(paths))
    return paths


def tstr(ts, fmt="%Y-%m-%d %H:%M UTC"):
    """แปลง datetime เป็นข้อความสั้นสำหรับ title."""
    return ts.strftime(fmt)


LOCAL_OFFSET_H = 7          # เวลาประเทศไทย = UTC+7


def tlabel(ts, local=True):
    """เช่น '12:00 UTC (19:00 LT)' — แสดงทั้ง UTC และเวลาท้องถิ่น."""
    import datetime as _dt
    s = ts.strftime("%H:%M UTC")
    if local:
        s += (ts + _dt.timedelta(hours=LOCAL_OFFSET_H)).strftime(" (%H:%M LT)")
    return s
