import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import copy

# ==========================================
# SAYFA YAPILANDIRMASI
# ==========================================
st.set_page_config(
    page_title="Beko Çerkezköy — TV Anakart Üretim Planlama",
    page_icon="📺",
    layout="wide",
)

BEKO_BLUE  = "#0033A0"
BEKO_CYAN  = "#00B5E2"
BEKO_PURP  = "#7B5EA7"
BEKO_GREEN = "#28A745"

# ==========================================
# VERİ YÜKLEME
# ==========================================
@st.cache_data
def load_base_data():
    with open("sonuc.json", "r", encoding="utf-8") as f:
        return json.load(f)

try:
    base_data = load_base_data()
except FileNotFoundError:
    st.error("❌ 'sonuc.json' dosyası bulunamadı. Lütfen dosyanın dashboard.py ile aynı klasörde olduğundan emin olun.")
    st.stop()

# ==========================================
# SESSION STATE — tek seferlik başlatma
# ==========================================
if "data" not in st.session_state:
    st.session_state.data = copy.deepcopy(base_data)
if "otd_opt" not in st.session_state:
    st.session_state.otd_opt = False
if "md_opt"  not in st.session_state:
    st.session_state.md_opt  = False
if "ta_opt"  not in st.session_state:
    st.session_state.ta_opt  = False
# Upload dedup anahtarları
for _key in ("last_otd_up", "last_md_up", "last_ta_up"):
    if _key not in st.session_state:
        st.session_state[_key] = None

data        = st.session_state.data
meta        = data.get("meta", {})
gunler      = meta.get("gunler", [])
str_gunler  = [str(g) for g in gunler]
tarihler    = meta.get("gun_tarih", {})
kartlar     = meta.get("kartlar", [])
otd_hatlari = meta.get("otd_hatlari", [])
md_kartlari = set(meta.get("md_kartlari", []))

color_palette = px.colors.qualitative.Pastel + px.colors.qualitative.Set3
kart_renkleri = {k: color_palette[i % len(color_palette)]
                 for i, k in enumerate(sorted(kartlar))}

# ==========================================
# OPTİMİZASYON STUB'LARI
# PuLP model entegre edildiğinde bu fonksiyonlar güncellenir.
# Şimdilik sonuc.json'daki optimize sonuçlarını döndürür.
# ==========================================
def run_otd_optimization(d):
    """Faz-1 (setup min) + Faz-2 (buffer min) MILP — sonuc.json stub."""
    return d.get("otd_plan", {}), d.get("setuplar", [])

def run_md_optimization(d):
    """MD hat-kart ataması — sonuc.json stub."""
    return d.get("md_onarim", [])

def run_ta_optimization(d):
    """TA fikstür planlaması — sonuc.json stub."""
    return d.get("fikstur_planlanan", {})

# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================
def tarih(gun):
    """Gün indeksini tarih etiketine çevirir."""
    return tarihler.get(str(gun), str(gun))

def get_daily_totals(dict_data, kart):
    """'kart|hat|gun' → {gun_int: toplam} sözlüğü döner."""
    totals = {int(g): 0.0 for g in gunler}
    for k, v in dict_data.items():
        parts = k.split("|")
        if parts[0] == kart:
            g_int = int(parts[-1])
            if g_int in totals:
                totals[g_int] += float(v)
    return totals

def build_otd_df(plan_dict, setuplar=None):
    """Hat × Gün DataFrame oluşturur; setup günlerine ⚡ ekler."""
    df = pd.DataFrame("—", index=otd_hatlari, columns=str_gunler)
    for hat in otd_hatlari:
        for g in str_gunler:
            val = (plan_dict or {}).get(hat, {}).get(g)
            if val:
                df.at[hat, g] = str(val)
    if setuplar:
        for s in setuplar:
            hat = s.get("hat")
            gun = str(s.get("gun"))
            if hat in df.index and gun in df.columns:
                cur = df.at[hat, gun]
                if cur != "—":
                    df.at[hat, gun] = cur + " ⚡"
    return df

