# Nowcasting พายุลูกเห็บด้วยข้อมูลเรดาร์กรมอุตุนิยมวิทยาและ pysteps

ชุด notebook สำหรับสอน **radar nowcasting และการติดตามพายุ** ด้วย [pysteps](https://pysteps.readthedocs.io/en/stable/) โดยใช้ **ข้อมูลจริงจากเรดาร์เชียงราย กรมอุตุนิยมวิทยา (TMD)** กรณีศึกษา **พายุลูกเห็บ อ.เชียงของ จ.เชียงราย วันที่ 23 เมษายน 2020** (11:00–14:00 UTC = 18:00–21:00 น. เวลาไทย)

เหมาะสำหรับนิสิตปริญญาตรีปี 3–4 และปริญญาโท สาขาวิทยาศาสตร์สิ่งแวดล้อม/ภูมิศาสตร์ คำอธิบายทั้งหมดเป็น **ภาษาไทย** (ศัพท์เทคนิคใช้ทับศัพท์) ส่วนรูปใช้ข้อความภาษาอังกฤษ เพื่อนำไปใช้ในบทความวิชาการได้ทันที
ชุดนี้ต่อยอดจาก repo [Teach_Nowcast_PySTEPs_ExampleData](https://github.com/nattaponm/Teach_Nowcast_PySTEPs_ExampleData) ซึ่งใช้ข้อมูลตัวอย่างจากยุโรป

## 📚 ลำดับการเรียน

| # | Notebook | เนื้อหา | เครื่องมือหลัก | เวลา |
|---|---|---|---|---|
| 0 | [`00_prepare_tmd_data`](notebooks/00_prepare_tmd_data.ipynb) | อ่าน GeoTIFF, สร้าง metadata, **QC** (range mask, noise, speckle, radial spike, ground clutter), บันทึก NetCDF | rasterio, scikit-image | 60 นาที |
| 1 | [`01_hailstorm_radar`](notebooks/01_hailstorm_radar.ipynb) | ตีความ dBZ, **Z–R + hail cap**, อนุกรมเวลาที่เชียงของ, ฝนสะสม | `tt.dbz_to_rainrate`, `dB_transform` | 60–75 นาที |
| 2 | [`02_motion_extrapolation_interpolation`](notebooks/02_motion_extrapolation_interpolation.ipynb) | LK/VET/DARTS บนข้อมูล 15 นาที, extrapolation, **advection interpolation 15 → 5 นาที** | `motion`, `extrapolate` | 75–90 นาที |
| 3 | [`03_deterministic_nowcast`](notebooks/03_deterministic_nowcast.ipynb) | Persistence vs Extrapolation vs S-PROG (+LINDA), verification จาก **6 issue times** (ETS, POD/FAR, FSS), export **GeoTIFF** | `sprog`, `linda`, `verification` | 75–90 นาที |
| 4 | [`04_probabilistic_nowcast`](notebooks/04_probabilistic_nowcast.ipynb) | STEPS ensemble, **ความน่าจะเป็นที่เชียงของ (pixel vs neighbourhood)**, กรณี nowcast พลาด, CRPS/ROC/reliability/rank histogram (+LINDA-P) | `steps`, `excprob` | 90 นาที |
| 5 | [`05_storm_tracking_tdating`](notebooks/05_storm_tracking_tdating.ipynb) | **T-DaTing** ตรวจจับ/ติดตามเซลล์พายุ, track ที่ผ่านเชียงของ, 15 vs 5 นาที, export **GeoPackage** | `feature.tstorm`, `tracking.tdating` | 90 นาที |

ทุก notebook มีโครงสร้างเดียวกัน
🎯 วัตถุประสงค์ → 📖 แนวคิดและสมการ → ⚙️ setup → 💻 ลงมือทำ → 🧪 แบบฝึกหัด (💡 คำใบ้ + ✅ เฉลยในเซลล์ที่ซ่อนโค้ดไว้) → 📝 สรุปและคำถามชวนคิด → 📚 อ้างอิง

## 🚀 วิธีใช้ (นิสิต)
1. เปิดใน Colab: `https://colab.research.google.com/github/nattaponm/Teach_Nowcast_Pysteps_TMD/blob/main/notebooks/<ชื่อไฟล์>.ipynb` (หรือกดปุ่ม *Open in Colab* ด้านบนของแต่ละไฟล์)
2. **File → Save a copy in Drive**
3. รันเซลล์ **⚙️ Setup** ก่อน (ติดตั้ง pysteps แล้ว clone repo นี้ ใช้เวลาประมาณ 2–3 นาที)
4. เริ่มจาก **Notebook 0** ซึ่งเตรียมข้อมูลจาก `0data/` ไปไว้ที่ `data/` ถ้า NB0 รันไม่ผ่าน ใน `data/` มีไฟล์ที่เตรียมไว้แล้ว จึงเรียน NB1–5 ต่อได้

รูปทุกรูปบันทึกเป็น **PNG 300 dpi + PDF** ในโฟลเดอร์ `figures/` ส่วนผลลัพธ์ GIS (GeoTIFF, GeoPackage, CSV) อยู่ใน `output/` ของ Colab session

## 📁 โครงสร้าง repo
```
0data/      CAPPI 2 km GeoTIFF ต้นฉบับจาก TMD (13 ไฟล์, ทุก 15 นาที, 500 m, UTM 47N)
data/       ข้อมูลหลัง QC (ผลลัพธ์จาก NB0)
  tmd_cri_20200423_dbz_500m.nc   reflectivity 500 m                → NB1
  tmd_cri_20200423_dbz_1km.nc    reflectivity 1 km (max 2×2)       → NB5
  tmd_cri_20200423_rain_1km.nc   rain rate 1 km (Z=200R^1.6, hail cap 55 dBZ) → NB2–4
notebooks/  notebook 0–5
utils/
  data_io.py    อ่าน/เขียน NetCDF ↔ (array, metadata) ของ pysteps
  mapplot.py    แผนที่ระดับตีพิมพ์ (UTM, จังหวัด, แม่น้ำโขง, จุดสำคัญ, วงรัศมี, scale bar, panel label)
  tmd_tools.py  พิกัด, Z–R, point time series, advection interpolation, T-DaTing → GeoPackage
```

## ⚙️ สมมติฐานและค่าที่ใช้ (ควรระบุในงานวิจัย)
| รายการ | ค่าที่ใช้ | หมายเหตุ |
|---|---|---|
| เวลาในชื่อไฟล์ | **UTC** (เวลาไทย = UTC+7) | สอดคล้องกับข่าวพายุลูกเห็บที่รายงานวันที่ 24 เม.ย. 2563 |
| รัศมีใช้งาน | 160 km | echo ไกลสุดที่ตรวจพบคือ 162 km |
| QC | noise < 15 dBZ, speckle < 8 pixel, radial spike (elongation ≥ 4, มุม ≤ 15°), clutter (มี echo ≥ 90 % ของภาพ และ σ < 5 dB) | ปรับมาสำหรับเคสนี้ ต้องตรวจด้วยตาเมื่อใช้กับเคสอื่น |
| Z–R | Marshall–Palmer $Z = 200R^{1.6}$ + hail cap 55 dBZ | NB1 เปรียบเทียบกับ WSR-88D และ Rosenfeld tropical |
| T-DaTing | minref 35, maxref 48, mindiff 6, minsize 50, minmax 41, mindis 10 (ที่ 1 km) | ค่า default ของ pysteps |

## 🐞 สิ่งที่แก้จาก notebook T-DaTing เดิม
- **export GeoPackage:** `cen_x/cen_y` เป็นตำแหน่ง pixel ต้องแปลงเป็นพิกัด UTM ก่อน (ของเดิมจุดไปอยู่ใกล้พิกัด 0,0)
- **อายุของเซลล์:** คำนวณจากเวลาจริง ไม่ใช่ `index × 15` (ซึ่งผิดเมื่อใช้ข้อมูล 5 นาที)
- **NaN:** แยก "ไม่มีข้อมูล (NaN)" ออกจาก "ไม่มีฝน (0)" ด้วย range mask
- **แผนที่:** ใช้ cartopy ที่มีพิกัด จังหวัด แม่น้ำโขง และจุดอ้างอิง (ของเดิมไม่มี geographic information)
- **QC:** เพิ่มการลบ radial interference ที่ชัดเจนช่วง 13:00 UTC และ ground clutter ซึ่งทำให้ฝนสะสมบางจุดสูงถึง 255 mm

## 📄 แหล่งข้อมูลและการอ้างอิง
- ข้อมูลเรดาร์: **กรมอุตุนิยมวิทยา (Thai Meteorological Department)** เรดาร์เชียงราย CAPPI 2 km
- Pulkkinen, S., et al. (2019). Pysteps: an open-source Python library for probabilistic precipitation nowcasting (v1.0). *Geosci. Model Dev.*, 12, 4185–4219. https://doi.org/10.5194/gmd-12-4185-2019
- Feldmann, M., et al. (2021). A characterisation of Alpine mesocyclone occurrence. *Weather Clim. Dynam.*, 2, 1225–1244.
- ข่าวเหตุการณ์: [สผ. 24 เม.ย. 2563 พายุลูกเห็บถล่มเชียงของ](https://www.onep.go.th/?p=8239), [สผ. 25 เม.ย. 2563](https://www.onep.go.th/?p=8292)
