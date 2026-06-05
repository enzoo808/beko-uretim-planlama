"""
app.py — Beko TV Anakart Üretim Planlama Dashboard (Streamlit)
================================================================
Bu dosya SADECE arayüz ve veri yönetimi içerir.
Optimizasyon mantığı tamamen optimizer.py'dadır.

Çalıştırma : streamlit run app.py
"""

import streamlit as st
import pandas as pd
import json
from datetime import date
from optimizer import solve as run_optimizer

# ─────────────────────────────────────────────────────────────────────
#  SAYFA AYARLARI
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Beko Şasi Üretim Planlama",
    page_icon="🏭",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────
#  SABİTLER VE VERİ TANIMLARI
# ─────────────────────────────────────────────────────────────────────
KARTLAR     = ["F4", "GB", "GL", "GX", "LG", "MR", "V1",
               "XC", "XD", "XGB", "XGS", "XR", "Y3", "Y4"]
KARTLAR_MD  = ["F4", "GB", "GL", "MR", "V1", "XGB", "XGS", "Y3", "Y4"]
KARTLAR_SKIP = ["GX", "LG", "XC", "XD", "XR"]

OTD_LINES   = ["OD0", "OD2", "OD3", "OD4", "OD5", "OD6", "OD7"]
MD_LINES    = ["MD1", "MD2"]
T           = 14  # 14 iş günü (7-23 Mayıs 2026)

GUN_ETIKETLERI = [
    "07.05", "08.05", "09.05", "12.05", "13.05", "14.05", "15.05",
    "16.05", "19.05", "20.05", "21.05", "22.05", "23.05", "26.05",
]
# Not: Excel'deki tarih etiketleri. 14 iş günü.

# Yetki kontrolü
AUTHORIZED_SICIL = "26127996"


# ─────────────────────────────────────────────────────────────────────
#  VERİ YÜKLEME — Gömülü (Embedded) Üretim Verileri
# ─────────────────────────────────────────────────────────────────────
# ÖNEMLİ: Aşağıdaki fonksiyonlar, mevcut dashboard.py'daki gömülü veriyi
# optimizer.py'ın beklediği dict formatına dönüştürür.
# Gerçek veriler için mevcut dashboard.py'dan kopyalanmalıdır.