def style_otd_df(df, df_ref=None):
    """Kart renklerini ve fark vurgusunu uygular."""
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    for i in df.index:
        for j in df.columns:
            raw = str(df.at[i, j]).replace(" ⚡", "").strip()
            if raw in ("—", "None", ""):
                css = "background-color:#1a1f36; color:#555; text-align:center;"
            else:
                bg  = kart_renkleri.get(raw, "#f0f2f6")
                css = f"background-color:{bg}; color:black; text-align:center; font-weight:bold;"
                if df_ref is not None:
                    ref_raw = str(df_ref.at[i, j]).replace(" ⚡", "").strip() \
                        if (i in df_ref.index and j in df_ref.columns) else "—"
                    if raw != ref_raw:
                        css += " outline:3px solid #FF4444; outline-offset:-3px;"
        styles.at[i, j] = css
    return styles

def build_fikstur_df(fd):
    """TA fikstür dict'ini Kart × Tarih pivot tablosuna çevirir."""
    if not fd:
        return None
    rows = [{"Kart": k.split("|")[0], "Gün": int(k.split("|")[1]), "Fikstür": v}
            for k, v in fd.items()]
    df_raw = pd.DataFrame(rows)
    if df_raw.empty:
        return None
    df_piv = df_raw.pivot(index="Kart", columns="Gün", values="Fikstür").fillna(0).astype(int)
    df_piv = df_piv[sorted(df_piv.columns)]
    df_piv.columns = [tarih(g) for g in df_piv.columns]
    return df_piv

def stok_grafigi(dict_data, kart, label, renk):
    """Buffer stok çizgi + alan grafiği."""
    tots = get_daily_totals(dict_data, kart)
    fig  = go.Figure()
    fig.add_trace(go.Scatter(
        x=[tarih(g) for g in gunler],
        y=[tots[int(g)] for g in gunler],
        mode="lines+markers",
        name=label,
        fill="tozeroy",
        line=dict(color=renk, width=2),
        marker=dict(size=6),
    ))
    fig.add_hline(
        y=0, line_dash="dash", line_color="red",
        annotation_text="Kritik Stok Sınırı (≥ 0)",
        annotation_position="top left",
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Tarih",
        yaxis_title="Stok Miktarı",
        height=300,
        margin=dict(t=10, b=10),
    )
    return fig

def durum_rozeti(flag, label):
    """HTML badge: optimize ise yeşil, referans ise mavi."""
    if flag:
        return (f"<span style='background:#d4edda; color:#155724; "
                f"padding:5px 14px; border-radius:20px; font-weight:bold; font-size:0.9em;'>"
                f"✅ {label}: Optimize</span>")
    return (f"<span style='background:#d1ecf1; color:#0c5460; "
            f"padding:5px 14px; border-radius:20px; font-weight:bold; font-size:0.9em;'>"
            f"📋 {label}: Referans</span>")

def process_upload(up_file, last_key):
    """Yeni dosya yüklendiyse JSON parse eder, aynı dosyaysa None döner."""
    if up_file is None:
        return None
    uid = f"{up_file.name}_{up_file.size}"
    if st.session_state[last_key] == uid:
        return None
    st.session_state[last_key] = uid
    return json.loads(up_file.getvalue().decode("utf-8"))

# ==========================================
# BAŞLIK
# ==========================================
st.markdown(
    f"<h1 style='color:{BEKO_BLUE}; text-align:center;'>"
    f"📺 Beko Çerkezköy — TV Anakart Üretim Planlama</h1>",
    unsafe_allow_html=True,
)
st.write("---")

# ==========================================
# KPI KARTLARI
# ==========================================
toplam_acik = meta.get("toplam_acik", 0)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Çözüm Durumu",    "FİZİBİL ✅" if toplam_acik == 0 else f"AÇIK ⚠️ ({toplam_acik})")
c2.metric("Toplam Setup",    f"{meta.get('toplam_setup', 0):.0f}")
c3.metric("Toplam T. Stok",  f"{meta.get('toplam_tampon', 0):,.0f}")
c4.metric("Planlama Ufku",   f"{len(gunler)} İş Günü")

# ==========================================
# TÜMÜNÜ OPTİMİZE ET + DURUM ROZETLERİ
# ==========================================
st.write("---")
col_gbtn, col_badges = st.columns([2, 8])

