import streamlit as st
import pandas as pd
import json
import base64
import os
import plotly.graph_objects as go

# =====================================================================
# SAYFA YAPILANDIRMASI
# =====================================================================
st.set_page_config(
    page_title="Beko Çerkezköy — Şasi Montaj Planlaması",
    page_icon="📺",
    layout="wide",
)

# =====================================================================
# SABİTLER
# =====================================================================
YETKILI_SICILLER = {
    "26127996",
}
# Yeni çalışan eklemek için yukarıdaki kümeye sicil numarasını ekleyin.

KART_RENKLERI = {
    "F4": "#FFB3BA", "GB": "#A8E6CF", "GL": "#B3D4FF", "GX": "#FFFACD",
    "LG": "#D9B3FF", "MR": "#FFCBA4", "V1": "#B5EAD7", "XC": "#C3B1E1",
    "XD": "#FFE0B2", "XGB": "#81D4FA", "XGS": "#80CBC4", "XR": "#F48FB1",
    "Y3": "#C5E1A5", "Y4": "#FFCCBC",
}

# =====================================================================
# BEKO BRANDING — ARKA PLAN & TEMA
# =====================================================================
bg_css = ""
for img_name in ["aaa.jpg", "aaa.jpeg", "aaa.png"]:
    if os.path.exists(img_name):
        with open(img_name, "rb") as img_file:
            bg_b64 = base64.b64encode(img_file.read()).decode()
        bg_css = f"""
        .stApp {{
            background: linear-gradient(rgba(0,20,60,0.88),rgba(0,10,40,0.92)),
            url("data:image/jpeg;base64,{bg_b64}");
            background-size: cover; background-position: center; background-attachment: fixed;
        }}"""
        break

# Logo base64
logo_b64 = ""
for logo_name in ["pngwing.com.png", "pngwing_com.png", "logo.png"]:
    if os.path.exists(logo_name):
        with open(logo_name, "rb") as lf:
            logo_b64 = base64.b64encode(lf.read()).decode()
        break

st.markdown(f"""<style>
    {bg_css}
    /* Streamlit footer gizle */
    footer {{ visibility: hidden!important; }}
    header[data-testid="stHeader"] {{ background: rgba(0,20,60,0.95)!important; backdrop-filter: blur(10px); }}

    /* Sayfa açılış animasyonu */
    @keyframes fadeSlideIn {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @keyframes logoPulse {{ 0%,100% {{ filter:brightness(1); }} 50% {{ filter:brightness(1.4) drop-shadow(0 0 12px rgba(96,165,250,0.6)); }} }}
    .block-container {{ max-width: 1300px; animation: fadeSlideIn 0.5s ease-out; }}
    .beko-logo {{ animation: logoPulse 2.5s ease-in-out 1; }}

    /* Sekme geçiş efekti */
    .stTabs [data-baseweb="tab-panel"] {{ animation: fadeSlideIn 0.35s ease-out; }}

    section[data-testid="stSidebar"] {{ background: rgba(0,15,45,0.95)!important; }}
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] h2 {{ color: #fff!important; }}
    div[data-testid="stMetric"] {{
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px; padding: 16px; backdrop-filter: blur(10px);
    }}
    div[data-testid="stMetric"] label {{ color: #93c5fd!important; }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{ color: #fff!important; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{ background: rgba(255,255,255,0.05); border-radius: 8px; color: #93c5fd; }}
    .stTabs [aria-selected="true"] {{ background: #2563eb!important; color: #fff!important; }}
    h1,h2,h3 {{ color: #fff!important; }}
    .stCaption {{ color: #cbd5e1!important; }}
    hr {{ border-color: rgba(255,255,255,0.1)!important; }}
    /* OTD Tablo */
    .otd-table {{ width:100%; border-collapse:separate; border-spacing:3px; font-family:'Segoe UI',sans-serif; }}
    .otd-table th {{ background:rgba(37,99,235,0.3); color:#93c5fd; padding:10px 6px; font-size:0.8rem; font-weight:600; text-align:center; border-radius:6px; }}
    .otd-table td {{ padding:10px 6px; text-align:center; font-weight:700; font-size:0.82rem; border-radius:6px; color:#1e293b; }}
    .otd-hl {{ box-shadow:0 0 14px 4px rgba(37,99,235,0.55); transform:scale(1.04); position:relative; z-index:2; }}
    .otd-dim {{ opacity:0.18; filter:grayscale(70%); }}
    .otd-none {{ background:rgba(255,255,255,0.04)!important; color:#475569!important; font-weight:400; }}
    .otd-diff {{ box-shadow:inset 0 0 0 3px #ef4444!important; }}
    .otd-rh {{ background:rgba(0,0,0,0.35)!important; color:#93c5fd!important; font-weight:700; text-align:left!important; padding-left:12px!important; min-width:52px; }}
    .setup-icon {{ color:#f59e0b; font-size:0.75rem; margin-left:2px; }}
    /* Durum kartlari */
    .status-card {{ background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:12px; padding:18px; margin-bottom:10px; }}
    .status-green {{ border-left:4px solid #22c55e; }}
    .status-yellow {{ border-left:4px solid #f59e0b; }}
    .status-red {{ border-left:4px solid #ef4444; }}
    .big-num {{ font-size:1.8rem; font-weight:800; color:#fff; line-height:1.1; }}
    .big-label {{ font-size:0.75rem; color:#93c5fd; margin-top:2px; }}
    .yorum-box {{ background:rgba(37,99,235,0.1); border:1px solid rgba(37,99,235,0.3); border-radius:10px; padding:14px 18px; margin:12px 0; color:#cbd5e1; font-size:0.9rem; line-height:1.6; }}
</style>""", unsafe_allow_html=True)


