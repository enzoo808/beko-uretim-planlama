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
    page_title="Beko Çerkezköy — TV Anakart Üretim Planlama",
    page_icon="📺",
    layout="wide",
)

# =====================================================================
# SABİTLER
# =====================================================================
ADMIN_SIFRE = "beko2026"

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

st.markdown(f"""<style>
    {bg_css}
    .block-container {{ max-width: 1300px; }}
    header[data-testid="stHeader"] {{ background: rgba(0,20,60,0.95)!important; backdrop-filter: blur(10px); }}
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

    /* OTD Tablo Stilleri */
    .otd-table {{ width:100%; border-collapse:separate; border-spacing:3px; font-family:'Segoe UI',sans-serif; }}
    .otd-table th {{
        background:rgba(37,99,235,0.3); color:#93c5fd; padding:10px 6px;
        font-size:0.8rem; font-weight:600; text-align:center; border-radius:6px;
    }}
    .otd-table td {{
        padding:10px 6px; text-align:center; font-weight:700; font-size:0.82rem;
        border-radius:6px; color:#1e293b;
    }}
    .otd-hl {{ box-shadow:0 0 14px 4px rgba(37,99,235,0.55); transform:scale(1.04); position:relative; z-index:2; }}
    .otd-dim {{ opacity:0.18; filter:grayscale(70%); }}
    .otd-none {{ background:rgba(255,255,255,0.04)!important; color:#475569!important; font-weight:400; }}
    .otd-diff {{ box-shadow:inset 0 0 0 3px #ef4444!important; }}
    .otd-rh {{
        background:rgba(0,0,0,0.35)!important; color:#93c5fd!important;
        font-weight:700; text-align:left!important; padding-left:12px!important; min-width:52px;
    }}
    .setup-icon {{ color:#f59e0b; font-size:0.75rem; margin-left:2px; }}

    /* Aksaklık Raporu */
    .issue-card {{
        background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
        border-radius:10px; padding:14px 18px; margin-bottom:8px;
    }}
    .issue-critical {{ border-left:4px solid #ef4444; }}
    .issue-warning  {{ border-left:4px solid #f59e0b; }}
    .issue-info     {{ border-left:4px solid #3b82f6; }}
    .sev-badge {{
        display:inline-block; padding:2px 10px; border-radius:12px;
        font-size:0.72rem; font-weight:700; color:#fff;
    }}
    .sev-critical {{ background:#ef4444; }}
    .sev-warning  {{ background:#f59e0b; color:#1e293b; }}
    .sev-info     {{ background:#3b82f6; }}
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
    """Ardışık günleri gruplara ayırır: [1,2,3,5,7,8] -> '1-3, 5, 7-8'"""
    if not days:
        return ""
    days = sorted(days)
    ranges, start, end = [], days[0], days[0]
    for d in days[1:]:
        if d == end + 1:
            end = d
        else:
            ranges.append(f"{start}-{end}" if start != end else str(start))
            start = end = d
    ranges.append(f"{start}-{end}" if start != end else str(start))
    return ", ".join(ranges)


def analyze_issues(data, meta):
    """Tüm tampon stokları tarar, sıfır ve kritik durumları tespit eder."""
    issues = []
    buf_labels = [("KSO", "OTD → MD/TA"), ("KSM", "MD → TA"), ("KST", "TA → Montaj")]
    for buf_key, buf_label in buf_labels:
        buf = data.get(buf_key, {})
        for kart in meta["kartlar"]:
            if buf_key == "KSM" and kart not in meta.get("md_kartlari", []):
                continue
            zero_days = []
            for g in meta["gunler"]:
                val = float(buf.get(f"{kart}|{g}", -1))
                if val == 0:
                    zero_days.append(g)
            if zero_days:
                n = len(zero_days)
                total = len(meta["gunler"])
                ratio = n / total
                if ratio >= 0.8:
                    severity, sev_label = "critical", "Kritik"
                elif ratio >= 0.4:
                    severity, sev_label = "warning", "Yüksek"
                else:
                    severity, sev_label = "info", "Orta"
                issues.append({
                    "kart": kart, "asama": buf_label, "buf_key": buf_key,
                    "zero_days": zero_days, "zero_count": n,
                    "severity": severity, "sev_label": sev_label,
                    "range_str": format_day_ranges(zero_days),
                })
    issues.sort(key=lambda x: (-x["zero_count"], x["kart"]))
    return issues


def build_otd_html(df_model, df_ref, setuplar, highlight_card=None):
    """OTD alokasyon tablosunu HTML olarak oluşturur (kart vurgulama destekli)."""
    setup_set = set()
    for s in setuplar:
        setup_set.add((s.get("hat"), str(s.get("gun"))))

    html = '<table class="otd-table"><thead><tr><th></th>'
    for g in str_gunler:
        tarih = tarihler.get(g, g)
        gun_label = tarih[-5:] if len(tarih) >= 5 else g  # MM-DD
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

            cls_list = []
            if is_none:
                cls_list.append("otd-none")
            elif highlight_card:
                if val == highlight_card:
                    cls_list.append("otd-hl")
                else:
                    cls_list.append("otd-dim")
            if is_diff:
                cls_list.append("otd-diff")

            style = f"background:{bg};" if not is_none else ""
            cls = " ".join(cls_list)
            display = "—" if is_none else val
            setup_html = '<span class="setup-icon"> ⚡</span>' if is_setup else ""

            html += f'<td class="{cls}" style="{style}">{display}{setup_html}</td>'
        html += "</tr>"
    html += "</tbody></table>"
    return html


# =====================================================================
# LOGO & BAŞLIK
# =====================================================================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    for logo_name in ["pngwing_com.png", "pngwing.com.png", "logo.png"]:
        if os.path.exists(logo_name):
            st.image(logo_name, width=100)
            break
with col_title:
    tarih_min = tarihler.get(str(gunler[0]), "") if gunler else ""
    tarih_max = tarihler.get(str(gunler[-1]), "") if gunler else ""
    horizon_text = f"{tarih_min}  →  {tarih_max}  ({len(gunler)} iş günü)" if tarih_min else f"{len(gunler)} iş günü"
    st.markdown(f"""<div>
        <h1 style="color:#fff;margin:0;font-size:1.5rem;font-weight:700;">
            Çerkezköy — TV Anakart Üretim Planlama Sonuçları</h1>
        <p style="color:#60a5fa;margin:0;font-size:0.82rem;">
            Çok Dönemli Tampon‑Fizibil Üretim Planlama Modeli &nbsp;|&nbsp;
            {horizon_text} &nbsp;|&nbsp; YTÜ Endüstri Mühendisliği 2026</p>
    </div>""", unsafe_allow_html=True)
st.write("---")

# =====================================================================
# SIDEBAR — KART SEÇİCİ
# =====================================================================
st.sidebar.header("Kart Filtresi")
kart_secenekleri = ["Tümü"] + sorted(kartlar)
secili_kart = st.sidebar.selectbox("Analiz edilecek kart:", kart_secenekleri)
highlight = None if secili_kart == "Tümü" else secili_kart

if secili_kart != "Tümü":
    renk = KART_RENKLERI.get(secili_kart, "#fff")
    st.sidebar.markdown(
        f'<div style="background:{renk};color:#1e293b;padding:8px 14px;border-radius:8px;'
        f'font-weight:700;text-align:center;font-size:1.1rem;margin-top:6px;">'
        f'{secili_kart}</div>',
        unsafe_allow_html=True,
    )
    if secili_kart in md_kartlari:
        st.sidebar.caption("MD aşamasından geçer")
    else:
        st.sidebar.caption("MD'yi atlar (OTD → TA)")

# =====================================================================
# SEKMELER
# =====================================================================
tab_kontrol, tab_analiz, tab_detay, tab_veri = st.tabs(
    ["📊 Kontrol Paneli", "📈 Kart Analizi", "📋 Detay Tabloları", "⚙️ Veri Yönetimi"]
)

# =============  TAB 1: KONTROL PANELİ  ===============================
with tab_kontrol:
    # --- KPI Kartları ---
    toplam_acik = meta.get("toplam_acik", 0)
    durum_text = "FİZİBİL ✅" if toplam_acik == 0 else f"AÇIK VAR ⚠️ ({toplam_acik})"
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Çözüm Durumu", durum_text)
    with c2:
        st.metric("Toplam Setup", f"{meta.get('toplam_setup', 0):.0f}")
    with c3:
        st.metric("Toplam Tampon Stok", f"{meta.get('toplam_tampon', 0):,.0f}")
    st.write("---")

    # --- OTD Alokasyon Tablosu ---
    st.subheader("OTD Alokasyon Planı")

    # Tablo verisini hazırla
    df_model = pd.DataFrame(index=otd_hatlari, columns=str_gunler)
    df_ref = pd.DataFrame(index=otd_hatlari, columns=str_gunler)
    for hat in otd_hatlari:
        for g in str_gunler:
            df_model.at[hat, g] = data.get("otd_plan", {}).get(hat, {}).get(g, None)
            df_ref.at[hat, g] = data.get("otd_referans", {}).get(hat, {}).get(g, None)

    setuplar = data.get("setuplar", [])

    tab_model, tab_ref = st.tabs(["🚀 Model Planı (Optimizasyon)", "📋 Referans Plan (Excel)"])
    with tab_model:
        st.caption("⚡ Setup göstergesi  •  Kırmızı çerçeve = referanstan farklı atama"
                   + (f"  •  🔵 **{secili_kart}** vurgulanıyor" if highlight else ""))
        st.markdown(build_otd_html(df_model, df_ref, setuplar, highlight), unsafe_allow_html=True)
    with tab_ref:
        st.caption("Excel'den okunan orijinal üretim planı.")
        st.markdown(build_otd_html(df_ref, df_ref, [], highlight), unsafe_allow_html=True)

    st.write("---")

    # --- Aksaklık Raporu ---
    st.subheader("🔍 Aksaklık Raporu")
    issues = analyze_issues(data, meta)

    if highlight:
        filtered = [i for i in issues if i["kart"] == highlight]
    else:
        filtered = issues

    if not filtered:
        st.success("Seçili kapsamda sıfır tampon stok tespit edilmedi — tüm tamponlar pozitif." if highlight
                   else "Hiçbir kartta sıfır tampon stok yok — sistem tamamen güvenli.")
    else:
        # Özet metrikler
        n_critical = sum(1 for i in filtered if i["severity"] == "critical")
        n_warning = sum(1 for i in filtered if i["severity"] == "warning")
        n_info = sum(1 for i in filtered if i["severity"] == "info")
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.metric("Toplam Tespit", len(filtered))
        with mc2:
            st.markdown(f'<div style="text-align:center"><span class="sev-badge sev-critical">'
                        f'KRİTİK</span><br><span style="color:#fff;font-size:1.4rem;font-weight:700">'
                        f'{n_critical}</span></div>', unsafe_allow_html=True)
        with mc3:
            st.markdown(f'<div style="text-align:center"><span class="sev-badge sev-warning">'
                        f'YÜKSEK</span><br><span style="color:#fff;font-size:1.4rem;font-weight:700">'
                        f'{n_warning}</span></div>', unsafe_allow_html=True)
        with mc4:
            st.markdown(f'<div style="text-align:center"><span class="sev-badge sev-info">'
                        f'ORTA</span><br><span style="color:#fff;font-size:1.4rem;font-weight:700">'
                        f'{n_info}</span></div>', unsafe_allow_html=True)

        st.write("")

        # Detay tablosu
        rows = []
        for i in filtered:
            rows.append({
                "Kart": i["kart"],
                "Tampon": i["asama"],
                "Sıfır Günler": i["range_str"],
                "Gün Sayısı": f"{i['zero_count']}/{len(gunler)}",
                "Seviye": i["sev_label"],
            })
        df_issues = pd.DataFrame(rows)

        def color_severity(val):
            colors = {"Kritik": "background:#ef4444;color:#fff",
                      "Yüksek": "background:#f59e0b;color:#1e293b",
                      "Orta": "background:#3b82f6;color:#fff"}
            return colors.get(val, "")

        styled = df_issues.style.applymap(color_severity, subset=["Seviye"])
        st.dataframe(styled, use_container_width=True, hide_index=True, height=min(400, 40 + 35 * len(rows)))


# =============  TAB 2: KART ANALİZİ  =================================
with tab_analiz:
    if secili_kart == "Tümü":
        st.info("Sol panelden bir kart seçin — tampon stok ve üretim grafikleri burada görüntülenecek.")
    else:
        kart = secili_kart

        kso = get_daily_totals(data.get("KSO", {}), kart)
        ksm = get_daily_totals(data.get("KSM", {}), kart)
        kst = get_daily_totals(data.get("KST", {}), kart)
        u_otd = get_daily_totals(data.get("xO", {}), kart)
        u_md = get_daily_totals(data.get("xM", {}), kart)
        u_ta = get_daily_totals(data.get("xT", {}), kart)
        montaj = get_daily_totals(data.get("montaj_plani", {}), kart)

        tarih_labels = [tarihler.get(str(g), str(g)) for g in gunler]

        col_g1, col_g2 = st.columns(2)

        # Tampon stok grafiği
        with col_g1:
            st.subheader(f"Tampon Stok: {kart}")
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=tarih_labels, y=[kso[g] for g in gunler],
                                      mode="lines+markers", name="KSO (OTD→MD)"))
            if kart in md_kartlari:
                fig1.add_trace(go.Scatter(x=tarih_labels, y=[ksm[g] for g in gunler],
                                          mode="lines+markers", name="KSM (MD→TA)"))
            fig1.add_trace(go.Scatter(x=tarih_labels, y=[kst[g] for g in gunler],
                                      mode="lines+markers", name="KST (TA→Montaj)"))
            fig1.add_hline(y=0, line_dash="dash", line_color="red",
                           annotation_text="Kritik Sınır")
            fig1.update_layout(template="plotly_dark", height=380,
                               margin=dict(l=40, r=20, t=30, b=40),
                               paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(255,255,255,0.03)",
                               legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
                               xaxis_title="", yaxis_title="Stok")
            st.plotly_chart(fig1, use_container_width=True)

        # Üretim-talep grafiği
        with col_g2:
            st.subheader(f"Üretim vs Talep: {kart}")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=tarih_labels, y=[u_otd[g] for g in gunler],
                                  name="OTD Üretim", marker_color="#00B5E2"))
            if kart in md_kartlari:
                fig2.add_trace(go.Bar(x=tarih_labels, y=[u_md[g] for g in gunler],
                                      name="MD Üretim", marker_color="#0033A0"))
            fig2.add_trace(go.Bar(x=tarih_labels, y=[u_ta[g] for g in gunler],
                                  name="TA Üretim", marker_color="#7B8CA3"))
            fig2.add_trace(go.Scatter(x=tarih_labels, y=[montaj[g] for g in gunler],
                                      mode="lines+markers", name="Montaj Talebi",
                                      line=dict(color="orange", width=3)))
            fig2.update_layout(barmode="group", template="plotly_dark", height=380,
                               margin=dict(l=40, r=20, t=30, b=40),
                               paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(255,255,255,0.03)",
                               legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
                               xaxis_title="", yaxis_title="Adet")
            st.plotly_chart(fig2, use_container_width=True)

        # Kart bazlı tampon stok ısı haritası
        st.subheader(f"Günlük Tampon Stok Tablosu: {kart}")
        buf_rows = {"KSO": [kso[g] for g in gunler]}
        if kart in md_kartlari:
            buf_rows["KSM"] = [ksm[g] for g in gunler]
        buf_rows["KST"] = [kst[g] for g in gunler]
        df_buf = pd.DataFrame(buf_rows, index=[tarihler.get(str(g), str(g)) for g in gunler]).T

        def heatmap_style(val):
            if val == 0:
                return "background:#ef4444;color:#fff;font-weight:700"
            elif val < 100:
                return "background:#f59e0b;color:#1e293b;font-weight:600"
            else:
                return "background:#22c55e;color:#fff"

        st.dataframe(
            df_buf.style.applymap(heatmap_style).format("{:.0f}"),
            use_container_width=True, height=160,
        )


# =============  TAB 3: DETAY TABLOLARI  ==============================
with tab_detay:
    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.subheader("🛠️ MD Onarım Atamaları")
        md_onarimlar = data.get("md_onarim", [])
        if md_onarimlar:
            df_md = pd.DataFrame(md_onarimlar)
            df_md = df_md.rename(columns={"kart": "Kart", "kanal": "Kanal", "gun": "Gün"})
            df_md["Tarih"] = df_md["Gün"].apply(lambda x: tarihler.get(str(x), str(x)))
            df_md = df_md[["Kart", "Kanal", "Gün", "Tarih"]].sort_values(["Gün", "Kanal"])
            if highlight:
                styled_md = df_md.style.apply(
                    lambda row: ["background:#2563eb;color:#fff" if row["Kart"] == highlight else "" for _ in row],
                    axis=1,
                )
                st.dataframe(styled_md, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_md, use_container_width=True, hide_index=True)
        else:
            st.info("Planlama ufkunda MD onarım ataması bulunmamaktadır.")

    with col_t2:
        st.subheader("🔧 TA Fikstür Atamaları")
        fikstur_dict = data.get("fikstur_planlanan", {})
        if fikstur_dict:
            fikstur_list = []
            for k, v in fikstur_dict.items():
                parts = k.split("|")
                fikstur_list.append({"Kart": parts[0], "Gün": int(parts[1]), "Fikstür": v})
            df_fiks = pd.DataFrame(fikstur_list)
            pivot = df_fiks.pivot(index="Kart", columns="Gün", values="Fikstür").fillna(0).astype(int)
            pivot = pivot[sorted(pivot.columns)]
            pivot.columns = [tarihler.get(str(g), str(g)) for g in sorted(pivot.columns)]

            if highlight and highlight in pivot.index:
                def hl_row(row):
                    return ["background:#2563eb20;font-weight:700" if row.name == highlight else "" for _ in row]
                st.dataframe(pivot.style.apply(hl_row, axis=1).background_gradient(cmap="Blues"),
                             use_container_width=True)
            else:
                st.dataframe(pivot.style.background_gradient(cmap="Blues"), use_container_width=True)
        else:
            st.info("Planlanan TA fikstür ataması bulunmamaktadır.")


# =============  TAB 4: VERİ YÖNETİMİ  ================================
with tab_veri:
    st.subheader("⚙️ Veri Yönetimi")
    st.caption("Sisteme yeni veri yüklemek veya mevcut verileri güncellemek için bu bölümü kullanın.")

    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        st.markdown('<div class="issue-card issue-warning">'
                    '<p style="color:#f59e0b;margin:0 0 8px 0;font-weight:600;">🔒 Bu bölüm şifre korumalıdır</p>'
                    '<p style="color:#cbd5e1;margin:0;font-size:0.85rem;">Veri değişikliği yapmak için yönetici şifresini girin.</p>'
                    '</div>', unsafe_allow_html=True)
        pw_col1, pw_col2 = st.columns([3, 1])
        with pw_col1:
            sifre = st.text_input("Şifre:", type="password", label_visibility="collapsed",
                                  placeholder="Yönetici şifresi")
        with pw_col2:
            if st.button("Giriş Yap", use_container_width=True):
                if sifre == ADMIN_SIFRE:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Yanlış şifre.")
    else:
        st.success("🔓 Yönetici erişimi aktif.")
        if st.button("Oturumu Kapat", type="secondary"):
            st.session_state.auth = False
            st.rerun()

        st.write("---")

        yukleme_modu = st.radio(
            "Yükleme Modu:",
            ["📄 Sonuç JSON Yükle", "📊 Excel Yükle & Model Çalıştır"],
            horizontal=True,
        )

        if yukleme_modu == "📄 Sonuç JSON Yükle":
            st.caption("Daha önce çalıştırılmış bir model sonucunu (`sonuc.json`) yükleyin.")
            uploaded = st.file_uploader("sonuc.json dosyası seçin:", type=["json"], key="json_up")
            if uploaded:
                try:
                    new_data = json.load(uploaded)
                    # Temel doğrulama
                    if "meta" not in new_data or "KSO" not in new_data:
                        st.error("Geçersiz dosya formatı — `meta` ve `KSO` anahtarları bulunamadı.")
                    else:
                        st.success(f"Dosya okundu: {len(new_data['meta'].get('kartlar', []))} kart, "
                                   f"{len(new_data['meta'].get('gunler', []))} gün.")

                        with st.expander("Yüklenen veri önizleme"):
                            st.json(new_data.get("meta", {}))

                        if st.button("✅ Bu veriyi uygula", type="primary", use_container_width=True):
                            st.session_state.sonuc_data = new_data
                            st.rerun()
                except json.JSONDecodeError:
                    st.error("JSON dosyası okunamadı — dosya formatını kontrol edin.")

        else:  # Excel yükle & model çalıştır
            st.caption("Üretim planı Excel dosyasını yükleyin. Sistem modeli çalıştırıp sonuçları otomatik güncelleyecek.")

            # model.py mevcut mu kontrol et
            model_exists = os.path.exists("model.py") and os.path.exists("veri_oku.py")

            if not model_exists:
                st.warning(
                    "⚠️ Model dosyaları (`model.py`, `veri_oku.py`) bu sunucuda henüz mevcut değil. "
                    "Bu dosyaları GitHub reposuna yükledikten sonra Excel → Model akışı aktif olacak.\n\n"
                    "Şu an için **Sonuç JSON Yükle** modunu kullanabilirsiniz."
                )
            else:
                uploaded_xl = st.file_uploader(
                    "Excel dosyası seçin (.xlsx):", type=["xlsx"], key="xl_up"
                )
                if uploaded_xl:
                    st.info("Excel yüklendi. Model çalıştırmak için aşağıdaki butona basın.")
                    if st.button("🚀 Modeli Çalıştır", type="primary", use_container_width=True):
                        with st.spinner("Model çözülüyor..."):
                            try:
                                # Excel'i geçici dosyaya kaydet
                                import tempfile
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                                    tmp.write(uploaded_xl.read())
                                    tmp_path = tmp.name

                                # Model'i çalıştır
                                from veri_oku import veri_yukle
                                from model import coz

                                veri = veri_yukle(tmp_path)
                                sonuc = coz(veri)
                                st.session_state.sonuc_data = sonuc
                                os.unlink(tmp_path)
                                st.success("Model başarıyla çözüldü! Sayfa yenileniyor...")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Model çalıştırılırken hata oluştu:\n\n`{e}`")