with col_gbtn:
    if st.button("🚀  Tümünü Optimize Et", type="primary", use_container_width=True):
        with st.spinner("OTD → MD → TA zinciri optimize ediliyor…"):
            opt_plan, opt_setup = run_otd_optimization(st.session_state.data)
            st.session_state.data["otd_plan"] = opt_plan
            st.session_state.data["setuplar"] = opt_setup
            st.session_state.otd_opt = True

            st.session_state.data["md_onarim"] = run_md_optimization(st.session_state.data)
            st.session_state.md_opt = True

            st.session_state.data["fikstur_planlanan"] = run_ta_optimization(st.session_state.data)
            st.session_state.ta_opt = True
        st.success("✅ Tüm aşamalar optimize edildi!")
        st.rerun()

with col_badges:
    st.markdown(
        f"""
        {durum_rozeti(st.session_state.otd_opt, "OTD")} &nbsp;&nbsp;
        {durum_rozeti(st.session_state.md_opt,  "MD")}  &nbsp;&nbsp;
        {durum_rozeti(st.session_state.ta_opt,  "TA")}
        """,
        unsafe_allow_html=True,
    )

st.write("---")

# ==========================================
# ANA SEKMELER: OTD | MD | TA
# ==========================================
TAB_OTD, TAB_MD, TAB_TA = st.tabs([
    "⚡ OTD — Otomatik Dizgi  (Hat Alokasyonu & Üretim & Stok)",
    "🛠️ MD — Manuel Dizgi  (Onarım Atamaları & Stok)",
    "🔧 TA — Test & Ayar  (Fikstür Atamaları & Stok)",
])

# ──────────────────────────────────────────
# OTD SEKMESİ
# ──────────────────────────────────────────
with TAB_OTD:

    # ── Kontrol satırı ──
    h1, h2, h3 = st.columns([5, 2, 2])

    with h1:
        st.markdown(
            durum_rozeti(st.session_state.otd_opt, "OTD"),
            unsafe_allow_html=True,
        )

    with h2:
        up_otd = st.file_uploader(
            "📤 OTD Verisi Yükle (.json)",
            type=["json"],
            key="up_otd",
            help=(
                "Beklenen format:\n"
                '{"otd_referans": {"OD0": {"1":"XGS", "2":"XGS", ...}, ...}}'
            ),
        )
        parsed_otd = process_upload(up_otd, "last_otd_up")
        if parsed_otd is not None:
            if "otd_referans" in parsed_otd:
                st.session_state.data["otd_referans"] = parsed_otd["otd_referans"]
                st.session_state.otd_opt = False
                st.success("✅ OTD referans verisi güncellendi.")
                st.rerun()
            else:
                st.error("JSON'da 'otd_referans' anahtarı bulunamadı.")

    with h3:
        if st.button(
            "⚡  OTD'yi Optimize Et",
            type="primary",
            use_container_width=True,
            key="btn_otd",
        ):
            with st.spinner("OTD optimize ediliyor…"):
                opt_plan, opt_setup = run_otd_optimization(st.session_state.data)
                st.session_state.data["otd_plan"] = opt_plan
                st.session_state.data["setuplar"] = opt_setup
                st.session_state.otd_opt = True
            st.success("✅ OTD optimize edildi!")
            st.rerun()

    # ── Hat–Kart Alokasyonu ──
    st.subheader("Hat – Kart Alokasyonu")

    df_ref_otd = build_otd_df(data.get("otd_referans", {}))
    df_opt_otd = build_otd_df(
        data.get("otd_plan", {}),
        setuplar=data.get("setuplar", []),
    )

    if st.session_state.otd_opt:
        col_l, col_r = st.columns(2)
        with col_l:
            st.caption("📋 **Referans Plan** (Excel)")
            st.dataframe(
                df_ref_otd.style.apply(lambda x: style_otd_df(x), axis=None),
                use_container_width=True,
            )
        with col_r:
            st.caption(
                "⚡ **Optimize Plan** (MILP)  —  "
                "⚡ = setup günü  |  🔴 çerçeve = referanstan farklı"
            )
            st.dataframe(
                df_opt_otd.style.apply(
                    lambda x: style_otd_df(x, df_ref_otd), axis=None
                ),
                use_container_width=True,
            )
    else:
        st.caption(
            "📋 **Referans Plan** (Excel'den okundu). "
            "Sağ üstteki **\"⚡ OTD'yi Optimize Et\"** butonuyla modeli çalıştırın."
        )
        st.dataframe(
            df_ref_otd.style.apply(lambda x: style_otd_df(x), axis=None),
            use_container_width=True,
        )

    # ── Günlük Üretim ──
    st.write("---")
    st.subheader("Günlük Üretim")
    xO = data.get("xO", {})
    if xO:
        rows = []
        for kart in sorted(kartlar):
            row = {"Kart": kart}
            for g in gunler:
                total = sum(
                    float(v)
                    for k, v in xO.items()
                    if k.split("|")[0] == kart and int(k.split("|")[-1]) == int(g)
                )
                row[tarih(g)] = int(total) if total > 0 else "—"
            rows.append(row)
        st.dataframe(
            pd.DataFrame(rows).set_index("Kart"),
            use_container_width=True,
        )
    else:
        st.info("OTD üretim miktarı henüz hesaplanmadı (xO boş).")

    # ── KSO Stok Grafiği ──
    st.write("---")
    st.subheader("Tampon Stok — KSO (OTD → MD / TA)")
    kart_otd = st.selectbox("Kart seçin:", sorted(kartlar), key="kart_otd")
    st.plotly_chart(
        stok_grafigi(data.get("KSO", {}), kart_otd, "KSO", BEKO_CYAN),
        use_container_width=True,
    )