# =====================================================================
# VERİ YÜKLEME
# =====================================================================
def load_data():
    if "sonuc_data" in st.session_state:
        return st.session_state.sonuc_data
    try:
        with open("sonuc.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        st.session_state.sonuc_data = data
        return data
    except FileNotFoundError:
        return None

data = load_data()
if data is None:
    st.error("Henüz yüklenmiş bir sonuç verisi yok. **Veri Yönetimi** sekmesinden veri yükleyin.")
    st.stop()

meta = data.get("meta", {})
gunler = meta.get("gunler", [])
str_gunler = [str(g) for g in gunler]
tarihler = meta.get("gun_tarih", {})
kartlar = meta.get("kartlar", [])
md_kartlari = meta.get("md_kartlari", [])
otd_hatlari = meta.get("otd_hatlari", [])


# =====================================================================
# YARDIMCI FONKSİYONLAR
# =====================================================================
def get_daily_totals(dict_data, target_card):
    totals = {int(g): 0.0 for g in gunler}
    for k, v in dict_data.items():
        parts = k.split("|")
        if parts[0] == target_card:
            gun = int(parts[-1])
            if gun in totals:
                totals[gun] += float(v)
    return totals

def format_day_ranges(days):
    if not days: return ""
    days = sorted(days)
    ranges, start, end = [], days[0], days[0]
    for d in days[1:]:
        if d == end + 1: end = d
        else:
            ranges.append(f"{start}-{end}" if start != end else str(start))
            start = end = d
    ranges.append(f"{start}-{end}" if start != end else str(start))
    return ", ".join(ranges)

def buffer_zero_count(buf_key, kart):
    buf = data.get(buf_key, {})
    return sum(1 for g in gunler if float(buf.get(f"{kart}|{g}", -1)) == 0)

def severity_info(zero_count, total):
    ratio = zero_count / total if total > 0 else 0
    if zero_count == 0:
        return "🟢", "Güvenli", "status-green"
    elif ratio < 0.4:
        return "🟡", "Dikkat", "status-yellow"
    elif ratio < 0.8:
        return "🟠", "Yüksek Risk", "status-yellow"
    else:
        return "🔴", "Kritik", "status-red"

def generate_yorum(kart):
    """Kart için otomatik Türkçe yorum üretir."""
    n = len(gunler)
    talep = sum(float(data.get('montaj_plani', {}).get(f'{kart}|{g}', 0)) for g in gunler)
    otd_uretim = sum(float(v) for k, v in data.get('xO', {}).items() if k.startswith(f'{kart}|'))
    ta_uretim = sum(float(v) for k, v in data.get('xT', {}).items() if k.startswith(f'{kart}|'))
    kso_z = buffer_zero_count('KSO', kart)
    kst_z = buffer_zero_count('KST', kart)
    ksm_z = buffer_zero_count('KSM', kart) if kart in md_kartlari else 0
    parts = []
    if talep == 0:
        parts.append(f"{kart} kartı için bu dönemde montaj talebi bulunmamaktadır; stok birikimi devam etmektedir.")
    elif otd_uretim == 0:
        parts.append(f"Bu kart dönem boyunca OTD'de üretilmiyor; mevcut devreden stok ile talep karşılanmaktadır.")
    elif kso_z >= n * 0.7:
        parts.append(f"OTD çıkışında tampon stok çoğunlukla sıfırdadır. Üretim tam zamanında (JIT) modunda ilerlemektedir.")
    if kst_z >= n * 0.5:
        parts.append(f"TA→Montaj tampon stoğu {kst_z}/{n} gün sıfırdadır. Herhangi bir TA aksaklığı montaj hattını doğrudan etkileyecektir.")
    if kart in md_kartlari and ksm_z >= n * 0.7:
        parts.append(f"MD→TA tampon stoğu da {ksm_z}/{n} gün sıfırdadır; MD darboğaz riski yüksektir.")
    if not parts:
        parts.append(f"{kart} kartı yeterli tampon stokla güvenli şekilde üretilmektedir. Aksaklık riski düşüktür.")
    return " ".join(parts)

def build_otd_html(df_model, df_ref, setuplar, highlight_card=None):
    setup_set = {(s.get("hat"), str(s.get("gun"))) for s in setuplar}
    html = '<table class="otd-table"><thead><tr><th></th>'
    for g in str_gunler:
        tarih = tarihler.get(g, g)
        gun_label = tarih[-5:] if len(tarih) >= 5 else g
        html += f"<th>{g}<br><span style='font-size:0.65rem;opacity:0.7'>{gun_label}</span></th>"
    html += "</tr></thead><tbody>"
    for hat in df_model.index:
        html += f'<tr><td class="otd-rh">{hat}</td>'
        for g in str_gunler:
            val = str(df_model.at[hat, g]) if pd.notna(df_model.at[hat, g]) else "None"
            ref_val = str(df_ref.at[hat, g]) if pd.notna(df_ref.at[hat, g]) else "None"
            is_none = val == "None"
            is_setup = (hat, g) in setup_set
            is_diff = val != ref_val and not is_none
            bg = KART_RENKLERI.get(val, "transparent")
            cls = []
            if is_none: cls.append("otd-none")
            elif highlight_card:
                cls.append("otd-hl" if val == highlight_card else "otd-dim")
            if is_diff: cls.append("otd-diff")
            style = f"background:{bg};" if not is_none else ""
            display = "—" if is_none else val
            setup_html = '<span class="setup-icon"> ⚡</span>' if is_setup else ""
            html += f'<td class="{" ".join(cls)}" style="{style}">{display}{setup_html}</td>'
        html += "</tr>"
    html += "</tbody></table>"
    return html

def analyze_issues():
    issues = []
    buf_labels = [("KSO", "OTD → MD/TA"), ("KSM", "MD → TA"), ("KST", "TA → Montaj")]
    for buf_key, buf_label in buf_labels:
        buf = data.get(buf_key, {})
        for kart in kartlar:
            if buf_key == "KSM" and kart not in md_kartlari: continue
            zero_days = [g for g in gunler if float(buf.get(f"{kart}|{g}", -1)) == 0]
            if zero_days:
                n, total = len(zero_days), len(gunler)
                ratio = n / total
                if ratio >= 0.8: sev, sev_l = "critical", "Kritik"
                elif ratio >= 0.4: sev, sev_l = "warning", "Yüksek"
                else: sev, sev_l = "info", "Orta"
                issues.append({"kart": kart, "asama": buf_label, "zero_days": zero_days,
                               "zero_count": n, "severity": sev, "sev_label": sev_l,
                               "range_str": format_day_ranges(zero_days)})
    issues.sort(key=lambda x: (-x["zero_count"], x["kart"]))
    return issues


# =====================================================================
# LOGO & BAŞLIK
# =====================================================================
logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="beko-logo" style="height:60px;margin-right:16px;vertical-align:middle;">' if logo_b64 else ""
st.markdown(f"""<div style="display:flex;align-items:center;margin-bottom:4px;">
    {logo_html}
    <div>
        <h1 style="color:#fff;margin:0;font-size:1.5rem;font-weight:700;">Çerkezköy Elektronik Fabrikası — Şasi ➜ Montaj Planlaması</h1>
    </div>
</div>""", unsafe_allow_html=True)
st.write("---")


# =====================================================================
# SIDEBAR
# =====================================================================
st.sidebar.header("Kart Filtresi")
kart_secenekleri = ["Tümü"] + sorted(kartlar)
secili_kart = st.sidebar.selectbox("Analiz edilecek kart:", kart_secenekleri)
highlight = None if secili_kart == "Tümü" else secili_kart

if highlight:
    renk = KART_RENKLERI.get(highlight, "#fff")
    st.sidebar.markdown(
        f'<div style="background:{renk};color:#1e293b;padding:8px 14px;border-radius:8px;'
        f'font-weight:700;text-align:center;font-size:1.1rem;margin-top:6px;">{highlight}</div>',
        unsafe_allow_html=True)
    st.sidebar.caption("MD geçişi var" if highlight in md_kartlari else "MD'yi atlar (OTD → TA)")


# =====================================================================
# SEKMELER
# =====================================================================
tab_kontrol, tab_durum, tab_detay, tab_uretim, tab_rapor, tab_veri = st.tabs(
    ["📊 Kontrol Paneli", "📋 Kart Durumu", "📈 Detaylı Grafikler", "🏭 Üretim Planı", "📑 Rapor & Geçişler", "⚙️ Veri Yönetimi"]
)


# =============  TAB 1: KONTROL PANELİ  ===============================
with tab_kontrol:
    toplam_acik = meta.get("toplam_acik", 0)
    durum_text = "FİZİBİL ✅" if toplam_acik == 0 else f"AÇIK VAR ⚠️ ({toplam_acik})"
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Çözüm Durumu", durum_text)
    with c2: st.metric("Toplam Setup", f"{meta.get('toplam_setup', 0):.0f}")
    with c3: st.metric("Toplam Tampon Stok", f"{meta.get('toplam_tampon', 0):,.0f}")
    st.write("---")

    # OTD Alokasyon Tablosu
    st.subheader("OTD Alokasyon Planı")
    df_model = pd.DataFrame(index=otd_hatlari, columns=str_gunler)
    df_ref = pd.DataFrame(index=otd_hatlari, columns=str_gunler)
    for hat in otd_hatlari:
        for g in str_gunler:
            df_model.at[hat, g] = data.get("otd_plan", {}).get(hat, {}).get(g, None)
            df_ref.at[hat, g] = data.get("otd_referans", {}).get(hat, {}).get(g, None)
    setuplar = data.get("setuplar", [])

    tab_m, tab_r = st.tabs(["🚀 Model Planı (Optimizasyon)", "📋 Referans Plan (Excel)"])
    with tab_m:
        hl_note = f"  •  🔵 **{highlight}** vurgulanıyor" if highlight else ""
        st.caption(f"⚡ Setup  •  Kırmızı çerçeve = referanstan fark{hl_note}")
        st.markdown(build_otd_html(df_model, df_ref, setuplar, highlight), unsafe_allow_html=True)
    with tab_r:
        st.caption("Excel'den okunan orijinal üretim planı.")
        st.markdown(build_otd_html(df_ref, df_ref, [], highlight), unsafe_allow_html=True)

    st.write("---")

    # Aksaklık Raporu
    st.subheader("🔍 Aksaklık Raporu")
    issues = analyze_issues()
    filtered = [i for i in issues if i["kart"] == highlight] if highlight else issues

    if not filtered:
        st.success("Seçili kapsamda sıfır tampon stok tespit edilmedi.")
    else:
        n_c = sum(1 for i in filtered if i["severity"] == "critical")
        n_w = sum(1 for i in filtered if i["severity"] == "warning")
        n_i = sum(1 for i in filtered if i["severity"] == "info")
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1: st.metric("Toplam Tespit", len(filtered))
        with mc2:
            st.markdown(f'<div style="text-align:center"><span style="background:#ef4444;color:#fff;padding:2px 10px;border-radius:12px;font-size:0.72rem;font-weight:700">KRİTİK</span><br><span style="color:#fff;font-size:1.4rem;font-weight:700">{n_c}</span></div>', unsafe_allow_html=True)
        with mc3:
            st.markdown(f'<div style="text-align:center"><span style="background:#f59e0b;color:#1e293b;padding:2px 10px;border-radius:12px;font-size:0.72rem;font-weight:700">YÜKSEK</span><br><span style="color:#fff;font-size:1.4rem;font-weight:700">{n_w}</span></div>', unsafe_allow_html=True)
        with mc4:
            st.markdown(f'<div style="text-align:center"><span style="background:#3b82f6;color:#fff;padding:2px 10px;border-radius:12px;font-size:0.72rem;font-weight:700">ORTA</span><br><span style="color:#fff;font-size:1.4rem;font-weight:700">{n_i}</span></div>', unsafe_allow_html=True)

        rows = [{"Kart": i["kart"], "Tampon": i["asama"], "Sıfır Günler": i["range_str"],
                 "Gün Sayısı": f"{i['zero_count']}/{len(gunler)}", "Seviye": i["sev_label"]} for i in filtered]
        df_iss = pd.DataFrame(rows)

        sev_colors = {"Kritik": "background:#ef4444;color:#fff",
                      "Yüksek": "background:#f59e0b;color:#1e293b",
                      "Orta": "background:#3b82f6;color:#fff"}

        def color_sev(val):
            return sev_colors.get(val, "")

        try:
            styled = df_iss.style.map(color_sev, subset=["Seviye"])
        except AttributeError:
            styled = df_iss.style.applymap(color_sev, subset=["Seviye"])
        st.dataframe(styled, use_container_width=True, hide_index=True,
                     height=min(400, 40 + 35 * len(rows)))


# =============  TAB 2: KART DURUMU  ==================================
with tab_durum:
    if secili_kart == "Tümü":
        st.subheader("Tüm Kartlar — Tampon Stok Durum Tablosu")
        st.caption("Her hücre o kart ve tampon noktasında kaç gün sıfır stok olduğunu gösterir. Renkler risk seviyesini belirtir.")

        header_html = """<table style="width:100%;border-collapse:separate;border-spacing:4px;font-family:'Segoe UI',sans-serif;">
        <thead><tr>
            <th style="background:rgba(37,99,235,0.3);color:#93c5fd;padding:10px;border-radius:6px;text-align:left;">Kart</th>
            <th style="background:rgba(37,99,235,0.3);color:#93c5fd;padding:10px;border-radius:6px;text-align:center;">Toplam Talep</th>
            <th style="background:rgba(37,99,235,0.3);color:#93c5fd;padding:10px;border-radius:6px;text-align:center;">OTD → MD</th>
            <th style="background:rgba(37,99,235,0.3);color:#93c5fd;padding:10px;border-radius:6px;text-align:center;">MD → TA</th>
            <th style="background:rgba(37,99,235,0.3);color:#93c5fd;padding:10px;border-radius:6px;text-align:center;">TA → Montaj</th>
            <th style="background:rgba(37,99,235,0.3);color:#93c5fd;padding:10px;border-radius:6px;text-align:center;">Risk</th>
        </tr></thead><tbody>"""

        for kart in sorted(kartlar):
            talep = sum(float(data.get('montaj_plani', {}).get(f'{kart}|{g}', 0)) for g in gunler)
            kso_z = buffer_zero_count('KSO', kart)
            ksm_z = buffer_zero_count('KSM', kart) if kart in md_kartlari else -1
            kst_z = buffer_zero_count('KST', kart)
            n = len(gunler)

            def cell(zero_cnt):
                if zero_cnt < 0: return '<td style="text-align:center;color:#475569;border-radius:6px;padding:8px;background:rgba(255,255,255,0.02);">—</td>'
                icon, _, _ = severity_info(zero_cnt, n)
                bg = "#ef4444" if zero_cnt/n >= 0.8 else "#f59e0b" if zero_cnt/n >= 0.4 else "#22c55e" if zero_cnt == 0 else "#eab308"
                return f'<td style="text-align:center;border-radius:6px;padding:8px;background:{bg}20;color:#fff;font-weight:600;">{icon} {zero_cnt}/{n}</td>'

            max_z = max(kso_z, ksm_z if ksm_z >= 0 else 0, kst_z)
            risk_icon, risk_text, _ = severity_info(max_z, n)
            kart_bg = KART_RENKLERI.get(kart, "#888")

            header_html += f"""<tr>
                <td style="padding:8px 12px;border-radius:6px;background:{kart_bg};color:#1e293b;font-weight:700;">{kart}</td>
                <td style="text-align:center;padding:8px;color:#fff;border-radius:6px;background:rgba(255,255,255,0.05);">{talep:,.0f}</td>
                {cell(kso_z)}{cell(ksm_z)}{cell(kst_z)}
                <td style="text-align:center;padding:8px;color:#fff;border-radius:6px;background:rgba(255,255,255,0.05);font-weight:600;">{risk_icon} {risk_text}</td>
            </tr>"""
        header_html += "</tbody></table>"
        st.markdown(header_html, unsafe_allow_html=True)

        st.write("")
        st.caption("🟢 Güvenli (0 gün sıfır)  •  🟡 Dikkat (<40%)  •  🟠 Yüksek Risk (40-80%)  •  🔴 Kritik (≥80%)")

    else:
        kart = highlight
        n = len(gunler)

        # Toplam değerler
        talep = sum(float(data.get('montaj_plani', {}).get(f'{kart}|{g}', 0)) for g in gunler)
        otd_u = sum(float(v) for k, v in data.get('xO', {}).items() if k.startswith(f'{kart}|'))
        md_u = sum(float(v) for k, v in data.get('xM', {}).items() if k.startswith(f'{kart}|'))
        ta_u = sum(float(v) for k, v in data.get('xT', {}).items() if k.startswith(f'{kart}|'))

        kso_z = buffer_zero_count('KSO', kart)
        ksm_z = buffer_zero_count('KSM', kart) if kart in md_kartlari else -1
        kst_z = buffer_zero_count('KST', kart)

        kart_bg = KART_RENKLERI.get(kart, "#888")
        st.markdown(f'<h2 style="margin-bottom:4px;"><span style="background:{kart_bg};color:#1e293b;padding:4px 16px;border-radius:8px;font-size:1.2rem;">{kart}</span> Kart Durum Raporu</h2>', unsafe_allow_html=True)

        # KPI satırı
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f'<div class="status-card"><div class="big-num">{talep:,.0f}</div><div class="big-label">Montaj Talebi</div></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="status-card"><div class="big-num">{otd_u:,.0f}</div><div class="big-label">OTD Üretim</div></div>', unsafe_allow_html=True)
        with k3:
            val = md_u if kart in md_kartlari else ta_u
            label = "MD Üretim" if kart in md_kartlari else "TA Üretim"
            st.markdown(f'<div class="status-card"><div class="big-num">{val:,.0f}</div><div class="big-label">{label}</div></div>', unsafe_allow_html=True)
        with k4:
            # OTD hat sayısı
            otd_hatlar = set()
            for k in data.get('xO', {}):
                if k.startswith(f'{kart}|'):
                    otd_hatlar.add(k.split('|')[1])
            st.markdown(f'<div class="status-card"><div class="big-num">{len(otd_hatlar)}</div><div class="big-label">OTD Hat Sayısı</div></div>', unsafe_allow_html=True)

        # Tampon stok durum kartları
        st.markdown("#### Tampon Stok Durumu")
        buffers_to_show = [("KSO", "OTD → MD/TA", kso_z)]
        if kart in md_kartlari:
            buffers_to_show.append(("KSM", "MD → TA", ksm_z))
        buffers_to_show.append(("KST", "TA → Montaj", kst_z))

        cols = st.columns(len(buffers_to_show))
        for col, (bk, bl, zc) in zip(cols, buffers_to_show):
            icon, risk_text, css_class = severity_info(zc, n)
            zero_range = format_day_ranges([g for g in gunler if float(data.get(bk, {}).get(f'{kart}|{g}', -1)) == 0])
            with col:
                st.markdown(f"""<div class="status-card {css_class}">
                    <div style="font-size:1rem;font-weight:700;color:#fff;">{icon} {bl}</div>
                    <div style="font-size:0.85rem;color:#cbd5e1;margin-top:6px;"><b>{zc}/{n}</b> gün sıfır stok</div>
                    <div style="font-size:0.78rem;color:#94a3b8;margin-top:4px;">Seviye: <b>{risk_text}</b></div>
                    <div style="font-size:0.72rem;color:#64748b;margin-top:4px;">{f"Günler: {zero_range}" if zero_range else "Tüm günler pozitif"}</div>
                </div>""", unsafe_allow_html=True)

        # Otomatik yorum
        yorum = generate_yorum(kart)
        st.markdown(f'<div class="yorum-box">📝 <b>Değerlendirme:</b> {yorum}</div>', unsafe_allow_html=True)

        # Günlük detay tablosu
        with st.expander("📊 Günlük Tampon Stok Tablosu"):
            kso = get_daily_totals(data.get("KSO", {}), kart)
            ksm = get_daily_totals(data.get("KSM", {}), kart)
            kst = get_daily_totals(data.get("KST", {}), kart)
            buf_rows = {"KSO (OTD→MD)": [kso[g] for g in gunler]}
            if kart in md_kartlari:
                buf_rows["KSM (MD→TA)"] = [ksm[g] for g in gunler]
            buf_rows["KST (TA→Montaj)"] = [kst[g] for g in gunler]
            df_buf = pd.DataFrame(buf_rows, index=[tarihler.get(str(g), str(g)) for g in gunler]).T
            def hs(val):
                if val == 0: return "background:#ef4444;color:#fff;font-weight:700"
                elif val < 100: return "background:#f59e0b;color:#1e293b;font-weight:600"
                else: return "background:#22c55e;color:#fff"
            try:
                st.dataframe(df_buf.style.map(hs).format("{:.0f}"), use_container_width=True, height=160)
            except AttributeError:
                st.dataframe(df_buf.style.applymap(hs).format("{:.0f}"), use_container_width=True, height=160)


