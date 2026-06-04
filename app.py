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
    Üretim verilerini optimizer.py'ın beklediği formata yükler.

    ───────────────────────────────────────────────────────────────
    BU FONKSİYON İÇİNE MEVCUT dashboard.py'DAKİ GÖMÜLÜDÜRİLMİŞ
    VERİLERİ (tempo_otd, tempo_md, ta_cap, demand, init_kso, vb.)
    AYNEN KOPYALAYIN. Aşağıdaki örnek yapı referans içindir.
    ───────────────────────────────────────────────────────────────
    """

    # ── OTD Tempoları: (kart, hat) → günlük kapasite ────────────────
    # Gerçek veriler dashboard.py'daki TEMPO dict'inden gelecek.
    tempo_otd = {}
    # Örnek: tempo_otd[("XC", "OD0")] = 1200
    # ... tüm (kart, hat) kombinasyonları ...

    # ── MD Tempoları: (kart, hat) → günlük kapasite ─────────────────
    tempo_md = {}
    # Örnek: tempo_md[("GB", "MD1")] = 800
    # ... sadece KARTLAR_MD × MD_LINES ...

    # ── TA Kapasitesi: (kart, gün) → günlük max üretim ──────────────
    ta_cap = {}
    # Örnek: ta_cap[("XC", 0)] = 900
    # Fikstur sayısı × çevrim başı adet = günlük kapasite
    # ... tüm (kart, gün) ...

    # ── Montaj Talebi: (kart, gün) → adet ───────────────────────────
    demand = {}
    # Örnek: demand[("XC", 0)] = 450
    # ... tüm (kart, gün) ...

    # ── Başlangıç Stokları ───────────────────────────────────────────
    init_kso = {k: 0 for k in KARTLAR}  # Gerçek değerler girilecek
    init_ksm = {k: 0 for k in KARTLAR_MD}
    init_kst = {k: 0 for k in KARTLAR}

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
    st.caption("OR-Tools SCIP · CLSP-SI MILP · Leksikografik Optimizasyon")

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
                f"✅ Onaylı Plan — Setup: {res['phase2_setups']} | "
                f"Toplam Tampon: {res['phase2_total_buffer']:,}")

            with st.expander("OTD Hat Alokasyonu", expanded=True):
                st.dataframe(result_to_otd_df(res), use_container_width=True)

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
            "Leksikografik iki fazlı çözüm: "
            "**Faz 1** setup sayısını minimize eder, "
            "**Faz 2** tampon stoğu minimize eder (setup ≤ z*).")

        col1, col2 = st.columns(2)
        with col1:
            time_limit = st.slider(
                "Çözücü Zaman Limiti (saniye/faz)",
                min_value=10, max_value=600, value=120, step=10)
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

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Faz 1 Setup (z*)",
                              result["phase1_setups"])
                    m2.metric("Faz 2 Setup",
                              result["phase2_setups"])
                    m3.metric("Toplam Tampon",
                              f"{result['phase2_total_buffer']:,}")
                    m4.metric("Çözüm Süresi",
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
                        f"❌ Fizibil çözüm bulunamadı (Faz {result.get('phase', '?')})")
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

            # Özet metrikler
            st.subheader("Model İstatistikleri")
            c1, c2, c3 = st.columns(3)
            c1.metric("Değişken Sayısı", f"{res['num_variables']:,}")
            c2.metric("Kısıt Sayısı", f"{res['num_constraints']:,}")
            c3.metric("Çözüm Süresi", f"{res['solve_time_sec']}s")

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