# ──────────────────────────────────────────
# MD SEKMESİ
# ──────────────────────────────────────────
with TAB_MD:

    # ── Kontrol satırı ──
    h1, h2, h3 = st.columns([5, 2, 2])

    with h1:
        st.markdown(
            durum_rozeti(st.session_state.md_opt, "MD"),
            unsafe_allow_html=True,
        )

    with h2:
        up_md = st.file_uploader(
            "📤 MD Verisi Yükle (.json)",
            type=["json"],
            key="up_md",
            help="Kabul edilen anahtarlar: md_referans, KSM, KSO",
        )
        parsed_md = process_upload(up_md, "last_md_up")
        if parsed_md is not None:
            updated = [k for k in ("md_referans", "KSM", "KSO") if k in parsed_md]
            if updated:
                for k in updated:
                    st.session_state.data[k] = parsed_md[k]
                st.session_state.md_opt = False
                st.success(f"✅ Güncellendi: {', '.join(updated)}")
                st.rerun()
            else:
                st.error("Geçerli anahtar bulunamadı (md_referans / KSM / KSO).")

    with h3:
        if st.button(
            "🛠️  MD'yi Optimize Et",
            type="primary",
            use_container_width=True,
            key="btn_md",
        ):
            with st.spinner("MD optimize ediliyor…"):
                st.session_state.data["md_onarim"] = run_md_optimization(
                    st.session_state.data
                )
                st.session_state.md_opt = True
            st.success("✅ MD optimize edildi!")
            st.rerun()

    # ── MD Onarım Atamaları ──
    st.subheader("MD Onarım Atamaları")

    def fmt_md_df(lst):
        if not lst:
            return None
        df = pd.DataFrame(lst).rename(
            columns={"kart": "Kart", "kanal": "Kanal", "gun": "Gün"}
        )
        if "Gün" in df.columns:
            df["Tarih"] = df["Gün"].apply(tarih)
        return df.sort_values(["Gün", "Kanal"]) if "Gün" in df.columns else df

    md_onarimlar = data.get("md_onarim", [])
    md_ref_list  = data.get("md_referans", [])

    if st.session_state.md_opt:
        col_l, col_r = st.columns(2)
        with col_l:
            st.caption("📋 **Referans**")
            df_mdr = fmt_md_df(md_ref_list or md_onarimlar)
            if df_mdr is not None:
                st.dataframe(df_mdr, use_container_width=True, hide_index=True)
            else:
                st.info("Referans MD verisi bulunamadı.")
        with col_r:
            st.caption("⚡ **Optimize**")
            df_mdo = fmt_md_df(md_onarimlar)
            if df_mdo is not None:
                st.dataframe(df_mdo, use_container_width=True, hide_index=True)
            else:
                st.info("Planlama ufkunda MD ataması bulunmamaktadır.")
    else:
        st.caption(
            "📋 **Referans Plan**.  "
            "Optimize etmek için yukarıdaki **\"🛠️ MD'yi Optimize Et\"** butonuna tıklayın."
        )
        df_show = fmt_md_df(md_ref_list or md_onarimlar)
        if df_show is not None:
            st.dataframe(df_show, use_container_width=True, hide_index=True)
        else:
            st.info("MD onarım verisi mevcut değil.")

    # ── KSM Stok Grafiği ──
    st.write("---")
    st.subheader("Tampon Stok — KSM (MD → TA)")
    md_kart_opts = [k for k in sorted(kartlar) if k in md_kartlari] or sorted(kartlar)
    kart_md = st.selectbox("Kart seçin:", md_kart_opts, key="kart_md")
    st.plotly_chart(
        stok_grafigi(data.get("KSM", {}), kart_md, "KSM", BEKO_PURP),
        use_container_width=True,
    )