@st.cache_data
def load_production_data() -> dict:
    """
    Sasi_Uretim_Plani_v4_1.xlsx'ten türetilmiş gömülü üretim verileri.
    optimizer.py (OR-Tools SCIP) tarafından doğrudan kullanılır.
    """

    # ── OTD Tempoları: (kart, hat) → günlük kapasite ────────────────
    _tempo_otd_raw = {
        ("F4","OD0"):100, ("GX","OD0"):800, ("V1","OD0"):1000, ("XGB","OD0"):927, ("XGS","OD0"):1040, ("Y3","OD0"):880, ("Y4","OD0"):850,
        ("F4","OD2"):200, ("GX","OD2"):700, ("LG","OD2"):450, ("V1","OD2"):1150, ("XC","OD2"):1140, ("XD","OD2"):770, ("XGB","OD2"):880, ("XGS","OD2"):1000, ("XR","OD2"):610, ("Y3","OD2"):920, ("Y4","OD2"):850,
        ("V1","OD3"):1150, ("XC","OD3"):1140, ("XD","OD3"):770, ("XGB","OD3"):880, ("XGS","OD3"):1000, ("XR","OD3"):610, ("Y3","OD3"):920, ("Y4","OD3"):850,
        ("F4","OD4"):500, ("LG","OD4"):550, ("XGB","OD4"):700, ("XGS","OD4"):750,
        ("F4","OD5"):300, ("GB","OD5"):500, ("GL","OD5"):540, ("MR","OD5"):450, ("V1","OD5"):700,
        ("F4","OD6"):400, ("GB","OD6"):700, ("GL","OD6"):750, ("Y3","OD6"):870, ("Y4","OD6"):750,
    }
    # Sıfır tempo = hat-kart kombinasyonu mümkün değil → filtrele
    tempo_otd = {k: float(v) for k, v in _tempo_otd_raw.items() if v > 0}

    # ── MD Tempoları ─────────────────────────────────────────────────
    # F4: MD temposu 0 → MD'den fiilen geçmiyor (skip gibi davranır)
    _tempo_md_raw = {
        ("GB","MD1"):800, ("GL","MD1"):780, ("MR","MD1"):600, ("V1","MD1"):1000,
        ("XGB","MD1"):950, ("XGS","MD1"):1100, ("Y3","MD1"):890, ("Y4","MD1"):1000,
        ("GB","MD2"):800, ("GL","MD2"):780, ("MR","MD2"):600, ("V1","MD2"):1000,
        ("XGB","MD2"):950, ("XGS","MD2"):1100, ("Y3","MD2"):890, ("Y4","MD2"):1000,
    }
    tempo_md = {k: float(v) for k, v in _tempo_md_raw.items() if v > 0}

    # ── TA Fikstur Kapasitesi: 2 × fikstur_sayısı × çevrim_başı_adet
    ta_max = {
        "F4":160, "GB":180, "GL":630, "GX":1040, "LG":1040,
        "MR":100, "V1":760, "XC":1160, "XD":600, "XGB":828,
        "XGS":1680, "XR":460, "Y3":640, "Y4":628,
    }
    ta_cap = {(k, t): float(v) for k, v in ta_max.items() for t in range(T)}

    # ── Montaj Talebi (SUS D–Q sütunları, 14 iş günü) ───────────────
    _raw = {
        "F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        "GB":[0,0,0,0,0,665,0,0,0,0,0,0,0,0],
        "GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        "GX":[0,0,0,550,0,0,297,0,0,0,0,0,0,0],
        "LG":[279,250,50,551,950,1501,1250,1148,1143,1001,201,25,0,26],
        "MR":[0,0,0,0,0,0,0,353,51,0,0,0,0,0],
        "V1":[258,0,0,0,0,0,0,0,0,0,0,0,0,0],
        "XC":[618,1400,1340,750,430,0,0,0,0,0,198,0,499,487],
        "XD":[625,102,0,4,0,0,0,0,0,0,0,735,374,225],
        "XGB":[205,1265,1086,600,0,0,1,0,0,0,0,840,343,280],
        "XGS":[1681,1250,999,300,0,461,946,1058,1200,2785,2584,1271,1213,843],
        "XR":[2,0,215,0,945,473,467,608,500,0,239,408,261,501],
        "Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,107],
        "Y4":[881,0,0,1100,900,508,0,0,0,0,0,0,0,0],
    }
    demand = {(k, t): float(v) for k, arr in _raw.items()
              for t, v in enumerate(arr)}

    # ── Başlangıç Stokları ───────────────────────────────────────────
    init_kso = {
        "F4":238, "GB":0, "GL":0, "GX":200, "LG":543, "MR":108,
        "V1":400, "XC":1814, "XD":1069, "XGB":681, "XGS":2055,
        "XR":380, "Y3":38, "Y4":1410,
    }
    init_ksm = {
        "F4":28, "GB":1188, "GL":644, "MR":347, "V1":27,
        "XGB":587, "XGS":123, "Y3":24, "Y4":554,
    }
    init_kst = {
        "F4":349, "GB":575, "GL":416, "GX":667, "LG":700, "MR":308,
        "V1":249, "XC":1784, "XD":850, "XGB":663, "XGS":2291,
        "XR":510, "Y3":157, "Y4":782,
    }

    return {
        "kartlar":      KARTLAR,
        "kartlar_md":   KARTLAR_MD,
        "kartlar_skip": KARTLAR_SKIP,
        "otd_lines":    OTD_LINES,
        "md_lines":     MD_LINES,
        "T":            T,
        "tempo_otd":    tempo_otd,
        "tempo_md":     tempo_md,
        "ta_cap":       ta_cap,
        "demand":       demand,
        "init_kso":     init_kso,
        "init_ksm":     init_ksm,
        "init_kst":     init_kst,
    }