# =============  TAB 3: DETAYLI GRAFİKLER  ============================
with tab_detay:
    if secili_kart == "Tümü":
        st.info("Sol panelden bir kart seçin — tampon stok ve üretim grafikleri burada görüntülenecek.")
    else:
        kart = highlight
        kso = get_daily_totals(data.get("KSO", {}), kart)
        ksm = get_daily_totals(data.get("KSM", {}), kart)
        kst = get_daily_totals(data.get("KST", {}), kart)
        u_otd = get_daily_totals(data.get("xO", {}), kart)
        u_md = get_daily_totals(data.get("xM", {}), kart)
        u_ta = get_daily_totals(data.get("xT", {}), kart)
        montaj = get_daily_totals(data.get("montaj_plani", {}), kart)
        tarih_labels = [tarihler.get(str(g), str(g)) for g in gunler]

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader(f"Tampon Stok: {kart}")
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=tarih_labels, y=[kso[g] for g in gunler], mode="lines+markers", name="KSO (OTD→MD)"))
            if kart in md_kartlari:
                fig1.add_trace(go.Scatter(x=tarih_labels, y=[ksm[g] for g in gunler], mode="lines+markers", name="KSM (MD→TA)"))
            fig1.add_trace(go.Scatter(x=tarih_labels, y=[kst[g] for g in gunler], mode="lines+markers", name="KST (TA→Montaj)"))
            fig1.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Kritik Sınır")
            fig1.update_layout(template="plotly_dark", height=380, margin=dict(l=40,r=20,t=30,b=40),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.03)",
                               legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"), xaxis_title="", yaxis_title="Stok")
            st.plotly_chart(fig1, use_container_width=True)

        with col_g2:
            st.subheader(f"Üretim vs Talep: {kart}")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=tarih_labels, y=[u_otd[g] for g in gunler], name="OTD Üretim", marker_color="#00B5E2"))
            if kart in md_kartlari:
                fig2.add_trace(go.Bar(x=tarih_labels, y=[u_md[g] for g in gunler], name="MD Üretim", marker_color="#0033A0"))
            fig2.add_trace(go.Bar(x=tarih_labels, y=[u_ta[g] for g in gunler], name="TA Üretim", marker_color="#7B8CA3"))
            fig2.add_trace(go.Scatter(x=tarih_labels, y=[montaj[g] for g in gunler], mode="lines+markers", name="Montaj Talebi", line=dict(color="orange", width=3)))
            fig2.update_layout(barmode="group", template="plotly_dark", height=380, margin=dict(l=40,r=20,t=30,b=40),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.03)",
                               legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"), xaxis_title="", yaxis_title="Adet")
            st.plotly_chart(fig2, use_container_width=True)

        # MD & TA tabloları
        st.write("---")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("🛠️ MD Onarım Atamaları")
            md_on = data.get("md_onarim", [])
            if kart in md_kartlari:
                kart_md = [o for o in md_on if o.get("kart") == kart]
                if kart_md:
                    df_md = pd.DataFrame(kart_md).rename(columns={"kart":"Kart","kanal":"Kanal","gun":"Gün"})
                    df_md["Tarih"] = df_md["Gün"].apply(lambda x: tarihler.get(str(x), str(x)))
                    st.dataframe(df_md[["Kart","Kanal","Gün","Tarih"]], use_container_width=True, hide_index=True)
                else:
                    st.info(f"{kart} için MD onarım ataması yok.")
            else:
                st.info(f"{kart} MD aşamasını atlıyor.")

        with col_t2:
            st.subheader("🔧 TA Fikstür Atamaları")
            fp = data.get("fikstur_planlanan", {})
            kart_fp = {k: v for k, v in fp.items() if k.startswith(f"{kart}|")}
            if kart_fp:
                rows = [{"Gün": int(k.split("|")[1]), "Fikstür": v} for k, v in kart_fp.items()]
                df_fp = pd.DataFrame(rows).sort_values("Gün")
                df_fp["Tarih"] = df_fp["Gün"].apply(lambda x: tarihler.get(str(x), str(x)))
                st.dataframe(df_fp[["Gün","Tarih","Fikstür"]], use_container_width=True, hide_index=True)
            else:
                st.info(f"{kart} için planlanan fikstür ataması yok.")