# ──────────────────────────────────────────
# TA SEKMESİ
# ──────────────────────────────────────────
with TAB_TA:

    # ── Kontrol satırı ──
    h1, h2, h3 = st.columns([5, 2, 2])

    with h1:
        st.markdown(
            durum_rozeti(st.session_state.ta_opt, "TA"),
            unsafe_allow_html=True,
        )

    with h2:
        up_ta = st.file_uploader(
            "📤 TA Verisi Yükle (.json)",
            type=["json"],
            key="up_ta",
            help="Kabul edilen anahtarlar: ta_referans, fikstur_planlanan, KST",
        )
        parsed_ta = process_upload(up_ta, "last_ta_up")
        if parsed_ta is not None:
            updated = [
                k
                for k in ("ta_referans", "fikstur_planlanan", "KST")
                if k in parsed_ta
            ]
            if updated:
                for k in updated:
                    st.session_state.data[k] = parsed_ta[k]
                st.session_state.ta_opt = False
                st.success(f"✅ Güncellendi: {', '.join(updated)}")
                st.rerun()
            else:
                st.error("Geçerli anahtar bulunamadı (ta_referans / fikstur_planlanan / KST).")

    with h3:
        if st.button(
            "🔧  TA'yı Optimize Et",
            type="primary",
            use_container_width=True,
            key="btn_ta",
        ):
            with st.spinner("TA optimize ediliyor…"):
                st.session_state.data["fikstur_planlanan"] = run_ta_optimization(
                    st.session_state.data
                )
                st.session_state.ta_opt = True
            st.success("✅ TA optimize edildi!")
            st.rerun()

    # ── TA Fikstür Atamaları ──
    st.subheader("TA Fikstür Atamaları")

    fikstur_opt = data.get("fikstur_planlanan", {})
    fikstur_ref = data.get("ta_referans", fikstur_opt)

    if st.session_state.ta_opt:
        col_l, col_r = st.columns(2)
        with col_l:
            st.caption("📋 **Referans Fikstür Planı**")
            df_ta_r = build_fikstur_df(fikstur_ref)
            if df_ta_r is not None:
                st.dataframe(
                    df_ta_r.style.background_gradient(cmap="Blues"),
                    use_container_width=True,
                )
            else:
                st.info("Referans TA verisi bulunamadı.")
        with col_r:
            st.caption("⚡ **Optimize Fikstür Planı**")
            df_ta_o = build_fikstur_df(fikstur_opt)
            if df_ta_o is not None:
                st.dataframe(
                    df_ta_o.style.background_gradient(cmap="Greens"),
                    use_container_width=True,
                )
            else:
                st.info("Optimize edilmiş TA verisi bulunamadı.")
    else:
        st.caption(
            "📋 **Referans Fikstür Planı**.  "
            "Optimize etmek için yukarıdaki **\"🔧 TA'yı Optimize Et\"** butonuna tıklayın."
        )
        df_ta_show = build_fikstur_df(fikstur_ref)
        if df_ta_show is not None:
            st.dataframe(
                df_ta_show.style.background_gradient(cmap="Blues"),
                use_container_width=True,
            )
        else:
            st.info("TA fikstür verisi mevcut değil.")

    # ── KST Stok Grafiği ──
    st.write("---")
    st.subheader("Tampon Stok — KST (TA → Son Montaj)")
    kart_ta = st.selectbox("Kart seçin:", sorted(kartlar), key="kart_ta")
    st.plotly_chart(
        stok_grafigi(data.get("KST", {}), kart_ta, "KST", BEKO_BLUE),
        use_container_width=True,
    )