# ─────────────────────────────────────────────────────────────────────
#  YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────────────
def result_to_otd_df(result: dict) -> pd.DataFrame:
    """Optimizer sonucundan OTD alokasyon tablosu oluşturur."""
    rows = []
    for l in OTD_LINES:
        row = {"Hat": l}
        for t in range(T):
            key = f"{l}|{t}"
            row[GUN_ETIKETLERI[t]] = result["plan_otd"].get(key, "—")
        rows.append(row)
    return pd.DataFrame(rows).set_index("Hat")


def result_to_stock_df(result: dict, stock_key: str,
                       card_list: list) -> pd.DataFrame:
    """Tampon stok sonuçlarını tablo formatına çevirir."""
    rows = []
    for k in card_list:
        row = {"Kart": k}
        for t in range(T):
            key = f"{k}|{t}"
            row[GUN_ETIKETLERI[t]] = result[stock_key].get(key, 0)
        rows.append(row)
    return pd.DataFrame(rows).set_index("Kart")


def result_to_daily_prod_df(result: dict, prod_key: str,
                            card_list: list) -> pd.DataFrame:
    """Günlük üretim toplamını kart × gün tablosuna çevirir."""
    rows = []
    for k in card_list:
        row = {"Kart": k}
        for t in range(T):
            total = sum(v for key, v in result.get(prod_key, {}).items()
                        if key.startswith(f"{k}|") and key.endswith(f"|{t}"))
            row[GUN_ETIKETLERI[t]] = total if total > 0 else "—"
        rows.append(row)
    return pd.DataFrame(rows).set_index("Kart")


def result_to_md_df(result: dict) -> pd.DataFrame:
    """MD alokasyon tablosu."""
    rows = []
    for m in MD_LINES:
        row = {"Hat": m}
        for t in range(T):
            key = f"{m}|{t}"
            row[GUN_ETIKETLERI[t]] = result.get("plan_md", {}).get(key, "—")
        rows.append(row)
    return pd.DataFrame(rows).set_index("Hat")


def check_negative_stocks(result: dict) -> list[str]:
    """Negatif stok uyarılarını tespit eder (olmamalı, güvenlik kontrolü)."""
    warnings = []
    for stock_key, label in [("stocks_kso", "KSO"),
                              ("stocks_ksm", "KSM"),
                              ("stocks_kst", "KST")]:
        for key, val in result.get(stock_key, {}).items():
            if val < 0:
                k, t = key.split("|")
                warnings.append(f"{label} [{k}] Gün {t}: {val}")
    return warnings