# =============  TAB 4: ÜRETİM PLANI  ==================================
with tab_uretim:
    # ─── SUS VERİ KAYNAĞI ───────────────────────────────────────────────
    SUS_DATES = ["07.05","08.05","09.05","11.05","12.05","13.05","14.05","15.05","16.05","18.05","20.05","21.05","22.05","23.05"]
    SUS_DAYS  = ["Perş","Cum","Cmt","Pzt","Sal","Çar","Perş","Cum","Cmt","Pzt","Çar","Perş","Cum","Cmt"]
    SUS_CARDS = ["F4","GB","GL","GX","LG","MR","V1","XC","XD","XGB","XGS","XR","Y3","Y4"]
    SUS_COL_LABELS = [f"{d}\n{t}" for d, t in zip(SUS_DAYS, SUS_DATES)]

    SUS_OTD_ALLOC = {"OD0":["XGS","XGS","XGB","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","",""],
                     "OD2":["XGB","LG","LG","LG","XC","XGS","LG","LG","LG","LG","XGS","XGS","XGS","XGS"],
                     "OD3":["XC","XC","XR","XR","XR","XR","XR","XR","XR","XC","XC","","",""],
                     "OD4":["LG","LG","LG","LG","LG","LG","LG","LG","LG","","","","",""],
                     "OD6":["Y4","Y4","","","","","","","","","","","",""]}
    SUS_OTD_RATES = {"OD0":[1,1,1,1,1,1,1,1,1,1,1,1,1,1],"OD2":[1,.3,.7,1,.5,1,1,1,1,1,1,1,1,1],"OD3":[1,1,1,1,1,1,1,1,1,1,1,1,1,1],"OD4":[1,1,.5,1,1,1,.5,1,1,1,.5,1,1,1],"OD6":[1,1,1,1,1,1,1,1,1,1,1,1,1,1]}

    SUS_OTD_DAILY = {"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[550,685,590,1000,550,550,725,1000,1000,450,0,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[1140,1140,0,0,570,0,0,0,0,1140,1140,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[880,0,927,0,0,0,0,0,0,0,0,0,0,0],"XGS":[1040,1040,0,1040,1040,2040,1040,1040,1040,1040,2040,2040,1000,1000],"XR":[0,0,610,610,610,610,610,610,610,0,0,0,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y4":[750,750,0,0,0,0,0,0,0,0,0,0,0,0]}

    SUS_OTD_REM = {"F4":[238,238,238,238,238,238,238,238,238,238,238,238,238,238],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[200,200,200,200,200,200,200,200,200,200,200,200,200,200],"LG":[-107,-207,-172,-232,118,18,-82,-137,83,303,-27,-27,-27,-27],"MR":[108,108,108,108,108,108,108,108,108,108,108,108,108,108],"V1":[400,400,400,400,400,400,400,400,400,400,400,400,400,400],"XC":[654,634,614,-546,-1126,-556,-556,-556,-556,-556,584,1724,1724,1724],"XD":[1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069],"XGB":[206,611,136,588,588,588,588,588,588,588,588,588,588,588],"XGS":[955,895,835,-265,-325,-385,555,-605,-1765,-2925,-2985,-2045,-1105,-205],"XR":[380,150,-80,70,220,370,520,670,820,970,510,50,50,50],"Y3":[38,38,38,38,38,38,38,38,38,38,38,38,38,38],"Y4":[910,1160,1410,910,410,410,410,410,410,410,410,410,410,410]}

    SUS_MD_ALLOC = {"MD1":[["XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS"]],"MD2":[["XGB","XGB","XGB","XGB","","","","XGS","XGS","XGS","","","",""],["Y4","Y4","Y4","Y4","Y4","","","","","","","","",""]]}
    SUS_MD_DAILY = {"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[475,475,475,475,0,0,0,0,0,0,0,0,0,0],"XGS":[1100,1100,1100,1100,1100,1100,1100,2200,2200,2200,1100,1100,1100,1100],"XR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y4":[500,500,500,500,500,0,0,0,0,0,0,0,0,0]}

    SUS_MD_REM = {"F4":[28,28,28,28,28,28,28,28,28,28,28,28,28,28],"GB":[1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188],"GL":[644,644,644,644,644,644,644,644,644,644,644,644,644,644],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"MR":[347,347,347,347,347,347,347,347,347,347,347,347,347,347],"V1":[27,27,27,27,27,27,27,27,27,27,27,27,27,27],"XC":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[-241,-594,-947,-1300,-825,-825,-825,-825,-825,-825,-1653,-1653,-1653,-1653],"XGS":[-717,-737,-477,-217,43,-257,-557,-857,-57,743,1543,1243,943,3143],"XR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y3":[24,24,24,24,24,24,24,24,24,24,24,24,24,24],"Y4":[-74,112,141,13,-115,-243,-871,-871,-871,-871,-871,-871,-871,-871]}

    SUS_TA_DAILY = {"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[650,650,650,650,650,650,650,780,780,780,780,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[1160,1160,1160,1160,580,0,0,0,0,0,0,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[828,828,828,828,0,0,0,0,0,0,828,0,0,0],"XGS":[840,1120,840,840,840,1400,1400,1400,1400,1400,1400,1400,1400,0],"XR":[0,230,230,460,460,460,460,460,460,460,460,460,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y4":[628,314,471,628,628,628,628,0,0,0,0,0,0,0]}

    SUS_TA_REM = {"F4":[349,349,349,349,349,349,349,349,349,349,349,349,349,349],"GB":[575,575,575,575,575,-90,-90,-90,-90,-90,-90,-90,-90,-90],"GL":[416,416,416,416,416,416,416,416,416,416,416,416,416,416],"GX":[667,667,667,117,117,117,-180,-180,-180,-180,-180,-180,-180,-180],"LG":[421,821,1421,1520,1220,369,-231,-729,-1092,-1313,-734,21,21,-5],"MR":[308,308,308,308,308,308,308,-45,-96,-96,-96,-96,-96,-96],"V1":[-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9],"XC":[1166,926,746,1156,1886,2466,2466,2466,2466,2466,2268,2268,1769,1282],"XD":[225,123,123,119,119,119,119,119,119,119,119,-616,-990,-1215],"XGB":[458,21,-237,-9,819,819,818,818,818,818,818,806,463,183],"XGS":[610,200,321,861,1701,2080,2534,2876,3076,1691,507,636,823,1380],"XR":[508,508,523,753,268,255,248,100,60,520,741,793,992,491],"Y3":[157,157,157,157,157,157,157,157,157,157,157,157,157,50],"Y4":[-99,529,843,214,-58,62,690,1318,1318,1318,1318,1318,1318,1318]}

    SUS_ASSEMBLY = {"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,665,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,550,0,0,297,0,0,0,0,0,0,0],"LG":[279,250,50,551,950,1501,1250,1148,1143,1001,201,25,0,26],"MR":[0,0,0,0,0,0,0,353,51,0,0,0,0,0],"V1":[258,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[618,1400,1340,750,430,0,0,0,0,0,198,0,499,487],"XD":[625,102,0,4,0,0,0,0,0,0,0,735,374,225],"XGB":[205,1265,1086,600,0,0,1,0,0,0,0,840,343,280],"XGS":[1681,1250,999,300,0,461,946,1058,1200,2785,2584,1271,1213,843],"XR":[2,0,215,0,945,473,467,608,500,0,239,408,261,501],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,107],"Y4":[881,0,0,1100,900,508,0,0,0,0,0,0,0,0]}

    SUS_INIT = {"F4":{"o":238,"m":28,"t":349},"GB":{"o":0,"m":1188,"t":575},"GL":{"o":0,"m":644,"t":416},"GX":{"o":200,"m":60,"t":667},"LG":{"o":543,"m":257,"t":700},"MR":{"o":108,"m":347,"t":308},"V1":{"o":400,"m":27,"t":249},"XC":{"o":1814,"m":57,"t":1784},"XD":{"o":1069,"m":12,"t":850},"XGB":{"o":681,"m":587,"t":663},"XGS":{"o":2055,"m":123,"t":2291},"XR":{"o":380,"m":6,"t":510},"Y3":{"o":38,"m":24,"t":157},"Y4":{"o":1410,"m":554,"t":782}}

    # ─── TABLO OLUŞTURMA ──────────────────────────────────────────────────
    def sus_make_table(card_data, show_init_key=None, init_source=None):
        """SUS verisi için HTML tablo üretir."""
        hdr = '<table class="otd-table"><thead><tr><th style="text-align:left;">Kart</th>'
        if show_init_key: hdr += '<th>Stok₀</th>'
        for i in range(14): hdr += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.6rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
        hdr += '</tr></thead><tbody>'
        total = [0]*14
        for c in SUS_CARDS:
            vals = card_data.get(c, [0]*14)
            bg = KART_RENKLERI.get(c, "#888")
            hdr += f'<tr><td style="background:{bg};color:#1e293b;font-weight:700;text-align:left;padding-left:10px;border-radius:6px;">{c}</td>'
            if show_init_key and init_source:
                iv = init_source.get(c, {}).get(show_init_key, 0)
                hdr += f'<td style="color:#93c5fd;font-weight:600;">{iv:,}</td>'
            for i, v in enumerate(vals):
                total[i] += v
                if v < 0:
                    hdr += f'<td style="background:rgba(239,68,68,0.25);color:#ef4444;font-weight:700;">{v:,}</td>'
                elif v == 0:
                    hdr += f'<td style="color:#475569;">—</td>'
                else:
                    hdr += f'<td style="color:#fff;">{v:,}</td>'
            hdr += '</tr>'
        # Toplam satırı
        hdr += '<tr style="border-top:2px solid rgba(37,99,235,0.4);"><td class="otd-rh">TOPLAM</td>'
        if show_init_key: hdr += '<td></td>'
        for t in total:
            hdr += f'<td style="color:#93c5fd;font-weight:800;">{t:,}</td>'
        hdr += '</tr></tbody></table>'
        return hdr

    def sus_alloc_table(alloc_dict, line_names):
        hdr = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
        for i in range(14): hdr += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.6rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
        hdr += '</tr></thead><tbody>'
        for ln in line_names:
            rows = alloc_dict.get(ln, [])
            if not rows: continue
            display_rows = rows if isinstance(rows[0], list) else [rows]
            for ri, row in enumerate(display_rows):
                hdr += f'<tr><td class="otd-rh">{ln if ri==0 else ""}</td>'
                for v in row:
                    if v:
                        bg = KART_RENKLERI.get(v, "#666")
                        hdr += f'<td style="background:{bg};color:#1e293b;font-weight:700;">{v}</td>'
                    else:
                        hdr += '<td class="otd-none">—</td>'
                hdr += '</tr>'
        hdr += '</tbody></table>'
        return hdr

    def sus_rate_table(rates_dict, line_names):
        hdr = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
        for i in range(14): hdr += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.6rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
        hdr += '</tr></thead><tbody>'
        for ln in line_names:
            vals = rates_dict.get(ln, [])
            if not vals: continue
            hdr += f'<tr><td class="otd-rh">{ln}</td>'
            for v in vals:
                pct = int(v * 100)
                clr = "#22c55e" if pct == 100 else "#f59e0b" if pct >= 50 else "#ef4444"
                hdr += f'<td style="color:{clr};font-weight:600;">%{pct}</td>'
            hdr += '</tr>'
        hdr += '</tbody></table>'
        return hdr

    # ─── SEKME İÇERİĞİ ──────────────────────────────────────────────────
    st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
        <span style="font-size:1.8rem;">🏭</span>
        <div><h2 style="margin:0;font-size:1.3rem;">Üretim Planı — Excel Görünümü</h2>
        <p style="color:#93c5fd;margin:0;font-size:0.8rem;">7–23 Mayıs 2026 • 14 İş Günü • Sasi_Uretim_Plani_v4</p></div>
    </div>""", unsafe_allow_html=True)

    up_otd, up_md, up_ta = st.tabs(["⚡ OTD (Otomatik Dizgi)", "✋ MD (Manuel Dizgi)", "🔬 TA (Test & Ayar)"])

    with up_otd:
        st.markdown("#### 🔧 Hat – Kart Alokasyonu")
        st.markdown(sus_alloc_table(SUS_OTD_ALLOC, ["OD0","OD2","OD3","OD4","OD6"]), unsafe_allow_html=True)
        with st.expander("📊 Hat Kullanım Oranları", expanded=False):
            st.markdown(sus_rate_table(SUS_OTD_RATES, ["OD0","OD2","OD3","OD4","OD6"]), unsafe_allow_html=True)
        st.markdown("#### 🏭 Günlük Üretim")
        st.markdown(sus_make_table(SUS_OTD_DAILY), unsafe_allow_html=True)
        st.markdown("#### 📦 Kalan Stok — KSO (OTD Çıkışı)")
        st.caption("🔴 Negatif değerler stok açığını gösterir — üretim montaj talebini karşılayamıyor.")
        st.markdown(sus_make_table(SUS_OTD_REM, "o", SUS_INIT), unsafe_allow_html=True)

    with up_md:
        st.markdown("#### 🔧 Hat – Kart Alokasyonu")
        st.markdown(sus_alloc_table(SUS_MD_ALLOC, ["MD1","MD2"]), unsafe_allow_html=True)
        st.markdown("#### 🏭 Günlük Üretim")
        st.markdown(sus_make_table(SUS_MD_DAILY), unsafe_allow_html=True)
        st.markdown("#### 📦 Kalan Stok — KSM (MD Çıkışı)")
        st.caption("🔴 Negatif değerler tampon stok açığını gösterir — MD çıkışı TA girişini karşılayamıyor.")
        st.markdown(sus_make_table(SUS_MD_REM, "m", SUS_INIT), unsafe_allow_html=True)

    with up_ta:
        st.markdown("#### 🏭 Günlük Üretim")
        st.markdown(sus_make_table(SUS_TA_DAILY), unsafe_allow_html=True)
        st.markdown("#### 📦 Kalan Stok — KST (TA Çıkışı)")
        st.caption("🔴 Negatif değerler tampon stok açığını gösterir — TA çıkışı montaj talebini karşılayamıyor.")
        st.markdown(sus_make_table(SUS_TA_REM, "t", SUS_INIT), unsafe_allow_html=True)
        st.markdown("#### 🎯 Montaj Planı (Son Montaj Talebi)")
        st.markdown(sus_make_table(SUS_ASSEMBLY), unsafe_allow_html=True)


# =============  TAB 5: RAPOR & GEÇİŞLER  ==============================
with tab_rapor:
    st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
        <span style="font-size:1.8rem;">📑</span>
        <div><h2 style="margin:0;font-size:1.3rem;">Rapor & Aşamalar Arası Geçişler</h2>
        <p style="color:#93c5fd;margin:0;font-size:0.8rem;">Stok ihlalleri • Kart bazında geçiş özeti • Genel durum</p></div>
    </div>""", unsafe_allow_html=True)

    # ── Genel Durum Kartları ──
    total_otd = sum(sum(v) for v in SUS_OTD_DAILY.values())
    total_md  = sum(sum(v) for v in SUS_MD_DAILY.values())
    total_ta  = sum(sum(v) for v in SUS_TA_DAILY.values())
    total_asm = sum(sum(v) for v in SUS_ASSEMBLY.values())

    # İhlal sayımı
    viol_otd = sum(1 for c in SUS_CARDS for v in SUS_OTD_REM.get(c,[]) if v < 0)
    viol_md  = sum(1 for c in SUS_CARDS for v in SUS_MD_REM.get(c,[]) if v < 0)
    viol_ta  = sum(1 for c in SUS_CARDS for v in SUS_TA_REM.get(c,[]) if v < 0)
    viol_total = viol_otd + viol_md + viol_ta

    rc1, rc2, rc3, rc4, rc5 = st.columns(5)
    with rc1: st.metric("OTD Üretim", f"{total_otd:,}")
    with rc2: st.metric("MD Üretim", f"{total_md:,}")
    with rc3: st.metric("TA Üretim", f"{total_ta:,}")
    with rc4: st.metric("Montaj Talebi", f"{total_asm:,}")
    with rc5: st.metric("Stok İhlali", f"{viol_total}", delta=f"KSO:{viol_otd} KSM:{viol_md} KST:{viol_ta}", delta_color="inverse")
    st.write("---")

    # ── Stok İhlalleri ──
    st.subheader("🚨 Stok İhlalleri (Negatif Tampon)")
    violations_list = []
    for stage_name, rem_data in [("KSO (OTD)", SUS_OTD_REM), ("KSM (MD)", SUS_MD_REM), ("KST (TA)", SUS_TA_REM)]:
        for c in SUS_CARDS:
            for i, v in enumerate(rem_data.get(c, [])):
                if v < 0:
                    violations_list.append({"Kart": c, "Aşama": stage_name, "Gün": i+1, "Tarih": SUS_DATES[i], "Açık": v})

    if violations_list:
        df_viol = pd.DataFrame(violations_list)
        neg_cards = df_viol["Kart"].nunique()
        vc1, vc2, vc3 = st.columns(3)
        with vc1:
            st.markdown(f'<div class="status-card status-red"><div class="big-num">{len(violations_list)}</div><div class="big-label">Toplam İhlal (gün×kart)</div></div>', unsafe_allow_html=True)
        with vc2:
            st.markdown(f'<div class="status-card status-yellow"><div class="big-num">{neg_cards}</div><div class="big-label">Etkilenen Kart Sayısı</div></div>', unsafe_allow_html=True)
        with vc3:
            worst = df_viol.loc[df_viol["Açık"].idxmin()]
            st.markdown(f'<div class="status-card status-red"><div class="big-num">{worst["Kart"]} {worst["Açık"]:,}</div><div class="big-label">En Büyük Açık ({worst["Aşama"]}, {worst["Tarih"]})</div></div>', unsafe_allow_html=True)

        with st.expander("📋 Tüm İhlal Detayları", expanded=True):
            def style_acik(val):
                if isinstance(val, (int, float)) and val < 0:
                    return "background:rgba(239,68,68,0.3);color:#ef4444;font-weight:700"
                return ""
            try:
                st.dataframe(df_viol.style.map(style_acik, subset=["Açık"]).format({"Açık": "{:,.0f}"}),
                             use_container_width=True, hide_index=True, height=min(500, 40 + 35*len(violations_list)))
            except AttributeError:
                st.dataframe(df_viol.style.applymap(style_acik, subset=["Açık"]).format({"Açık": "{:,.0f}"}),
                             use_container_width=True, hide_index=True, height=min(500, 40 + 35*len(violations_list)))
    else:
        st.success("Tüm aşamalarda stok ihlali yok — tüm tampon stoklar pozitif. ✅")

    st.write("---")

    # ── Kart Bazında Geçiş Özeti ──
    st.subheader("🔄 Kart Bazında OTD → MD → TA Geçiş Özeti")
    PROCESS_MAP = {"F4":True,"GB":True,"GL":True,"GX":False,"LG":False,"MR":True,"V1":True,"XC":False,"XD":False,"XGB":True,"XGS":True,"XR":False,"Y3":True,"Y4":True}

    trans_rows = []
    for c in SUS_CARDS:
        otd_t = sum(SUS_OTD_DAILY.get(c,[]))
        md_t = sum(SUS_MD_DAILY.get(c,[]))
        ta_t = sum(SUS_TA_DAILY.get(c,[]))
        asm_t = sum(SUS_ASSEMBLY.get(c,[]))
        si = SUS_INIT.get(c, {})
        denge = ta_t + si.get("t", 0) - asm_t
        trans_rows.append({
            "Kart": c, "MD?": "Evet" if PROCESS_MAP.get(c) else "—",
            "OTD Ürt.": otd_t, "OTD Stok₀": si.get("o",0),
            "MD Ürt.": md_t if PROCESS_MAP.get(c) else 0,
            "MD Stok₀": si.get("m",0) if PROCESS_MAP.get(c) else 0,
            "TA Ürt.": ta_t, "TA Stok₀": si.get("t",0),
            "Montaj": asm_t, "Denge": denge
        })

    df_trans = pd.DataFrame(trans_rows)
    def style_denge(val):
        if isinstance(val, (int, float)) and val < 0:
            return "background:rgba(239,68,68,0.3);color:#ef4444;font-weight:700"
        elif isinstance(val, (int, float)) and val > 500:
            return "background:rgba(34,197,94,0.2);color:#22c55e;font-weight:600"
        return ""
    try:
        styled_trans = df_trans.style.map(style_denge, subset=["Denge"]).format({
            "OTD Ürt.": "{:,.0f}", "OTD Stok₀": "{:,.0f}", "MD Ürt.": "{:,.0f}",
            "MD Stok₀": "{:,.0f}", "TA Ürt.": "{:,.0f}", "TA Stok₀": "{:,.0f}",
            "Montaj": "{:,.0f}", "Denge": "{:,.0f}"})
    except AttributeError:
        styled_trans = df_trans.style.applymap(style_denge, subset=["Denge"]).format({
            "OTD Ürt.": "{:,.0f}", "OTD Stok₀": "{:,.0f}", "MD Ürt.": "{:,.0f}",
            "MD Stok₀": "{:,.0f}", "TA Ürt.": "{:,.0f}", "TA Stok₀": "{:,.0f}",
            "Montaj": "{:,.0f}", "Denge": "{:,.0f}"})
    st.dataframe(styled_trans, use_container_width=True, hide_index=True, height=540)

    st.write("---")

    # ── Kritik Notlar ──
    st.subheader("⚠️ Kritik Bulgular")
    notes = [
        ("KRİTİK", "#ef4444", "XGS kartı OTD'de Gün 4'ten itibaren sürekli negatif stok — üretim-talep dengesizliği var."),
        ("KRİTİK", "#ef4444", "XGB kartı MD'de Gün 1'den itibaren negatif — OTD çıkışı MD girişini karşılayamıyor."),
        ("ORTA", "#f59e0b", "Y4 kartı MD'de Gün 1 ve Gün 5+ negatif — erken dönem TA talebi yüksek."),
        ("ORTA", "#f59e0b", "LG kartı OTD'de kısa süreli negatifler var, TA'da ise dönem ortasında stok eriyor."),
        ("DÜŞÜK", "#3b82f6", "V1 kartı TA'da Gün 1'den itibaren −9 — başlangıç stoğu montaj talebini karşılamıyor."),
    ]
    for sev, clr, txt in notes:
        st.markdown(f"""<div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);align-items:flex-start;">
            <span style="background:{clr};color:#fff;padding:2px 10px;border-radius:6px;font-size:0.7rem;font-weight:700;white-space:nowrap;margin-top:2px;">{sev}</span>
            <span style="color:#cbd5e1;font-size:0.88rem;line-height:1.5;">{txt}</span>
        </div>""", unsafe_allow_html=True)


# =============  TAB 6: VERİ YÖNETİMİ  ================================
with tab_veri:
    st.subheader("⚙️ Veri Yönetimi")
    st.caption("Sisteme yeni veri yüklemek veya mevcut verileri güncellemek için bu bölümü kullanın.")

    if "auth" not in st.session_state:
        st.session_state.auth = False
        st.session_state.auth_sicil = None

    if not st.session_state.auth:
        st.markdown('<div class="status-card status-yellow">'
                    '<p style="color:#f59e0b;margin:0 0 8px 0;font-weight:600;">🔒 Yetkili personel girişi gereklidir</p>'
                    '<p style="color:#cbd5e1;margin:0;font-size:0.85rem;">Veri değişikliği yapmak için sicil numaranızı girin.</p>'
                    '</div>', unsafe_allow_html=True)
        pw1, pw2 = st.columns([3, 1])
        with pw1:
            sicil_input = st.text_input("Sicil No:", type="password", label_visibility="collapsed", placeholder="Sicil numaranız")
        with pw2:
            if st.button("Giriş Yap", use_container_width=True):
                if sicil_input.strip() in YETKILI_SICILLER:
                    st.session_state.auth = True
                    st.session_state.auth_sicil = sicil_input.strip()
                    st.rerun()
                else:
                    st.error("Yetkisiz sicil numarası.")
    else:
        st.success(f"🔓 Giriş yapıldı — Sicil: {st.session_state.auth_sicil}")
        if st.button("Oturumu Kapat", type="secondary"):
            st.session_state.auth = False
            st.session_state.auth_sicil = None
            st.rerun()
        st.write("---")

        yukleme_modu = st.radio("Yükleme Modu:", ["📄 Sonuç JSON Yükle", "📊 Excel Yükle & Model Çalıştır"], horizontal=True)

        if yukleme_modu == "📄 Sonuç JSON Yükle":
            st.caption("Daha önce çalıştırılmış bir model sonucunu (`sonuc.json`) yükleyin.")
            uploaded = st.file_uploader("sonuc.json dosyası seçin:", type=["json"], key="json_up")
            if uploaded:
                try:
                    new_data = json.load(uploaded)
                    if "meta" not in new_data or "KSO" not in new_data:
                        st.error("Geçersiz dosya formatı — `meta` ve `KSO` anahtarları bulunamadı.")
                    else:
                        st.success(f"Dosya okundu: {len(new_data['meta'].get('kartlar',[]))} kart, "
                                   f"{len(new_data['meta'].get('gunler',[]))} gün.")
                        with st.expander("Veri önizleme"):
                            st.json(new_data.get("meta", {}))
                        if st.button("✅ Bu veriyi uygula", type="primary", use_container_width=True):
                            st.session_state.sonuc_data = new_data
                            st.rerun()
                except json.JSONDecodeError:
                    st.error("JSON dosyası okunamadı — dosya formatını kontrol edin.")

        else:
            st.caption("Üretim planı Excel dosyasını yükleyin. Sistem modeli çalıştırıp sonuçları güncelleyecek.")
            model_exists = os.path.exists("model.py") and os.path.exists("veri_oku.py")
            if not model_exists:
                st.warning("⚠️ Model dosyaları (`model.py`, `veri_oku.py`) bu sunucuda mevcut değil. "
                           "GitHub reposuna yükledikten sonra bu özellik aktif olacak.")
            else:
                uploaded_xl = st.file_uploader("Excel dosyası (.xlsx):", type=["xlsx"], key="xl_up")
                if uploaded_xl:
                    if st.button("🚀 Modeli Çalıştır", type="primary", use_container_width=True):
                        with st.spinner("Veri okunuyor ve model çözülüyor... (bu 30-60 saniye sürebilir)"):
                            try:
                                import tempfile
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                                    tmp.write(uploaded_xl.read())
                                    tmp_path = tmp.name
                                import veri_oku as vo
                                import model as mdl
                                veri = vo.veri_oku(tmp_path)
                                uyarilar = vo.dogrula(veri)
                                if uyarilar:
                                    st.warning("Veri uyarıları:\n" + "\n".join(f"• {u}" for u in uyarilar))
                                sonuc = mdl.model_kur_coz(veri, sessiz=True)
                                mdl.sonuc_kaydet(veri, sonuc, 'sonuc.json')
                                with open('sonuc.json', 'r', encoding='utf-8') as f:
                                    st.session_state.sonuc_data = json.load(f)
                                os.unlink(tmp_path)
                                st.success(f"Model çözüldü! Durum: {sonuc.get('durum','?')} | "
                                           f"Setup: {sonuc.get('toplam_setup',0):.0f} | "
                                           f"Açık: {sonuc.get('toplam_acik',0):.0f}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Hata:\n\n`{e}`")
