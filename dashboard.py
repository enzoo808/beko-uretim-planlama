import streamlit as st
import pandas as pd
import json
import base64
import os
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# SAYFA YAPILANDIRMASI
# ==========================================
st.set_page_config(
    page_title="Beko Çerkezköy — TV Anakart Üretim Planlama",
    page_icon="📺",
    layout="wide"
)

# ==========================================
# BEKO BRANDING - ARKA PLAN & TEMA
# ==========================================
bg_css = ""
if os.path.exists("aaa.jpg"):
    with open("aaa.jpg", "rb") as img_file:
        bg_b64 = base64.b64encode(img_file.read()).decode()
    bg_css = f"""
    .stApp {{
        background: linear-gradient(
            rgba(0, 20, 60, 0.88),
            rgba(0, 10, 40, 0.92)
        ),
        url("data:image/jpeg;base64,{bg_b64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    """

st.markdown(f"""
<style>
    {bg_css}
    .block-container {{
        max-width: 1200px;
    }}
    header[data-testid="stHeader"] {{
        background: rgba(0, 20, 60, 0.95) !important;
        backdrop-filter: blur(10px);
    }}
    section[data-testid="stSidebar"] {{
        background: rgba(0, 15, 45, 0.95) !important;
    }}
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] h2 {{
        color: #ffffff !important;
    }}
    div[data-testid="stMetric"] {{
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        backdrop-filter: blur(10px);
    }}
    div[data-testid="stMetric"] label {{
        color: #93c5fd !important;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        color: #ffffff !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        color: #93c5fd;
    }}
    .stTabs [aria-selected="true"] {{
        background: #2563eb !important;
        color: white !important;
    }}
    h2, h3 {{
        color: #ffffff !important;
    }}
    .stCaption {{
        color: #cbd5e1 !important;
    }}
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
    }}
    .stAlert {{
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #93c5fd !important;
    }}
    hr {{
        border-color: rgba(255, 255, 255, 0.1) !important;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# VERİ YÜKLEME VE İŞLEME
# ==========================================
@st.cache_data
def load_data():
    with open("sonuc.json", "r", encoding="utf-8") as f:
        return json.load(f)

try:
    data = load_data()
except FileNotFoundError:
    st.error("Hata: 'sonuc.json' dosyası bulunamadı.")
    st.stop()

meta = data.get("meta", {})
gunler = meta.get("gunler", [])
str_gunler = [str(g) for g in gunler]
tarihler = meta.get("gun_tarih", {})
kartlar = meta.get("kartlar", [])

# ==========================================
# LOGO VE BAŞLIK ALANI
# ==========================================
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("pngwing_com.png"):
        st.image("pngwing_com.png", width=120)
with col_title:
    st.markdown("""
    <div>
        <h1 style="color: #ffffff; margin: 0; font-size: 1.6rem; font-weight: 700;">
            Çerkezköy — TV Anakart Üretim Planlama Sonuçları
        </h1>
        <p style="color: #60a5fa; margin: 0; font-size: 0.85rem;">
            Çok Dönemli Tampon-Fizibil Üretim Planlama Modeli &nbsp;|&nbsp; YTÜ Endüstri Mühendisliği Bitirme Projesi 2026
        </p>
    </div>
    """, unsafe_allow_html=True)

st.write("---")

# ==========================================
# 1. ÖZET KPI KARTLARI
# ==========================================
col1, col2, col3, col4 = st.columns(4)

toplam_acik = meta.get("toplam_acik", 0)
durum_text = "FİZİBİL ✅" if toplam_acik == 0 else f"AÇIK VAR ⚠️ ({toplam_acik})"

with col1:
    st.metric(label="Çözüm Durumu", value=durum_text)
with col2:
    st.metric(label="Toplam Setup", value=f"{meta.get('toplam_setup', 0):.0f}")
with col3:
    st.metric(label="Toplam Tampon Stok", value=f"{meta.get('toplam_tampon', 0):,.0f}")
with col4:
    st.metric(label="Planlama Ufku", value=f"{len(gunler)} İş Günü")

st.write("---")

# ==========================================
# 2. OTD ALOKASYON PLANI
# ==========================================
st.subheader("OTD Alokasyon Planı")

df_model_clean = pd.DataFrame(index=meta.get("otd_hatlari", []), columns=str_gunler)
df_ref = pd.DataFrame(index=meta.get("otd_hatlari", []), columns=str_gunler)

for hat in meta.get("otd_hatlari", []):
    for g in str_gunler:
        df_model_clean.at[hat, g] = data.get("otd_plan", {}).get(hat, {}).get(g, None)
        df_ref.at[hat, g] = data.get("otd_referans", {}).get(hat, {}).get(g, None)

df_model_display = df_model_clean.copy()

setuplar = data.get("setuplar", [])
for s in setuplar:
    hat = s.get("hat")
    gun = str(s.get("gun"))
    if hat in df_model_display.index and gun in df_model_display.columns:
        mevcut_deger = df_model_display.at[hat, gun]
        if pd.notna(mevcut_deger):
            df_model_display.at[hat, gun] = str(mevcut_deger) + " ⚡"

color_palette = px.colors.qualitative.Pastel + px.colors.qualitative.Set3
kart_renkleri = {kart: color_palette[i % len(color_palette)] for i, kart in enumerate(kartlar)}

def style_otd_plan(df_to_style, df_compare=None):
    styles = pd.DataFrame('', index=df_to_style.index, columns=df_to_style.columns)
    for i in df_to_style.index:
        for j in df_to_style.columns:
            val = str(df_to_style.at[i, j]).replace(' ⚡', '').strip()
            bg_color = kart_renkleri.get(val, '#f0f2f6' if val != 'None' else '')
            cell_style = f"background-color: {bg_color}; color: black; text-align: center; font-weight: bold;"
            if df_compare is not None:
                val_clean = str(df_model_clean.at[i, j]).strip()
                ref_clean = str(df_compare.at[i, j]).strip()
                if val_clean != ref_clean and val_clean != 'None':
                    cell_style += " border: 3px solid #FF0000;"
            styles.at[i, j] = cell_style
    return styles

tab1, tab2 = st.tabs(["🚀 Model Planı (Optimizasyon)", "📋 Referans Plan (Excel)"])

with tab1:
    st.caption("⚡ işareti ilgili gün ve hatta 'Setup' yapıldığını gösterir. Kırmızı çerçeveli hücreler, referans plandan farklı olan üretim atamalarıdır.")
    st.dataframe(df_model_display.style.apply(lambda x: style_otd_plan(x, df_ref), axis=None), use_container_width=True)

with tab2:
    st.caption("Excel'den okunan orijinal üretim planı.")
    st.dataframe(df_ref.style.apply(lambda x: style_otd_plan(x, None), axis=None), use_container_width=True)

# ==========================================
# 3. & 4. SEÇİLİ KART İÇİN TAMPON VE ÜRETİM
# ==========================================
st.write("---")
st.sidebar.header("Filtreleme Seçenekleri")
secili_kart = st.sidebar.selectbox("Analiz Edilecek Kartı Seçin:", sorted(kartlar))

col_grafik1, col_grafik2 = st.columns(2)

def get_daily_totals(dict_data, target_card):
    totals = {int(g): 0.0 for g in gunler}
    for k, v in dict_data.items():
        parts = k.split('|')
        kart = parts[0]
        gun = int(parts[-1])
        if kart == target_card and gun in totals:
            totals[gun] += float(v)
    return totals

kso_data = get_daily_totals(data.get("KSO", {}), secili_kart)
ksm_data = get_daily_totals(data.get("KSM", {}), secili_kart)
kst_data = get_daily_totals(data.get("KST", {}), secili_kart)

uretim_otd = get_daily_totals(data.get("xO", {}), secili_kart)
uretim_md = get_daily_totals(data.get("xM", {}), secili_kart)
uretim_ta = get_daily_totals(data.get("xT", {}), secili_kart)
montaj_talep = get_daily_totals(data.get("montaj_plani", {}), secili_kart)

df_analiz = pd.DataFrame({
    "Gün": gunler,
    "Tarih": [tarihler.get(str(g), str(g)) for g in gunler],
    "KSO (OTD->MD)": [kso_data[g] for g in gunler],
    "KSM (MD->TA)": [ksm_data[g] for g in gunler],
    "KST (TA->Montaj)": [kst_data[g] for g in gunler],
    "OTD Üretim": [uretim_otd[g] for g in gunler],
    "MD Üretim": [uretim_md[g] for g in gunler],
    "TA Üretim": [uretim_ta[g] for g in gunler],
    "Montaj Talebi": [montaj_talep[g] for g in gunler]
})

with col_grafik1:
    st.subheader(f"Tampon Stok Analizi: {secili_kart}")
    fig_stok = go.Figure()
    fig_stok.add_trace(go.Scatter(x=df_analiz["Tarih"], y=df_analiz["KSO (OTD->MD)"], mode='lines+markers', name="KSO (OTD→MD)"))
    if secili_kart in meta.get("md_kartlari", []):
        fig_stok.add_trace(go.Scatter(x=df_analiz["Tarih"], y=df_analiz["KSM (MD->TA)"], mode='lines+markers', name="KSM (MD→TA)"))
    fig_stok.add_trace(go.Scatter(x=df_analiz["Tarih"], y=df_analiz["KST (TA->Montaj)"], mode='lines+markers', name="KST (TA→Montaj)"))
    fig_stok.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Kritik Stok Sınırı")
    for col in ["KSO (OTD->MD)", "KSM (MD->TA)", "KST (TA->Montaj)"]:
        if col == "KSM (MD->TA)" and secili_kart not in meta.get("md_kartlari", []):
            continue
        zero_points = df_analiz[df_analiz[col] <= 0]
        if not zero_points.empty:
            fig_stok.add_trace(go.Scatter(
                x=zero_points["Tarih"],
                y=zero_points[col],
                mode='markers',
                marker=dict(color='red', size=12, symbol='x'),
                showlegend=False,
                hoverinfo="skip"
            ))
    fig_stok.update_layout(xaxis_title="Tarih", yaxis_title="Stok Miktarı", template="plotly_white", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_stok, use_container_width=True)

with col_grafik2:
    st.subheader(f"Üretim ve Talep Dengesi: {secili_kart}")
    fig_uretim = go.Figure()
    fig_uretim.add_trace(go.Bar(x=df_analiz["Tarih"], y=df_analiz["OTD Üretim"], name="OTD Üretim", marker_color="#00B5E2"))
    if secili_kart in meta.get("md_kartlari", []):
        fig_uretim.add_trace(go.Bar(x=df_analiz["Tarih"], y=df_analiz["MD Üretim"], name="MD Üretim", marker_color="#0033A0"))
    fig_uretim.add_trace(go.Bar(x=df_analiz["Tarih"], y=df_analiz["TA Üretim"], name="TA Üretim", marker_color="#7B8CA3"))
    fig_uretim.add_trace(go.Scatter(x=df_analiz["Tarih"], y=df_analiz["Montaj Talebi"], mode='lines+markers', name="Son Montaj Talebi", line=dict(color='orange', width=3)))
    fig_uretim.update_layout(barmode='group', xaxis_title="Tarih", yaxis_title="Miktar", template="plotly_white", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_uretim, use_container_width=True)

# ==========================================
# 5. MD ONARIM TABLOSU & 6. TA FİKSTÜR TABLOSU
# ==========================================
st.write("---")
col_table1, col_table2 = st.columns(2)

with col_table1:
    st.subheader("🛠️ MD Onarım Atamaları")
    md_onarimlar = data.get("md_onarim", [])
    if md_onarimlar:
        df_md = pd.DataFrame(md_onarimlar)
        df_md = df_md.rename(columns={"kart": "Kart", "kanal": "Kanal", "gun": "Gün"})
        df_md["Tarih"] = df_md["Gün"].apply(lambda x: tarihler.get(str(x), str(x)))
        df_md = df_md[["Kart", "Kanal", "Gün", "Tarih"]].sort_values(["Gün", "Kanal"])
        st.dataframe(df_md, use_container_width=True, hide_index=True)
    else:
        st.info("Planlama ufkunda MD onarım ataması bulunmamaktadır.")

with col_table2:
    st.subheader("🔧 Planlanan TA Fikstür Atamaları")
    fikstur_dict = data.get("fikstur_planlanan", {})
    if fikstur_dict:
        fikstur_list = []
        for k, v in fikstur_dict.items():
            parts = k.split('|')
            fikstur_list.append({"Kart": parts[0], "Gün": int(parts[1]), "Fikstür": v})
        df_fikstur_raw = pd.DataFrame(fikstur_list)
        df_fikstur_pivot = df_fikstur_raw.pivot(index="Kart", columns="Gün", values="Fikstür").fillna(0).astype(int)
        mevcut_gunler = sorted(df_fikstur_pivot.columns.tolist())
        df_fikstur_pivot = df_fikstur_pivot[mevcut_gunler]
        df_fikstur_pivot.columns = [tarihler.get(str(g), str(g)) for g in mevcut_gunler]
        st.dataframe(df_fikstur_pivot.style.background_gradient(cmap="Blues"), use_container_width=True)
    else:
        st.info("Planlanan TA fikstür ataması bulunmamaktadır.")