# ─────────────────────────────────────────────────────────────────────
#  ANA UYGULAMA
# ─────────────────────────────────────────────────────────────────────
def main():
    st.title("🏭 Beko Şasi Üretim Planlama Karar Destek Sistemi")
    st.caption("OR-Tools SCIP · CLSP-SI MILP · Deterministik OTD + Hibrit MD/TA")

    # ── Session State başlat ─────────────────────────────────────────
    if "opt_result" not in st.session_state:
        st.session_state.opt_result = None
    if "approved" not in st.session_state:
        st.session_state.approved = False

    # ── Sekmeler ─────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Kontrol Paneli & Üretim Planı",
        "🚀 Optimize Et",
        "📊 Rapor & Geçişler",
        "⚙️ Veri Yönetimi",
    ])

    data = load_production_data()

    # ═════════════════════════════════════════════════════════════════
    #  TAB 1 — KONTROL PANELİ & ÜRETİM PLANI
    # ═════════════════════════════════════════════════════════════════
    with tab1:
        st.header("Mevcut Üretim Planı")

        if st.session_state.opt_result and st.session_state.approved:
            res = st.session_state.opt_result
            st.success(
                f"✅ Onaylı Plan — Setup: {res['total_setups']} | "
                f"Toplam Tampon: {res['total_buffer']:,}")

            with st.expander("OTD Hat Alokasyonu", expanded=True):
                st.dataframe(result_to_otd_df(res), use_container_width=True)

            with st.expander("Günlük OTD Üretim (Optimize)", expanded=True):
                st.dataframe(
                    result_to_daily_prod_df(res, "prod_otd", KARTLAR),
                    use_container_width=True)

            with st.expander("MD Hat Alokasyonu"):
                st.dataframe(result_to_md_df(res), use_container_width=True)

            with st.expander("KSO — OTD Sonrası Tampon Stok"):
                st.dataframe(
                    result_to_stock_df(res, "stocks_kso", KARTLAR),
                    use_container_width=True)

            with st.expander("KSM — MD Sonrası Tampon Stok"):
                st.dataframe(
                    result_to_stock_df(res, "stocks_ksm", KARTLAR_MD),
                    use_container_width=True)

            with st.expander("KST — TA Sonrası Tampon Stok"):
                st.dataframe(
                    result_to_stock_df(res, "stocks_kst", KARTLAR),
                    use_container_width=True)
        else:
            st.info("Henüz onaylı bir optimizasyon sonucu yok. "
                    "'Optimize Et' sekmesinden çalıştırın.")

    # ═════════════════════════════════════════════════════════════════
    #  TAB 2 — OPTİMİZASYON
    # ═════════════════════════════════════════════════════════════════
    with tab2:
        st.header("🚀 MILP Optimizasyonu")
        st.markdown(
            "OTD üretimi **deterministik** (tam tempo veya sıfır), "
            "MD kapasite sınırlı sürekli, TA fikstur sınırlı sürekli. "
            "Ağırlıklı amaç fonksiyonu: setup minimize + tampon stok minimize.")

        col1, col2 = st.columns(2)
        with col1:
            time_limit = st.slider(
                "Çözücü Zaman Limiti (saniye)",
                min_value=10, max_value=600, value=60, step=10)
        with col2:
            st.metric("Çözücü", "SCIP (OR-Tools)")
            st.metric("Model Tipi", "MILP / CLSP-SI")

        if st.button("🔄 Optimizasyonu Başlat", type="primary",
                      use_container_width=True):

            # Veri eksiklik kontrolü
            if not data["tempo_otd"]:
                st.error("⚠️ OTD tempo verisi boş! "
                         "'Veri Yönetimi' sekmesinden veri yükleyin.")
            else:
                with st.spinner("SCIP çözücü çalışıyor..."):
                    result = run_optimizer(data, time_limit_sec=time_limit)

                st.session_state.opt_result = result
                st.session_state.approved = False

                if result["status"] in ("OPTIMAL", "FEASIBLE"):
                    st.success(
                        f"✅ Çözüm bulundu ({result['status']}) — "
                        f"{result['solve_time_sec']}s")

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Toplam Setup", result["total_setups"])
                    m2.metric("Toplam Tampon Stok",
                              f"{result['total_buffer']:,}")
                    m3.metric("Çözüm Süresi",
                              f"{result['solve_time_sec']}s")

                    st.subheader("Önerilen OTD Alokasyonu")
                    st.dataframe(result_to_otd_df(result),
                                 use_container_width=True)

                    # Negatif stok kontrolü
                    warns = check_negative_stocks(result)
                    if warns:
                        st.warning("⚠️ Negatif stok tespit edildi:")
                        for w in warns:
                            st.write(f"  • {w}")
                    else:
                        st.info("Tüm tampon stoklar ≥ 0 (fizibil).")

                    # Onay mekanizması
                    st.divider()
                    st.subheader("Planı Onayla")
                    sicil = st.text_input("Sicil Numarası", type="password")
                    if st.button("✅ Bu Planı Onayla"):
                        if sicil == AUTHORIZED_SICIL:
                            st.session_state.approved = True
                            st.success("Plan onaylandı ve uygulandı!")
                            st.rerun()
                        else:
                            st.error("Yetkisiz sicil numarası.")

                elif result["status"] == "INFEASIBLE":
                    st.error(
                        "❌ Fizibil çözüm bulunamadı.")
                    st.warning(result.get("message", ""))
                    st.info(
                        "Olası çözümler: TA fikstur kapasitesini artırın, "
                        "montaj talebini revize edin veya planlama ufkunu "
                        "genişletin.")
                else:
                    st.error(f"Beklenmeyen durum: {result['status']}")
                    st.json(result)

    # ═════════════════════════════════════════════════════════════════
    #  TAB 3 — RAPOR & GEÇİŞLER
    # ═════════════════════════════════════════════════════════════════
    with tab3:
        st.header("📊 Rapor & Geçişler")

        if st.session_state.opt_result:
            res = st.session_state.opt_result

            # Setup geçiş matrisi
            st.subheader("OTD Setup Geçişleri")
            setup_rows = []
            for l in OTD_LINES:
                row = {"Hat": l}
                for t in range(T):
                    key = f"{l}|{t}"
                    row[GUN_ETIKETLERI[t]] = (
                        "🔄" if res["setups"].get(key) else "—")
                setup_rows.append(row)
            st.dataframe(
                pd.DataFrame(setup_rows).set_index("Hat"),
                use_container_width=True)

            st.subheader("MD Setup Geçişleri")
            md_setup_rows = []
            for m in MD_LINES:
                row = {"Hat": m}
                for t in range(T):
                    key = f"{m}|{t}"
                    row[GUN_ETIKETLERI[t]] = (
                        "🔄" if res.get("setups_md", {}).get(key) else "—")
                md_setup_rows.append(row)
            st.dataframe(
                pd.DataFrame(md_setup_rows).set_index("Hat"),
                use_container_width=True)

            # Özet metrikler
            st.subheader("Model İstatistikleri")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Değişken Sayısı", f"{res['num_variables']:,}")
            c2.metric("Kısıt Sayısı", f"{res['num_constraints']:,}")
            c3.metric("OTD Setup", res.get('otd_setups', '—'))
            c4.metric("MD Setup", res.get('md_setups', '—'))

            # JSON export
            st.subheader("Sonuç Dışa Aktarma")
            st.download_button(
                "📥 JSON Olarak İndir",
                data=json.dumps(res, ensure_ascii=False, indent=2),
                file_name="optimizasyon_sonuc.json",
                mime="application/json",
            )
        else:
            st.info("Henüz optimizasyon çalıştırılmadı.")

    # ═════════════════════════════════════════════════════════════════
    #  TAB 4 — VERİ YÖNETİMİ
    # ═════════════════════════════════════════════════════════════════
    with tab4:
        st.header("⚙️ Veri Yönetimi")

        # Sicil kontrolü
        sicil = st.text_input("Düzenleme için Sicil No", type="password",
                              key="veri_sicil")
        if sicil != AUTHORIZED_SICIL:
            st.warning("Veri düzenleme için yetkilendirme gereklidir.")
            return

        st.success("Yetkili erişim.")

        st.subheader("TA Fikstur Kapasitesi Düzenleme")
        st.info(
            "Fikstur sayısı × çevrim başı adet = günlük TA kapasitesi. "
            "Tempolar sayfasından alınır.")

        # TA kapasite düzenleme tablosu
        ta_edit_data = []
        for k in KARTLAR:
            row = {"Kart": k}
            for t in range(T):
                row[GUN_ETIKETLERI[t]] = data["ta_cap"].get((k, t), 0)
            ta_edit_data.append(row)

        ta_df = pd.DataFrame(ta_edit_data).set_index("Kart")
        edited_ta = st.data_editor(ta_df, use_container_width=True,
                                    num_rows="fixed")

        if st.button("💾 TA Kapasitesini Güncelle"):
            for k in KARTLAR:
                for t in range(T):
                    col = GUN_ETIKETLERI[t]
                    data["ta_cap"][(k, t)] = edited_ta.loc[k, col]
            st.success("TA kapasitesi güncellendi.")
            st.cache_data.clear()

        st.divider()
        st.subheader("Başlangıç Stokları")
        stock_data = []
        for k in KARTLAR:
            stock_data.append({
                "Kart": k,
                "KSO": data["init_kso"].get(k, 0),
                "KSM": data["init_ksm"].get(k, 0) if k in KARTLAR_MD else "—",
                "KST": data["init_kst"].get(k, 0),
            })
        st.dataframe(pd.DataFrame(stock_data).set_index("Kart"),
                     use_container_width=True)

        st.divider()
        st.subheader("Varsayılan Veriye Sıfırla")
        if st.button("🔁 Tüm Veriyi Sıfırla", type="secondary"):
            st.cache_data.clear()
            st.session_state.opt_result = None
            st.session_state.approved = False
            st.success("Veriler sıfırlandı.")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
