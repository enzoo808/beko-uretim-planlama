import streamlit as st
import pandas as pd
import json, base64, os, copy
from datetime import datetime, timedelta
import plotly.graph_objects as go

# =====================================================================
# SAYFA YAPILANDIRMASI
# =====================================================================
_page_icon = "pngwing.com.png" if os.path.exists("pngwing.com.png") else "📺"
st.set_page_config(
    page_title="Beko Şasi Planlama",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================================
# SABİTLER
# =====================================================================
YETKILI_SICILLER = {"26127996"}

KART_RENKLERI = {
    "F4":"#FFB3BA","GB":"#A8E6CF","GL":"#B3D4FF","GX":"#FFFACD","LG":"#D9B3FF",
    "MR":"#FFCBA4","V1":"#B5EAD7","XC":"#C3B1E1","XD":"#FFE0B2","XGB":"#81D4FA",
    "XGS":"#80CBC4","XR":"#F48FB1","Y3":"#C5E1A5","Y4":"#FFCCBC",
}

_DEFAULT_DATES = ["07.05","08.05","09.05","11.05","12.05","13.05","14.05","15.05","16.05","18.05","20.05","21.05","22.05","23.05"]
_DEFAULT_DAYS  = ["Perş","Cum","Cmt","Pzt","Sal","Çar","Perş","Cum","Cmt","Pzt","Çar","Perş","Cum","Cmt"]
SUS_CARDS = ["F4","GB","GL","GX","LG","MR","V1","XC","XD","XGB","XGS","XR","Y3","Y4"]
PROCESS_MAP = {"F4":True,"GB":True,"GL":True,"GX":False,"LG":False,"MR":True,"V1":True,"XC":False,"XD":False,"XGB":True,"XGS":True,"XR":False,"Y3":True,"Y4":True}

_TR_DAYS = {0:"Pzt",1:"Sal",2:"Çar",3:"Perş",4:"Cum",5:"Cmt",6:"Paz"}

TEMPO = {
    "OD0":{"F4":100,"GX":800,"V1":1000,"XGB":927,"XGS":1040,"Y3":880,"Y4":850},
    "OD2":{"F4":200,"GX":700,"LG":450,"V1":1150,"XC":1140,"XD":770,"XGB":880,"XGS":1000,"XR":610,"Y3":920,"Y4":850},
    "OD3":{"V1":1150,"XC":1140,"XD":770,"XGB":880,"XGS":1000,"XR":610,"Y3":920,"Y4":850},
    "OD4":{"F4":500,"LG":550,"V1":0,"XGB":700,"XGS":750},
    "OD6":{"F4":400,"GB":700,"GL":750,"Y3":870,"Y4":750},
}
MD_TEMPO = {"MD1":{"XGS":1100,"XGB":950,"Y4":1000,"F4":0,"GB":800,"GL":780,"MR":600,"V1":1000,"Y3":890},
            "MD2":{"XGS":1100,"XGB":950,"Y4":1000,"F4":0,"GB":800,"GL":780,"MR":600,"V1":1000,"Y3":890}}

# ═══ TA Fikstür Parametreleri (Tempolar sayfasından — kullanıcı düzenleyebilir) ═══
# Formül: ta_daily[c][t] = fikstür_kullanımı[c][t] × TA_ADET_DEFAULT[c]
# Kısıt:  fikstür_kullanımı[c][t] ≤ 2 × TA_FIKSTUR_DEFAULT[c]
TA_FIKSTUR_DEFAULT = {"F4":1,"GB":1,"GL":3,"GX":4,"LG":4,"MR":1,"V1":2,
                      "XC":4,"XD":2,"XGB":3,"XGS":6,"XR":2,"Y3":2,"Y4":2}
TA_ADET_DEFAULT    = {"F4":80,"GB":90,"GL":105,"GX":130,"LG":130,"MR":50,"V1":190,
                      "XC":145,"XD":150,"XGB":138,"XGS":140,"XR":115,"Y3":160,"Y4":157}
TA_TEST_SYS = {"F4":"TESTAR","GB":"TESTAR","GL":"TESTAR","GX":"IPTE","LG":"LG","MR":"TESTAR",
               "V1":"TP200","XC":"IPTE","XD":"TESTAR","XGB":"TESTAR","XGS":"TESTAR",
               "XR":"TESTAR","Y3":"TP200","Y4":"TP200"}

# =====================================================================
# VARSAYILAN SUS VERİSİ
# =====================================================================
def get_default_sus():
    return {
        "otd_alloc":{"OD0":["XGS","XGS","XGB","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","",""],"OD2":["XGB","LG","LG","LG","XC","XGS","LG","LG","LG","LG","XGS","XGS","XGS","XGS"],"OD3":["XC","XC","XR","XR","XR","XR","XR","XR","XR","XC","XC","","",""],"OD4":["LG","LG","LG","LG","LG","LG","LG","LG","LG","","","","",""],"OD6":["Y4","Y4","","","","","","","","","","","",""]},
        "otd_rates":{"OD0":[1,1,1,1,1,1,1,1,1,1,1,1,1,1],"OD2":[1,.3,.7,1,.5,1,1,1,1,1,1,1,1,1],"OD3":[1,1,1,1,1,1,1,1,1,1,1,1,1,1],"OD4":[1,1,.5,1,1,1,.5,1,1,1,.5,1,1,1],"OD6":[1,1,1,1,1,1,1,1,1,1,1,1,1,1]},
        "otd_daily":{"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[550,685,590,1000,550,550,725,1000,1000,450,0,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[1140,1140,0,0,570,0,0,0,0,1140,1140,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[880,0,927,0,0,0,0,0,0,0,0,0,0,0],"XGS":[1040,1040,0,1040,1040,2040,1040,1040,1040,1040,2040,2040,1000,1000],"XR":[0,0,610,610,610,610,610,610,610,0,0,0,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y4":[750,750,0,0,0,0,0,0,0,0,0,0,0,0]},
        "otd_rem":{"F4":[238,238,238,238,238,238,238,238,238,238,238,238,238,238],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[200,200,200,200,200,200,200,200,200,200,200,200,200,200],"LG":[-107,-207,-172,-232,118,18,-82,-137,83,303,-27,-27,-27,-27],"MR":[108,108,108,108,108,108,108,108,108,108,108,108,108,108],"V1":[400,400,400,400,400,400,400,400,400,400,400,400,400,400],"XC":[654,634,614,-546,-1126,-556,-556,-556,-556,-556,584,1724,1724,1724],"XD":[1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069],"XGB":[206,611,136,588,588,588,588,588,588,588,588,588,588,588],"XGS":[955,895,835,-265,-325,-385,555,-605,-1765,-2925,-2985,-2045,-1105,-205],"XR":[380,150,-80,70,220,370,520,670,820,970,510,50,50,50],"Y3":[38,38,38,38,38,38,38,38,38,38,38,38,38,38],"Y4":[910,1160,1410,910,410,410,410,410,410,410,410,410,410,410]},
        "md_alloc":{"MD1":[["XGS"]*14, [""]*14],"MD2":[["XGB","XGB","XGB","XGB","","","","XGS","XGS","XGS","","","",""],["Y4","Y4","Y4","Y4","Y4","","","","","","","","",""]]},
        "md_rates":{"MD1":[[1.0]*14, [1.0]*14],
                    "MD2":[[0.5,0.5,0.5,0.5,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0],
                           [0.5,0.5,0.5,0.5,0.5,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0]]},
        "md_daily":{"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[475,475,475,475,0,0,0,0,0,0,0,0,0,0],"XGS":[1100,1100,1100,1100,1100,1100,1100,2200,2200,2200,1100,1100,1100,1100],"XR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y4":[500,500,500,500,500,0,0,0,0,0,0,0,0,0]},
        "md_rem":{"F4":[28,28,28,28,28,28,28,28,28,28,28,28,28,28],"GB":[1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188],"GL":[644,644,644,644,644,644,644,644,644,644,644,644,644,644],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"MR":[347,347,347,347,347,347,347,347,347,347,347,347,347,347],"V1":[27,27,27,27,27,27,27,27,27,27,27,27,27,27],"XC":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[-241,-594,-947,-1300,-825,-825,-825,-825,-825,-825,-1653,-1653,-1653,-1653],"XGS":[-717,-737,-477,-217,43,-257,-557,-857,-57,743,1543,1243,943,3143],"XR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y3":[24,24,24,24,24,24,24,24,24,24,24,24,24,24],"Y4":[-74,112,141,13,-115,-243,-871,-871,-871,-871,-871,-871,-871,-871]},
        "ta_daily":{"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[650,650,650,650,650,650,650,780,780,780,780,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[1160,1160,1160,1160,580,0,0,0,0,0,0,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[828,828,828,828,0,0,0,0,0,0,828,0,0,0],"XGS":[840,1120,840,840,840,1400,1400,1400,1400,1400,1400,1400,1400,0],"XR":[0,230,230,460,460,460,460,460,460,460,460,460,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y4":[628,314,471,628,628,628,628,0,0,0,0,0,0,0]},
        "ta_rem":{"F4":[349,349,349,349,349,349,349,349,349,349,349,349,349,349],"GB":[575,575,575,575,575,-90,-90,-90,-90,-90,-90,-90,-90,-90],"GL":[416,416,416,416,416,416,416,416,416,416,416,416,416,416],"GX":[667,667,667,117,117,117,-180,-180,-180,-180,-180,-180,-180,-180],"LG":[421,821,1421,1520,1220,369,-231,-729,-1092,-1313,-734,21,21,-5],"MR":[308,308,308,308,308,308,308,-45,-96,-96,-96,-96,-96,-96],"V1":[-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9],"XC":[1166,926,746,1156,1886,2466,2466,2466,2466,2466,2268,2268,1769,1282],"XD":[225,123,123,119,119,119,119,119,119,119,119,-616,-990,-1215],"XGB":[458,21,-237,-9,819,819,818,818,818,818,818,806,463,183],"XGS":[610,200,321,861,1701,2080,2534,2876,3076,1691,507,636,823,1380],"XR":[508,508,523,753,268,255,248,100,60,520,741,793,992,491],"Y3":[157,157,157,157,157,157,157,157,157,157,157,157,157,50],"Y4":[-99,529,843,214,-58,62,690,1318,1318,1318,1318,1318,1318,1318]},
        "assembly":{"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,665,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,550,0,0,297,0,0,0,0,0,0,0],"LG":[279,250,50,551,950,1501,1250,1148,1143,1001,201,25,0,26],"MR":[0,0,0,0,0,0,0,353,51,0,0,0,0,0],"V1":[258,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[618,1400,1340,750,430,0,0,0,0,0,198,0,499,487],"XD":[625,102,0,4,0,0,0,0,0,0,0,735,374,225],"XGB":[205,1265,1086,600,0,0,1,0,0,0,0,840,343,280],"XGS":[1681,1250,999,300,0,461,946,1058,1200,2785,2584,1271,1213,843],"XR":[2,0,215,0,945,473,467,608,500,0,239,408,261,501],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,107],"Y4":[881,0,0,1100,900,508,0,0,0,0,0,0,0,0]},
        "init":{"F4":{"o":238,"m":28,"t":349},"GB":{"o":0,"m":1188,"t":575},"GL":{"o":0,"m":644,"t":416},"GX":{"o":200,"m":60,"t":667},"LG":{"o":543,"m":257,"t":700},"MR":{"o":108,"m":347,"t":308},"V1":{"o":400,"m":27,"t":249},"XC":{"o":1814,"m":57,"t":1784},"XD":{"o":1069,"m":12,"t":850},"XGB":{"o":681,"m":587,"t":663},"XGS":{"o":2055,"m":123,"t":2291},"XR":{"o":380,"m":6,"t":510},"Y3":{"o":38,"m":24,"t":157},"Y4":{"o":1410,"m":554,"t":782}},
        # ═══ TA Fikstür Kullanımı (kart × gün) — günde 2× fikstür_sayısı sınırlı ═══
        "ta_fixture_usage":{
            "F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            "GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            "LG":[5,5,5,5,5,5,5,6,6,6,6,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            "V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[8,8,8,8,4,0,0,0,0,0,0,0,0,0],
            "XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[6,6,6,6,0,0,0,0,0,0,6,0,0,0],
            "XGS":[6,8,6,6,6,10,10,10,10,10,10,10,10,0],
            "XR":[0,2,2,4,4,4,4,4,4,4,4,4,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            "Y4":[4,2,3,4,4,4,4,0,0,0,0,0,0,0],
        },
        # ═══ TA parametreleri (kullanıcı düzenleyebilir, varsayılan Tempolar sayfasından) ═══
        "ta_fixture_count":dict(TA_FIKSTUR_DEFAULT),
        "ta_per_cycle":dict(TA_ADET_DEFAULT),
    }

# =====================================================================
# SESSION STATE
# =====================================================================
if "sus" not in st.session_state:
    st.session_state.sus = get_default_sus()

# ═══ Geriye dönük uyumluluk: eski session'larda eksik TA fikstür anahtarlarını ekle ═══
_default_sus = get_default_sus()
for _k in ("ta_fixture_usage","ta_fixture_count","ta_per_cycle","md_rates"):
    if _k not in st.session_state.sus:
        st.session_state.sus[_k] = _default_sus[_k]
# md_alloc: tek satırlı eski hatları çok satırlıya çıkar
for _ln in ("MD1","MD2"):
    _rows = st.session_state.sus.get("md_alloc",{}).get(_ln, [])
    if _rows and not isinstance(_rows[0], list):
        st.session_state.sus["md_alloc"][_ln] = [_rows, [""]*len(_rows)]
    elif len(_rows) < 2:
        nd = len(st.session_state.sus["md_alloc"][_ln][0]) if _rows else 14
        st.session_state.sus["md_alloc"][_ln].append([""]*nd)
    # md_rates aynı sayıda satır olsun
    n_alloc_rows = len(st.session_state.sus["md_alloc"][_ln])
    md_rates_lines = st.session_state.sus.get("md_rates",{}).get(_ln, [])
    while len(md_rates_lines) < n_alloc_rows:
        nd = len(st.session_state.sus["md_alloc"][_ln][0])
        md_rates_lines.append([1.0]*nd)
    st.session_state.sus.setdefault("md_rates",{})[_ln] = md_rates_lines

if "opt_result" not in st.session_state:
    st.session_state.opt_result = None
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.auth_sicil = None

# YENİ — Bölüm bazlı optimizasyon sonuçları
if "otd_opt_res" not in st.session_state: st.session_state.otd_opt_res = None
if "md_opt_res"  not in st.session_state: st.session_state.md_opt_res  = None
if "ta_opt_res"  not in st.session_state: st.session_state.ta_opt_res  = None
# YENİ — Upload dedup
for _k in ("last_otd_up", "last_md_up", "last_ta_up"):
    if _k not in st.session_state: st.session_state[_k] = None

# ═══ v3 EKLENTİLERİ — Tarih Aralığı & Manuel Düzenleme ═══
if "date_start_idx" not in st.session_state: st.session_state.date_start_idx = 0
if "date_end_idx"   not in st.session_state: st.session_state.date_end_idx   = 13
if "manual_edit_alloc" not in st.session_state: st.session_state.manual_edit_alloc = None
if "manual_edit_before" not in st.session_state: st.session_state.manual_edit_before = None
if "manual_impact" not in st.session_state: st.session_state.manual_impact = None
# ═══ v3.4: Kalıcı önizleme durumu — oran düzenleme sırasında kaybolmaz ═══
if "preview_active" not in st.session_state: st.session_state.preview_active = False
if "preview_alloc" not in st.session_state: st.session_state.preview_alloc = None
if "preview_rates" not in st.session_state: st.session_state.preview_rates = None
if "preview_setups" not in st.session_state: st.session_state.preview_setups = None
# ═══ MD Manuel Düzenleme önizlemesi ═══
if "md_preview_active" not in st.session_state: st.session_state.md_preview_active = False
if "md_preview_alloc"  not in st.session_state: st.session_state.md_preview_alloc  = None
if "md_preview_rates"  not in st.session_state: st.session_state.md_preview_rates  = None
if "md_preview_setups" not in st.session_state: st.session_state.md_preview_setups = None
# ═══ TA Manuel Düzenleme önizlemesi ═══
if "ta_preview_active"  not in st.session_state: st.session_state.ta_preview_active  = False
if "ta_preview_usage"   not in st.session_state: st.session_state.ta_preview_usage   = None
if "ta_preview_fcount"  not in st.session_state: st.session_state.ta_preview_fcount  = None
if "ta_preview_percycle" not in st.session_state: st.session_state.ta_preview_percycle = None

# ═══ v3.5: Dinamik planlama ufku (URL query param ile kalıcı) ═══
def _read_horizon_extra_from_qp():
    """URL ?ext=N parametresinden ek gün sayısını oku (F5 sonrası kalıcılık)."""
    try:
        v = st.query_params.get("ext", None)
        if v is None: return 0
        if isinstance(v, list): v = v[0] if v else "0"
        return max(0, min(int(v), 400))
    except Exception:
        return 0

def _persist_horizon_to_qp():
    """Mevcut ek gün sayısını URL query param'a yaz."""
    try:
        extra = len(st.session_state.dyn_dates) - len(_DEFAULT_DATES)
        if extra > 0:
            st.query_params["ext"] = str(extra)
        else:
            if "ext" in st.query_params:
                del st.query_params["ext"]
    except Exception:
        pass

def _build_horizon_lists(extra_days):
    """Default + extra gün eklenerek (Pazar atlanır) tarih/gün listeleri kurar."""
    dates = list(_DEFAULT_DATES)
    days  = list(_DEFAULT_DAYS)
    if extra_days <= 0:
        return dates, days
    last_str = dates[-1]
    dd, mm = int(last_str[:2]), int(last_str[3:])
    last_dt = datetime(2026, mm, dd)
    added = 0
    while added < extra_days:
        last_dt += timedelta(days=1)
        if last_dt.weekday() == 6: continue
        dates.append(last_dt.strftime("%d.%m"))
        days.append(_TR_DAYS[last_dt.weekday()])
        added += 1
    return dates, days

if "dyn_dates" not in st.session_state:
    _extra = _read_horizon_extra_from_qp()
    _d, _dy = _build_horizon_lists(_extra)
    st.session_state.dyn_dates = _d
    st.session_state.dyn_days  = _dy
if "dyn_days"  not in st.session_state: st.session_state.dyn_days  = list(_DEFAULT_DAYS)
# Bekleyen ufku değişikliği (sicil onayı için)
if "pending_horizon" not in st.session_state: st.session_state.pending_horizon = 0

# Query param'dan gelen uzun ufuk için sus arrays'lerini pad'le
_nd_now = len(st.session_state.dyn_dates)
if _nd_now > len(_DEFAULT_DATES):
    # Slider sonunu da uzat (F5 sonrası daraltmasın)
    if st.session_state.get("date_end_idx", 13) < _nd_now - 1:
        st.session_state.date_end_idx = _nd_now - 1
    _s = st.session_state.sus
    for _key in ("otd_daily","otd_rem","md_daily","md_rem","ta_daily","ta_rem","assembly","ta_fixture_usage"):
        for _c in SUS_CARDS:
            _arr = _s.get(_key, {}).get(_c, [])
            if len(_arr) < _nd_now: _s[_key][_c] = _arr + [0] * (_nd_now - len(_arr))
    for _ln in _s.get("otd_alloc", {}):
        _a = _s["otd_alloc"][_ln]
        if isinstance(_a[0], list):
            for _row in _a:
                if len(_row) < _nd_now: _row.extend([""] * (_nd_now - len(_row)))
        elif len(_a) < _nd_now:
            _s["otd_alloc"][_ln] = _a + [""] * (_nd_now - len(_a))
    for _ln in _s.get("md_alloc", {}):
        for _row in _s["md_alloc"][_ln]:
            if isinstance(_row, list) and len(_row) < _nd_now:
                _row.extend([""] * (_nd_now - len(_row)))
    for _ln in _s.get("otd_rates", {}):
        _a = _s["otd_rates"][_ln]
        if len(_a) < _nd_now: _s["otd_rates"][_ln] = _a + [1.0] * (_nd_now - len(_a))
    for _ln in _s.get("md_rates", {}):
        for _row in _s["md_rates"][_ln]:
            if isinstance(_row, list) and len(_row) < _nd_now:
                _row.extend([1.0] * (_nd_now - len(_row)))

# Modül seviyesinde referans — tüm fonksiyonlar bunları kullanır
SUS_DATES = st.session_state.dyn_dates
SUS_DAYS  = st.session_state.dyn_days
N_DAYS    = len(SUS_DATES)

def extend_horizon(n_extra):
    """Planlama ufkunu n_extra gün uzatır (Pazar hariç). Tüm veri dizilerini pad'ler."""
    last_str = st.session_state.dyn_dates[-1]   # "23.05"
    dd, mm = int(last_str[:2]), int(last_str[3:])
    last_dt = datetime(2026, mm, dd)
    added = 0
    while added < n_extra:
        last_dt += timedelta(days=1)
        if last_dt.weekday() == 6:  # Pazar — atla
            continue
        st.session_state.dyn_dates.append(last_dt.strftime("%d.%m"))
        st.session_state.dyn_days.append(_TR_DAYS[last_dt.weekday()])
        added += 1
    # Tüm veri dizilerini pad'le
    sus = st.session_state.sus
    new_n = len(st.session_state.dyn_dates)
    for key in ["otd_daily","otd_rem","md_daily","md_rem","ta_daily","ta_rem","assembly","ta_fixture_usage"]:
        for c in SUS_CARDS:
            arr = sus.get(key, {}).get(c, [])
            if len(arr) < new_n:
                sus[key][c] = arr + [0] * (new_n - len(arr))
    for key in ["otd_alloc"]:
        for ln in sus.get(key, {}):
            arr = sus[key][ln]
            if isinstance(arr[0], list):
                for row in arr:
                    if len(row) < new_n: row.extend([""] * (new_n - len(row)))
            else:
                if len(arr) < new_n: sus[key][ln] = arr + [""] * (new_n - len(arr))
    for key in ["md_alloc"]:
        for ln in sus.get(key, {}):
            rows = sus[key][ln]
            for row in rows:
                if isinstance(row, list) and len(row) < new_n:
                    row.extend([""] * (new_n - len(row)))
    for ln in sus.get("otd_rates", {}):
        arr = sus["otd_rates"][ln]
        if len(arr) < new_n: sus["otd_rates"][ln] = arr + [1.0] * (new_n - len(arr))
    for ln in sus.get("md_rates", {}):
        for row in sus["md_rates"][ln]:
            if isinstance(row, list) and len(row) < new_n:
                row.extend([1.0] * (new_n - len(row)))
    st.session_state.sus = recalc_stocks(sus)

sus = st.session_state.sus

# =====================================================================
# OPTİMİZASYON MOTORU  (orijinal, değişmedi)
# =====================================================================
def recalc_stocks(plan):
    p = copy.deepcopy(plan)
    init = p["init"]
    nd = len(st.session_state.dyn_dates)
    for c in SUS_CARDS:
        otd = p["otd_daily"].get(c, [0]*nd)
        asm = p["assembly"].get(c, [0]*nd)
        md  = p["md_daily"].get(c, [0]*nd)
        ta  = p["ta_daily"].get(c, [0]*nd)
        needs_md = PROCESS_MAP.get(c, False)
        cum_otd = 0; cum_down = 0; otd_rem = []
        for i in range(nd):
            cum_otd  += otd[i] if i < len(otd) else 0
            cum_down += (md[i] if needs_md else ta[i]) if i < len(md if needs_md else ta) else 0
            otd_rem.append(init.get(c,{}).get("o",0) + cum_otd - cum_down)
        p["otd_rem"][c] = otd_rem
        if needs_md:
            cum_md = 0; cum_ta_d = 0; md_rem = []
            for i in range(nd):
                cum_md   += md[i] if i < len(md) else 0
                cum_ta_d += ta[i] if i < len(ta) else 0
                md_rem.append(init.get(c,{}).get("m",0) + cum_md - cum_ta_d)
            p["md_rem"][c] = md_rem
        cum_ta = 0; cum_asm = 0; ta_rem = []
        for i in range(nd):
            cum_ta  += ta[i] if i < len(ta) else 0
            cum_asm += asm[i] if i < len(asm) else 0
            ta_rem.append(init.get(c,{}).get("t",0) + cum_ta - cum_asm)
        p["ta_rem"][c] = ta_rem
    return p

def run_optimization(current_plan):
    plan = copy.deepcopy(current_plan)
    nd = len(st.session_state.dyn_dates)
    proposals = []
    violations = []
    for stage, rem_key, stage_label in [("OTD","otd_rem","KSO"),("MD","md_rem","KSM"),("TA","ta_rem","KST")]:
        for c in SUS_CARDS:
            if stage == "MD" and not PROCESS_MAP.get(c): continue
            rem = plan[rem_key].get(c, [0]*nd)
            for i, v in enumerate(rem):
                if v < 0:
                    violations.append({"card":c,"stage":stage,"day":i,"deficit":abs(v),"rem_key":rem_key,"label":stage_label})
    if not violations:
        return {"status":"optimal","proposals":[],"message":"Plan zaten fizibil — tüm tampon stoklar pozitif!","new_plan":plan}
    applied = copy.deepcopy(plan)
    for v in sorted(violations, key=lambda x: (x["day"], -x["deficit"])):
        c, stage, day, deficit = v["card"], v["stage"], v["day"], v["deficit"]
        if stage == "OTD":
            alloc = applied["otd_alloc"]
            for d in range(max(0, day-2), day+1):
                for line in ["OD0","OD2","OD3","OD4","OD6"]:
                    line_alloc = alloc.get(line, [""]*nd)
                    if d < len(line_alloc) and line_alloc[d] == "":
                        cap = TEMPO.get(line, {}).get(c, 0)
                        if cap > 0:
                            old_val = applied["otd_daily"][c][d] if d < len(applied["otd_daily"].get(c,[])) else 0
                            add = min(cap, deficit)
                            proposals.append({"type":"OTD üretim ekle","card":c,"day":d+1,"date":SUS_DATES[d] if d<len(SUS_DATES) else f"G{d+1}","line":line,"old":old_val,"new":old_val+add,"reason":f"{c} KSO Gün {day+1}'de −{deficit:,} açık","impact":f"+{add:,} adet üretim"})
                            applied["otd_daily"][c][d] += add
                            line_alloc[d] = c
                            deficit -= add
                            if deficit <= 0: break
                    if deficit <= 0: break
                if deficit <= 0: break
        elif stage == "MD":
            for d in range(max(0, day-2), day+1):
                for line in ["MD1","MD2"]:
                    rows = applied["md_alloc"].get(line, [])
                    for row in rows:
                        if d < len(row) and row[d] == "":
                            cap = MD_TEMPO.get(line,{}).get(c, 0)
                            if cap > 0:
                                old_val = applied["md_daily"][c][d]
                                add = min(cap, deficit)
                                proposals.append({"type":"MD üretim ekle","card":c,"day":d+1,"date":SUS_DATES[d],"line":line,"old":old_val,"new":old_val+add,"reason":f"{c} KSM Gün {day+1}'de −{deficit:,} açık","impact":f"+{add:,} adet MD üretim"})
                                applied["md_daily"][c][d] += add
                                row[d] = c
                                deficit -= add
                                if deficit <= 0: break
                        if deficit <= 0: break
                    if deficit <= 0: break
                if deficit <= 0: break
    applied = recalc_stocks(applied)
    remaining = 0
    for c in SUS_CARDS:
        for rem_key in ["otd_rem","md_rem","ta_rem"]:
            if rem_key == "md_rem" and not PROCESS_MAP.get(c): continue
            remaining += sum(1 for v in applied[rem_key].get(c,[]) if v < 0)
    suggestions = []
    if remaining > 0:
        suggestions.append("Tüm ihlaller otomatik çözülemedi — aşağıdaki öneriler uygulanabilir:")
        for c in SUS_CARDS:
            for rem_key, label in [("otd_rem","OTD"),("md_rem","MD"),("ta_rem","TA")]:
                if rem_key == "md_rem" and not PROCESS_MAP.get(c): continue
                negs = [(i,v) for i,v in enumerate(applied[rem_key].get(c,[])) if v < 0]
                if negs:
                    worst_day, worst_val = min(negs, key=lambda x: x[1])
                    suggestions.append(f"• {c} {label}: Gün {worst_day+1}'de {worst_val:,} açık — mesai veya hat eklenmesi gerekli")
    else:
        suggestions.append("✅ Tüm öneriler uygulandığında plan tamamen fizibil hale gelir.")
        suggestions.append("📈 Daha iyi hale getirmek için:")
        for c in SUS_CARDS:
            min_ta = min(applied["ta_rem"].get(c,[999]))
            if 0 <= min_ta < 200:
                suggestions.append(f"• {c} TA stoğu minimum {min_ta} — güvenlik marjı düşük, TA fikstür artışı düşünülebilir")
    status = "feasible" if remaining == 0 else "partial"
    return {"status":status,"proposals":proposals,"new_plan":applied,"remaining_violations":remaining,"suggestions":suggestions,"message":"Plan optimize edildi!" if remaining==0 else f"{remaining} ihlal kaldı — ek müdahale gerekli"}

# =====================================================================
# YENİ — Bölüm Bazlı Yardımcı Fonksiyonlar
# =====================================================================
def run_stage_opt(plan, stage):
    """Sadece belirtilen aşama (OTD/MD/TA) için optimizasyon çalıştırır."""
    full = run_optimization(plan)
    stage_props = [p for p in full.get("proposals", []) if p["type"].startswith(stage)]
    # Sadece bu aşamanın önerilerini uygula
    new_plan = copy.deepcopy(plan)
    for p in stage_props:
        c, d = p["card"], p["day"] - 1
        if stage == "OTD":
            new_plan["otd_daily"][c][d] = p["new"]
            if p.get("line"):
                alloc = new_plan["otd_alloc"].get(p["line"], [""]*N_DAYS)
                if d < len(alloc): alloc[d] = c
        elif stage == "MD":
            new_plan["md_daily"][c][d] = p["new"]
        elif stage == "TA":
            new_plan["ta_daily"][c][d] = p["new"]
    new_plan = recalc_stocks(new_plan)
    rem_map = {"OTD": "otd_rem", "MD": "md_rem", "TA": "ta_rem"}
    remaining = sum(1 for c in SUS_CARDS for v in new_plan.get(rem_map[stage], {}).get(c, []) if v < 0)
    if stage == "MD":
        remaining = sum(1 for c in SUS_CARDS if PROCESS_MAP.get(c) for v in new_plan["md_rem"].get(c, []) if v < 0)
    status = "feasible" if remaining == 0 else "partial"
    msg = f"✅ {stage} tamamen fizibil!" if remaining == 0 else f"⚠️ {stage}: {remaining} ihlal kaldı — ek kapasite gerekli"
    return {"status": status, "proposals": stage_props, "new_plan": new_plan, "remaining": remaining, "message": msg}

def apply_stage_proposals(proposals, plan, stage, approvals=None):
    """Onaylanan önerileri plana uygular ve stokları yeniden hesaplar."""
    applied = copy.deepcopy(plan)
    count = 0
    for i, p in enumerate(proposals):
        if approvals is not None and not approvals.get(i, True):
            continue
        c, d = p["card"], p["day"] - 1
        if stage == "OTD":
            applied["otd_daily"][c][d] = p["new"]
            if p.get("line"):
                alloc = applied["otd_alloc"].get(p["line"], [""]*N_DAYS)
                if d < len(alloc): alloc[d] = c
        elif stage == "MD":
            applied["md_daily"][c][d] = p["new"]
        elif stage == "TA":
            applied["ta_daily"][c][d] = p["new"]
        count += 1
    return recalc_stocks(applied), count

def process_upload_file(upfile, state_key):
    """Aynı dosyanın tekrar işlenmesini önler, yeni dosyayı döner."""
    if upfile is None: return None
    uid = f"{upfile.name}_{upfile.size}"
    if st.session_state.get(state_key) == uid: return None
    st.session_state[state_key] = uid
    return upfile

def parse_upload_json(upfile):
    """Yüklenen JSON dosyasını güvenli biçimde parse eder."""
    try:
        return json.loads(upfile.getvalue().decode("utf-8")), None
    except Exception as e:
        return None, str(e)

def parse_upload_csv(upfile, target_dict_key):
    """
    CSV formatı: Kart, 07.05, 08.05, ..., 23.05
    target_dict_key: 'otd_daily' / 'md_daily' / 'ta_daily' gibi bir anahtar
    """
    try:
        df = pd.read_csv(upfile)
        result = {}
        for _, row in df.iterrows():
            kart = str(row.iloc[0]).strip()
            if kart in SUS_CARDS:
                vals = [int(v) for v in row.iloc[1:15]]
                result[kart] = vals
        return {target_dict_key: result}, None
    except Exception as e:
        return None, str(e)

# =====================================================================
# CSS  (orijinal, değişmedi)
# =====================================================================
bg_css = ""
for img_name in ["aaa.jpg","aaa.jpeg","aaa.png"]:
    if os.path.exists(img_name):
        with open(img_name,"rb") as f: bg_b64 = base64.b64encode(f.read()).decode()
        bg_css = (
            f".stApp{{"
            f"background:url('data:image/jpeg;base64,{bg_b64}');"
            f"background-size:cover;background-position:center;background-attachment:fixed;"
            f"}}"
            f".stApp::before{{"
            f"content:'';position:fixed;inset:0;z-index:0;pointer-events:none;"
            f"background:radial-gradient(ellipse at 50% 40%,rgba(0,8,30,0.18) 0%,rgba(0,5,22,0.42) 60%,rgba(0,3,18,0.65) 100%);"
            f"}}"
            f".stApp>*{{position:relative;z-index:1;}}"
        )
        break
logo_b64 = ""
for ln in ["pngwing.com.png","pngwing_com.png","logo.png"]:
    if os.path.exists(ln):
        with open(ln,"rb") as f: logo_b64 = base64.b64encode(f.read()).decode()
        break

st.markdown(f"""<style>
    {bg_css}
    footer{{visibility:hidden!important;display:none!important;}}
    /* ═══ v3.6: Streamlit varsayılan UI elementlerini gizle ═══ */
    /* Sadece spesifik butonları gizle — sidebar toggle açık kalsın */
    [data-testid="stDeployButton"]{{display:none!important;}}
    [data-testid="stMainMenu"]{{display:none!important;}}
    [data-testid="stStatusWidget"]{{display:none!important;}}
    [data-testid="stDecoration"]{{display:none!important;}}
    [data-testid="stHeaderActionElements"] > div:not(:has([data-testid="stSidebarCollapsedControl"])){{display:none!important;}}
    #MainMenu{{visibility:hidden!important;display:none!important;}}
    .viewerBadge_container__1QSob, .viewerBadge_link__qRIco, .styles_viewerBadge__CvC9N{{display:none!important;}}
    [class*="viewerBadge"]{{display:none!important;}}
    a[href*="streamlit.io"]{{display:none!important;}}
    iframe[title*="Streamlit"]{{display:none!important;}}
    /* Sidebar açma butonunu mutlaka göster */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    button[kind="header"]{{display:flex!important;visibility:visible!important;opacity:1!important;}}
    header[data-testid="stHeader"]{{background:rgba(0,15,45,0.4)!important;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);height:auto!important;}}
    @keyframes fadeSlideIn{{from{{opacity:0;transform:translateY(12px);}}to{{opacity:1;transform:translateY(0);}}}}
    .block-container{{max-width:1300px;animation:fadeSlideIn 0.5s ease-out;}}
    .stTabs [data-baseweb="tab-panel"]{{animation:fadeSlideIn 0.35s ease-out;}}
    section[data-testid="stSidebar"]{{
        background:
            linear-gradient(180deg,#020a1f 0%,#04122e 50%,#020a1f 100%)
        !important;
        border-right:1px solid rgba(147,197,253,0.10);
        position:relative;
    }}
    /* Sidebar scroll fix — Streamlit'in iç container'larını hedefle */
    section[data-testid="stSidebar"] > div,
    section[data-testid="stSidebar"] > div > div,
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{{
        overflow-y:auto!important;
        max-height:100vh!important;
        height:auto!important;
    }}
    /* Scrollbar stili — Beko mavisi */
    section[data-testid="stSidebar"] ::-webkit-scrollbar{{width:6px;}}
    section[data-testid="stSidebar"] ::-webkit-scrollbar-track{{background:rgba(255,255,255,0.02);}}
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb{{background:rgba(37,99,235,0.4);border-radius:3px;}}
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover{{background:rgba(37,99,235,0.7);}}
    /* Sidebar dekoratif accent — premium minimal */
    section[data-testid="stSidebar"]::after{{
        content:'';position:absolute;top:0;right:0;bottom:0;width:1px;
        background:linear-gradient(180deg,transparent 0%,rgba(37,99,235,0.4) 30%,rgba(6,182,212,0.3) 70%,transparent 100%);
        pointer-events:none;
    }}
    section[data-testid="stSidebar"] .stSelectbox label,section[data-testid="stSidebar"] h2{{color:#fff!important;}}
    /* ═══ v3.6: Sidebar branding — premium minimal ═══ */
    .sb-glow{{display:none;}}
    .sb-top-accent{{height:80px;margin:-1rem -1rem 12px;background:radial-gradient(ellipse at 50% 0%,rgba(37,99,235,0.18) 0%,rgba(6,182,212,0.08) 40%,transparent 75%);position:relative;pointer-events:none;}}
    .sb-brand{{padding:0 12px 16px;text-align:center;border-bottom:1px solid rgba(147,197,253,0.08);margin-bottom:18px;position:relative;}}
    .sb-brand::after{{content:'';position:absolute;bottom:-1px;left:30%;right:30%;height:1px;background:linear-gradient(90deg,transparent,rgba(37,99,235,0.5),transparent);}}
    .sb-brand img{{height:54px;margin-bottom:10px;filter:drop-shadow(0 4px 12px rgba(37,99,235,0.35));}}
    .sb-brand-title{{font-size:0.7rem;color:rgba(255,255,255,0.85);letter-spacing:4px;text-transform:uppercase;font-weight:700;margin:0;}}
    .sb-brand-sub{{font-size:0.6rem;color:rgba(147,197,253,0.5);letter-spacing:2px;margin:4px 0 0;text-transform:uppercase;}}
    .sb-section{{margin:14px 0 8px;padding:0 2px;}}
    .sb-section-title{{font-size:0.68rem;color:rgba(147,197,253,0.55);text-transform:uppercase;letter-spacing:2.5px;font-weight:700;margin:0 0 10px 2px;display:flex;align-items:center;gap:6px;}}
    .sb-section-title::after{{content:'';flex:1;height:1px;background:linear-gradient(90deg,rgba(147,197,253,0.15) 0%,transparent 100%);margin-left:6px;}}
    .sb-divider{{height:1px;background:linear-gradient(90deg,transparent 0%,rgba(147,197,253,0.12) 30%,rgba(147,197,253,0.12) 70%,transparent 100%);margin:20px 0 14px;}}
    .sb-stat{{display:flex;justify-content:space-between;align-items:center;padding:9px 12px;border-radius:8px;background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.04);margin-bottom:5px;transition:all 0.2s ease;}}
    .sb-stat:hover{{background:rgba(255,255,255,0.05);border-color:rgba(147,197,253,0.15);}}
    .sb-stat-label{{font-size:0.72rem;color:#94a3b8;font-weight:500;letter-spacing:0.5px;}}
    .sb-stat-val{{font-size:0.88rem;font-weight:800;color:#93c5fd;}}
    .sb-stat-bad{{color:#f87171!important;}}

    /* ═══ v3.8: Tıklanabilir ihlal stat butonları — sadece primary kind ═══ */
    section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]{{
        background:linear-gradient(90deg,rgba(239,68,68,0.10),rgba(239,68,68,0.04))!important;
        border:1px solid rgba(239,68,68,0.28)!important;
        color:#fca5a5!important;
        font-size:0.78rem!important;font-weight:600!important;
        padding:10px 14px!important;
        border-radius:9px!important;
        text-align:left!important;
        letter-spacing:0.5px!important;
        white-space:pre!important;
        transition:all 0.18s ease!important;
        box-shadow:none!important;
    }}
    section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover{{
        background:linear-gradient(90deg,rgba(239,68,68,0.18),rgba(239,68,68,0.08))!important;
        border-color:rgba(239,68,68,0.5)!important;
        transform:translateX(2px);
        color:#fecaca!important;
    }}
    div[data-testid="stMetric"]{{background:rgba(0,15,50,0.55);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:16px;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);}}
    div[data-testid="stMetric"] label{{color:#93c5fd!important;}}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"]{{color:#fff!important;}}
    .stTabs [data-baseweb="tab-list"]{{gap:8px;}}
    .stTabs [data-baseweb="tab"]{{background:rgba(255,255,255,0.05);border-radius:8px;color:#93c5fd;}}
    .stTabs [aria-selected="true"]{{background:#2563eb!important;color:#fff!important;}}
    h1,h2,h3{{color:#fff!important;}}
    .stCaption{{color:#cbd5e1!important;}}
    hr{{border-color:rgba(255,255,255,0.1)!important;}}
    .otd-table{{width:100%;border-collapse:separate;border-spacing:3px;font-family:'Segoe UI',sans-serif;}}
    .otd-table th{{background:rgba(37,99,235,0.35);color:#93c5fd;padding:8px 5px;font-size:0.75rem;font-weight:600;text-align:center;border-radius:6px;backdrop-filter:blur(6px);}}
    .otd-table td{{padding:7px 5px;text-align:center;font-weight:700;font-size:0.78rem;border-radius:6px;color:#1e293b;}}
    .otd-rh{{background:rgba(0,0,0,0.45)!important;color:#93c5fd!important;font-weight:700;text-align:left!important;padding-left:10px!important;min-width:48px;backdrop-filter:blur(6px);}}
    .otd-none{{background:rgba(255,255,255,0.04)!important;color:#475569!important;font-weight:400;}}
    .status-card{{background:rgba(0,15,50,0.5);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:16px;margin-bottom:8px;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);}}
    .status-green{{border-left:4px solid #22c55e;}} .status-yellow{{border-left:4px solid #f59e0b;}} .status-red{{border-left:4px solid #ef4444;}}
    /* ═══ v3.1: Expander arka plan ═══ */
    details[data-testid="stExpander"]{{background:rgba(0,12,40,0.45);border-radius:12px;backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);}}
    /* ═══ v3.1: Oran alt-metin stili ═══ */
    .rate-sub{{font-size:0.58rem;font-weight:600;opacity:0.85;display:block;margin-top:1px;}}
    .status-green{{border-left:4px solid #22c55e;}} .status-yellow{{border-left:4px solid #f59e0b;}} .status-red{{border-left:4px solid #ef4444;}}
    .big-num{{font-size:1.6rem;font-weight:800;color:#fff;line-height:1.1;}}
    .big-label{{font-size:0.72rem;color:#93c5fd;margin-top:2px;}}
    .rozet-ref{{background:rgba(147,197,253,0.15);color:#93c5fd;padding:4px 12px;border-radius:16px;font-size:0.8rem;font-weight:600;border:1px solid rgba(147,197,253,0.3);}}
    .rozet-opt{{background:rgba(34,197,94,0.15);color:#22c55e;padding:4px 12px;border-radius:16px;font-size:0.8rem;font-weight:600;border:1px solid rgba(34,197,94,0.3);}}
    .rozet-partial{{background:rgba(245,158,11,0.15);color:#f59e0b;padding:4px 12px;border-radius:16px;font-size:0.8rem;font-weight:600;border:1px solid rgba(245,158,11,0.3);}}

    /* ═══ v3: Manuel düzenleme stiller ═══ */
    .impact-box{{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:16px;margin:8px 0;}}
    .impact-fixed{{border-left:4px solid #22c55e;}} .impact-new-viol{{border-left:4px solid #ef4444;}}
    [data-testid="stDataEditor"]{{border-radius:10px;overflow:hidden;}}
    [data-testid="stDataEditor"] td{{font-weight:600!important;}}

    /* ═══ v3.7: Splash Screen — Beko logo açılış animasyonu ═══ */
    @keyframes splashFade{{
        0%{{opacity:1;visibility:visible;}}
        80%{{opacity:1;visibility:visible;}}
        100%{{opacity:0;visibility:hidden;}}
    }}
    @keyframes splashLogo{{
        0%{{opacity:0;transform:scale(0.7) translateY(20px);}}
        40%{{opacity:1;transform:scale(1.05) translateY(0);}}
        60%{{opacity:1;transform:scale(1) translateY(0);}}
        100%{{opacity:0;transform:scale(0.95) translateY(-10px);}}
    }}
    @keyframes splashRing{{
        0%{{opacity:0;transform:scale(0.5) rotate(0deg);border-width:3px;}}
        50%{{opacity:0.4;transform:scale(1.2) rotate(180deg);border-width:1px;}}
        100%{{opacity:0;transform:scale(1.8) rotate(360deg);border-width:0px;}}
    }}
    @keyframes splashSubtitle{{
        0%{{opacity:0;transform:translateY(8px);letter-spacing:8px;}}
        50%{{opacity:1;transform:translateY(0);letter-spacing:6px;}}
        100%{{opacity:0;transform:translateY(-4px);letter-spacing:5px;}}
    }}
    .beko-splash{{
        position:fixed;inset:0;z-index:99999;
        background:radial-gradient(ellipse at center,#04122e 0%,#020817 100%);
        display:flex;flex-direction:column;align-items:center;justify-content:center;
        animation:splashFade 2.4s ease-in-out forwards;
        pointer-events:none;
    }}
    .beko-splash-logo{{height:120px;animation:splashLogo 2.4s cubic-bezier(0.16,1,0.3,1) forwards;filter:drop-shadow(0 8px 32px rgba(37,99,235,0.5));}}
    .beko-splash-ring{{position:absolute;width:200px;height:200px;border:2px solid rgba(37,99,235,0.6);border-radius:50%;animation:splashRing 2.4s ease-out forwards;}}
    .beko-splash-ring:nth-child(2){{animation-delay:0.2s;border-color:rgba(6,182,212,0.4);}}
    .beko-splash-subtitle{{margin-top:24px;color:rgba(147,197,253,0.9);font-size:0.85rem;letter-spacing:6px;text-transform:uppercase;font-weight:600;animation:splashSubtitle 2.4s ease-in-out forwards;animation-delay:0.3s;opacity:0;}}
</style>""", unsafe_allow_html=True)

# ═══ v3.7: Splash ekranı (sayfa açılışında bir kez) ═══
if "splash_shown" not in st.session_state:
    st.session_state.splash_shown = True
    _splash_logo = f'<img src="data:image/png;base64,{logo_b64}" class="beko-splash-logo">' if logo_b64 else '<div style="font-size:5rem;font-weight:900;color:#fff;letter-spacing:6px;animation:splashLogo 2.4s cubic-bezier(0.16,1,0.3,1) forwards;">BEKO</div>'
    st.markdown(f"""<div class="beko-splash">
        <div class="beko-splash-ring"></div>
        <div class="beko-splash-ring"></div>
        {_splash_logo}
        <div class="beko-splash-subtitle">Çerkezköy · Şasi Planlama</div>
    </div>""", unsafe_allow_html=True)

# =====================================================================
# TABLO FONKSİYONLARI  (orijinal, değişmedi)
# =====================================================================

# ═══ v3: Alokasyondan günlük üretime dönüşüm ═══
def alloc_to_daily(alloc_dict, tempo_dict, lines, rates_dict=None):
    """OTD alokasyonunu günlük üretim miktarlarına dönüştürür."""
    nd = len(st.session_state.dyn_dates)
    daily = {c: [0]*nd for c in SUS_CARDS}
    for ln in lines:
        row_data = alloc_dict.get(ln, [""]*nd)
        rows = row_data if (row_data and isinstance(row_data[0], list)) else [row_data]
        rates = rates_dict.get(ln, [1]*nd) if rates_dict else [1]*nd
        for row in rows:
            for i, card in enumerate(row):
                if i < nd and card and card in SUS_CARDS:
                    cap = tempo_dict.get(ln, {}).get(card, 0)
                    rate = rates[i] if i < len(rates) else 1
                    daily[card][i] += int(cap * rate)
    return daily

def compute_manual_impact(old_plan, new_plan):
    """Manuel değişikliklerin etkisini hesaplar."""
    impact = {"changes": [], "summary": {"fixed": 0, "new_violations": 0, "unchanged": 0}}
    for stage, rem_key, label in [("OTD","otd_rem","KSO"),("MD","md_rem","KSM"),("TA","ta_rem","KST")]:
        for c in SUS_CARDS:
            if rem_key == "md_rem" and not PROCESS_MAP.get(c): continue
            old_rem = old_plan[rem_key].get(c, [0]*N_DAYS)
            new_rem = new_plan[rem_key].get(c, [0]*N_DAYS)
            for i in range(N_DAYS):
                ov, nv = old_rem[i], new_rem[i]
                if ov != nv:
                    change = {"card": c, "stage": label, "day": i+1, "date": SUS_DATES[i],
                              "old": ov, "new": nv, "diff": nv - ov}
                    if ov < 0 and nv >= 0:
                        change["status"] = "fixed"
                        impact["summary"]["fixed"] += 1
                    elif ov >= 0 and nv < 0:
                        change["status"] = "new_violation"
                        impact["summary"]["new_violations"] += 1
                    else:
                        change["status"] = "changed"
                        impact["summary"]["unchanged"] += 1
                    impact["changes"].append(change)
    return impact

# ═══ v3.2: Setup Değişikliği Algılama ═══
SETUP_DEFAULT_RATE = 0.50  # Setup değişikliği = %50 verimlilik kaybı

def detect_setup_changes(new_alloc, old_alloc, lines):
    """Alokasyondaki setup değişikliklerini tespit eder.
    Bir gün önceki kart ile o günkü kart farklıysa setup değişikliği var demektir."""
    setups = []
    for ln in lines:
        new_row = new_alloc.get(ln, [""]*N_DAYS)
        old_row = old_alloc.get(ln, [""]*N_DAYS)
        if isinstance(new_row[0], list): new_row = new_row[0]
        if isinstance(old_row[0], list): old_row = old_row[0]
        for i in range(N_DAYS):
            new_card = new_row[i] if i < len(new_row) else ""
            old_card = old_row[i] if i < len(old_row) else ""
            if not new_card:
                continue
            # Önceki gün: aynı hattaki bir önceki günün kartı
            prev_card = new_row[i-1] if i > 0 and (i-1) < len(new_row) else ""
            # Setup = kart değişti ve hücre dolu
            is_setup = prev_card != "" and prev_card != new_card
            # Ayrıca: kullanıcı kartı değiştirdiyse (eski alokasyondan farklı)
            is_user_change = new_card != old_card
            if is_setup or (is_user_change and i == 0 and new_card != old_card):
                setups.append({
                    "line": ln, "day_idx": i, "day": i+1, "date": SUS_DATES[i],
                    "prev_card": prev_card, "new_card": new_card,
                    "old_card": old_card,
                    "suggested_rate": SETUP_DEFAULT_RATE if is_setup else 1.0,
                    "is_user_change": is_user_change,
                    "reason": f"{prev_card}→{new_card} setup" if is_setup else "ilk gün / değişiklik"
                })
    return setups

def make_alloc_rates_combined(alloc_dict, rates_dict, lines, d_idx=None):
    """Alokasyon + oranlar birleşik HTML tablosu."""
    idx = d_idx if d_idx is not None else list(range(N_DAYS))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    for ln in lines:
        rows = alloc_dict.get(ln, [])
        if not rows: continue
        disp = rows if isinstance(rows[0], list) else [rows]
        rates = rates_dict.get(ln, [1]*N_DAYS) if rates_dict else [1]*N_DAYS
        for ri, row in enumerate(disp):
            h += f'<tr><td class="otd-rh">{ln if ri==0 else ""}</td>'
            for i in idx:
                v = row[i] if i < len(row) else ""
                if v:
                    bg = KART_RENKLERI.get(v,"#666")
                    rv = rates[i] if i < len(rates) else 1.0
                    pct = int(rv * 100)
                    if rv < 1.0:
                        bar_w = max(10, pct)
                        rate_html = (f'<div style="margin-top:2px;height:4px;border-radius:2px;background:rgba(0,0,0,0.15);">'
                                     f'<div style="width:{bar_w}%;height:100%;border-radius:2px;background:{"#ef4444" if pct<60 else "#f59e0b"};"></div></div>'
                                     f'<span class="rate-sub" style="color:rgba(0,0,0,0.7);font-weight:800;">%{pct}</span>')
                    else:
                        rate_html = ''
                    h += f'<td style="background:{bg};color:#1e293b;font-weight:700;line-height:1.1;padding:5px 4px;">{v}{rate_html}</td>'
                else:
                    h += '<td class="otd-none">—</td>'
            h += '</tr>'
    h += '</tbody></table>'
    return h

# ═══ TA FİKSTÜR YARDIMCILARI ═══
def fixture_usage_to_ta_daily(fixture_usage, per_cycle):
    """Fikstür kullanım sayısını TA günlük üretimine çevirir.
    ta_daily[c][t] = fikstür_kullanımı[c][t] × adet_per_cycle[c]"""
    nd = len(st.session_state.dyn_dates)
    daily = {}
    for c in SUS_CARDS:
        use = fixture_usage.get(c, [0]*nd)
        rate = per_cycle.get(c, 0)
        daily[c] = [int((use[i] if i < len(use) else 0) * rate) for i in range(nd)]
    return daily

def detect_fixture_violations(usage_dict, fcount_dict):
    """2× fikstür sayısı kısıtını aşan günleri tespit eder."""
    viols = []
    for c in SUS_CARDS:
        cap = 2 * fcount_dict.get(c, 0)
        use = usage_dict.get(c, [])
        for i, v in enumerate(use):
            if v > cap:
                viols.append({"card": c, "day": i+1, "date": SUS_DATES[i] if i < len(SUS_DATES) else f"G{i+1}",
                              "used": v, "cap": cap, "excess": v - cap})
    return viols

def make_fixture_grid(usage_dict, fcount_dict, d_idx=None, editable_ref=None):
    """TA fikstür kullanım tablosu — limit aşımları kırmızı, fikstür sayısı kolonunda."""
    idx = d_idx if d_idx is not None else list(range(N_DAYS))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Kart</th><th>Fix.×2</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    for c in SUS_CARDS:
        bg = KART_RENKLERI.get(c, "#888")
        cap = 2 * fcount_dict.get(c, 0)
        h += f'<tr><td class="otd-rh" style="background:{bg};color:#1e293b;font-weight:800;">{c}</td>'
        h += f'<td style="text-align:center;color:#93c5fd;font-weight:700;">{fcount_dict.get(c,0)}×2={cap}</td>'
        use = usage_dict.get(c, [0]*N_DAYS)
        for i in idx:
            v = use[i] if i < len(use) else 0
            if v == 0:
                h += '<td class="otd-none">—</td>'
            elif v > cap:
                h += f'<td style="background:rgba(239,68,68,0.35);color:#fff;font-weight:800;">{v}⚠</td>'
            elif v == cap:
                h += f'<td style="background:rgba(245,158,11,0.25);color:#fbbf24;font-weight:700;">{v}</td>'
            else:
                h += f'<td style="color:#e2e8f0;">{v}</td>'
        h += '</tr>'
    h += '</tbody></table>'
    return h

def make_grid(card_data, init_key=None, d_idx=None):
    idx = d_idx if d_idx is not None else list(range(N_DAYS))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Kart</th>'
    if init_key: h += '<th>Stok₀</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    tot = [0]*len(idx)
    for c in SUS_CARDS:
        vals = card_data.get(c, [0]*N_DAYS)
        bg = KART_RENKLERI.get(c,"#888")
        h += f'<tr><td style="background:{bg};color:#1e293b;font-weight:700;text-align:left;padding-left:8px;border-radius:6px;">{c}</td>'
        if init_key:
            iv = sus["init"].get(c,{}).get(init_key,0)
            h += f'<td style="color:#93c5fd;font-weight:600;">{iv:,}</td>'
        for ji, i in enumerate(idx):
            v = vals[i] if i < len(vals) else 0
            tot[ji] += v
            if v < 0: h += f'<td style="background:rgba(239,68,68,0.25);color:#ef4444;font-weight:700;">{v:,}</td>'
            elif v == 0: h += '<td style="color:#475569;">—</td>'
            else: h += f'<td style="color:#fff;">{v:,}</td>'
        h += '</tr>'
    h += '<tr style="border-top:2px solid rgba(37,99,235,0.4);"><td class="otd-rh">TOPLAM</td>'
    if init_key: h += '<td></td>'
    for t in tot: h += f'<td style="color:#93c5fd;font-weight:800;">{t:,}</td>'
    h += '</tr></tbody></table>'
    return h

def make_grid_plan(card_data, ref_data=None, init_key=None, init_src=None, d_idx=None):
    """make_grid'in gelişmiş versiyonu: referanstan farklı hücreleri vurgular."""
    idx = d_idx if d_idx is not None else list(range(N_DAYS))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Kart</th>'
    if init_key: h += '<th>Stok₀</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    tot = [0]*len(idx)
    for c in SUS_CARDS:
        vals = card_data.get(c, [0]*N_DAYS)
        ref_vals = ref_data.get(c, [0]*N_DAYS) if ref_data else None
        bg = KART_RENKLERI.get(c,"#888")
        h += f'<tr><td style="background:{bg};color:#1e293b;font-weight:700;text-align:left;padding-left:8px;border-radius:6px;">{c}</td>'
        if init_key:
            iv = (init_src or sus)["init"].get(c,{}).get(init_key,0)
            h += f'<td style="color:#93c5fd;font-weight:600;">{iv:,}</td>'
        for ji, i in enumerate(idx):
            v = vals[i] if i < len(vals) else 0
            tot[ji] += v
            rv = ref_vals[i] if ref_vals and i < len(ref_vals) else None
            diff = rv is not None and v != rv
            outline = "outline:2px solid #22c55e;outline-offset:-2px;" if diff else ""
            if v < 0:
                h += f'<td style="background:rgba(239,68,68,0.25);color:#ef4444;font-weight:700;{outline}">{v:,}</td>'
            elif v == 0:
                h += f'<td style="color:#475569;{outline}">—</td>'
            else:
                h += f'<td style="color:#fff;{outline}">{v:,}</td>'
        h += '</tr>'
    h += '<tr style="border-top:2px solid rgba(37,99,235,0.4);"><td class="otd-rh">TOPLAM</td>'
    if init_key: h += '<td></td>'
    for t in tot: h += f'<td style="color:#93c5fd;font-weight:800;">{t:,}</td>'
    h += '</tr></tbody></table>'
    return h

def make_alloc(alloc_dict, lines, d_idx=None, rates_dict=None):
    idx = d_idx if d_idx is not None else list(range(N_DAYS))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    for ln in lines:
        rows = alloc_dict.get(ln, [])
        if not rows: continue
        disp = rows if isinstance(rows[0], list) else [rows]
        rates_all = rates_dict.get(ln, None) if rates_dict else None
        rates_is_multi = bool(rates_all) and bool(rates_all) and isinstance(rates_all[0], list)
        for ri, row in enumerate(disp):
            if rates_is_multi:
                rates = rates_all[ri] if ri < len(rates_all) else [1.0]*N_DAYS
            else:
                rates = rates_all
            row_label = ln if ri == 0 else ""
            if len(disp) > 1:
                row_label = f"{ln}-{ri+1}"
            h += f'<tr><td class="otd-rh">{row_label}</td>'
            for i in idx:
                v = row[i] if i < len(row) else ""
                if v:
                    bg = KART_RENKLERI.get(v,"#666")
                    rate_val = rates[i] if rates and i < len(rates) else 1.0
                    rate_html = ""
                    if rates and rate_val < 1.0:
                        pct = int(rate_val * 100)
                        rate_html = f'<span class="rate-sub" style="color:rgba(0,0,0,0.6);">%{pct}</span>'
                    elif rates and rate_val == 1.0:
                        rate_html = f'<span class="rate-sub" style="color:rgba(0,0,0,0.35);">%100</span>'
                    h += f'<td style="background:{bg};color:#1e293b;font-weight:700;line-height:1.15;">{v}{rate_html}</td>'
                else: h += '<td class="otd-none">—</td>'
            h += '</tr>'
    h += '</tbody></table>'
    return h

def make_alloc_compare(alloc_new, alloc_ref, lines, d_idx=None, rates_dict=None):
    """İki alokasyon karşılaştırır; farklı hücreleri yeşil çerçeve ile işaretler."""
    idx = d_idx if d_idx is not None else list(range(N_DAYS))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    for ln in lines:
        rows_new = alloc_new.get(ln, [])
        rows_ref = alloc_ref.get(ln, [])
        if not rows_new: continue
        disp_new = rows_new if isinstance(rows_new[0], list) else [rows_new]
        disp_ref = rows_ref if (rows_ref and isinstance(rows_ref[0], list)) else [rows_ref] if rows_ref else [[""] * 14]
        rates = rates_dict.get(ln, [1]*N_DAYS) if rates_dict else None
        for ri, row in enumerate(disp_new):
            ref_row = disp_ref[ri] if ri < len(disp_ref) else [""] * 14
            h += f'<tr><td class="otd-rh">{ln if ri==0 else ""}</td>'
            for i in idx:
                v = row[i] if i < len(row) else ""
                ref_v = ref_row[i] if i < len(ref_row) else ""
                diff = v != ref_v
                outline = "outline:2px solid #22c55e;outline-offset:-2px;" if diff else ""
                if v:
                    bg = KART_RENKLERI.get(v,"#666")
                    rate_val = rates[i] if rates and i < len(rates) else 1.0
                    rate_html = ""
                    if rates and rate_val < 1.0:
                        pct = int(rate_val * 100)
                        rate_html = f'<span class="rate-sub" style="color:rgba(0,0,0,0.6);">%{pct}</span>'
                    h += f'<td style="background:{bg};color:#1e293b;font-weight:700;line-height:1.15;{outline}">{v}{rate_html}</td>'
                else:
                    h += f'<td class="otd-none" style="{outline}">—</td>'
            h += '</tr>'
    h += '</tbody></table>'
    return h

def make_rates_table(rates_dict, alloc_dict, lines, d_idx=None):
    """Verimlilik oranları tablosu — alokasyondaki kart rengini arka plan olarak kullanır.
    Multi-row destekli: rates_dict[ln] hem flat liste hem list-of-list olabilir."""
    idx = d_idx if d_idx is not None else list(range(N_DAYS))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    for ln in lines:
        rates_all = rates_dict.get(ln, [1]*N_DAYS)
        alloc_raw = alloc_dict.get(ln, [""]*N_DAYS)
        rates_is_multi = bool(rates_all) and isinstance(rates_all[0], list)
        alloc_is_multi = bool(alloc_raw) and isinstance(alloc_raw[0], list)
        if rates_is_multi or alloc_is_multi:
            rates_rows = rates_all if rates_is_multi else [rates_all]
            alloc_rows = alloc_raw if alloc_is_multi else [alloc_raw]
            # En çok satıra göre genişlet
            n_rows = max(len(rates_rows), len(alloc_rows))
        else:
            rates_rows = [rates_all]
            alloc_rows = [alloc_raw]
            n_rows = 1
        for ri in range(n_rows):
            rates = rates_rows[ri] if ri < len(rates_rows) else [1.0]*N_DAYS
            alloc_row = alloc_rows[ri] if ri < len(alloc_rows) else [""]*N_DAYS
            row_label = ln if n_rows == 1 else f"{ln}-{ri+1}"
            h += f'<tr><td class="otd-rh">{row_label}</td>'
            for i in idx:
                rv = rates[i] if i < len(rates) else 1.0
                card = alloc_row[i] if i < len(alloc_row) else ""
                pct = int(rv * 100)
                if not card:
                    h += '<td class="otd-none">—</td>'
                elif rv < 1.0:
                    bg = KART_RENKLERI.get(card, "#666")
                    h += f'<td style="background:{bg};color:#1e293b;font-weight:800;font-size:0.82rem;">%{pct}</td>'
                else:
                    h += f'<td style="background:rgba(255,255,255,0.06);color:#64748b;font-weight:500;">%{pct}</td>'
            h += '</tr>'
    h += '</tbody></table>'
    return h

# =====================================================================
# LOGO & BAŞLIK — Yeni yapı: sekmeler önce, marka şeridi sonra (aşağıda)
# =====================================================================

# =====================================================================
# SIDEBAR  — v3.3 Beko Branded Design
# =====================================================================
# ── Beko Brand Header ──
_sb_logo = f'<img src="data:image/png;base64,{logo_b64}">' if logo_b64 else '<div style="font-size:1.8rem;font-weight:900;color:#fff;letter-spacing:2px;">BEKO</div>'
st.sidebar.markdown('<div class="sb-top-accent"></div>', unsafe_allow_html=True)
st.sidebar.markdown(f"""<div class="sb-brand">
    {_sb_logo}
    <p class="sb-brand-title">Çerkezköy Elektronik</p>
    <p class="sb-brand-sub">Şasi Üretim Planlama Sistemi</p>
</div>""", unsafe_allow_html=True)

# ── Kart Filtresi ──
st.sidebar.markdown('<div class="sb-section"><p class="sb-section-title">🎯 Kart Filtresi</p></div>', unsafe_allow_html=True)
kart_sec = ["Tümü"] + sorted(SUS_CARDS)
secili = st.sidebar.selectbox("Kart:", kart_sec, label_visibility="collapsed")
hl = None if secili == "Tümü" else secili
if hl:
    r = KART_RENKLERI.get(hl,"#fff")
    needs_md = PROCESS_MAP.get(hl, False)
    md_text = "OTD → MD → TA" if needs_md else "OTD → TA (MD atlar)"
    st.sidebar.markdown(f"""<div style="background:{r};color:#1e293b;padding:10px 14px;border-radius:10px;text-align:center;margin-top:6px;">
        <div style="font-weight:800;font-size:1.2rem;">{hl}</div>
        <div style="font-size:0.68rem;opacity:0.7;margin-top:2px;">{md_text}</div>
    </div>""", unsafe_allow_html=True)

# ── Tarih Aralığı ──
st.sidebar.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sb-section"><p class="sb-section-title">📅 Tarih Aralığı</p></div>', unsafe_allow_html=True)
_date_labels = [f"{SUS_DAYS[i]} {SUS_DATES[i]}" for i in range(N_DAYS)]
_d_start, _d_end = st.sidebar.select_slider(
    "Görüntülenecek tarih aralığı:",
    options=list(range(N_DAYS)),
    value=(st.session_state.date_start_idx, st.session_state.date_end_idx),
    format_func=lambda x: _date_labels[x],
    key="date_slider"
)
st.session_state.date_start_idx = _d_start
st.session_state.date_end_idx   = _d_end
DATE_INDICES = list(range(_d_start, _d_end + 1))
st.sidebar.caption(f"{len(DATE_INDICES)} / {N_DAYS} gün · {SUS_DATES[_d_start]} — {SUS_DATES[_d_end]}")

# ── Ufku Uzat (sicil onaylı + kalıcı) ──
st.sidebar.markdown('<div class="sb-section"><p class="sb-section-title">📐 Planlama Ufku</p></div>', unsafe_allow_html=True)
st.sidebar.caption(f"Mevcut: {N_DAYS} gün ({SUS_DATES[0]} — {SUS_DATES[-1]})")
_ext_cols = st.sidebar.columns(4)
with _ext_cols[0]:
    if st.button("+1 Gün", use_container_width=True, key="ext_1d"):
        st.session_state.pending_horizon = 1; st.rerun()
with _ext_cols[1]:
    if st.button("+1 Hafta", use_container_width=True, key="ext_1w"):
        st.session_state.pending_horizon = 6; st.rerun()
with _ext_cols[2]:
    if st.button("+1 Ay", use_container_width=True, key="ext_1m"):
        st.session_state.pending_horizon = 26; st.rerun()
with _ext_cols[3]:
    if st.button("+1 Yıl", use_container_width=True, key="ext_1y"):
        st.session_state.pending_horizon = 313; st.rerun()

# Sıfırla butonu
if N_DAYS > len(_DEFAULT_DATES):
    if st.sidebar.button("🔄 Varsayılana Sıfırla (14 gün)", use_container_width=True, key="ext_reset"):
        st.session_state.pending_horizon = -1; st.rerun()

# Sicil onayı paneli
if st.session_state.pending_horizon != 0:
    ph = st.session_state.pending_horizon
    if ph > 0:
        ph_label = f"+{ph} gün eklenecek"
    else:
        ph_label = "Varsayılana (14 gün) sıfırlanacak"
    st.sidebar.markdown(f"""<div style="background:rgba(245,158,11,0.15);border:1px solid rgba(245,158,11,0.4);border-radius:8px;padding:10px 12px;margin-top:8px;">
        <div style="color:#fbbf24;font-weight:700;font-size:0.82rem;">⏳ Onay Bekleniyor</div>
        <div style="color:#cbd5e1;font-size:0.78rem;margin-top:3px;">{ph_label}</div>
        <div style="color:#94a3b8;font-size:0.72rem;margin-top:2px;">Değişiklik kalıcı olacak (F5 sonrası korunur).</div>
    </div>""", unsafe_allow_html=True)
    if st.session_state.auth:
        cap1, cap2 = st.sidebar.columns(2)
        with cap1:
            if st.button("✅ Uygula", type="primary", use_container_width=True, key="ph_apply_authed"):
                if ph == -1:
                    # Sıfırla
                    st.session_state.dyn_dates = list(_DEFAULT_DATES)
                    st.session_state.dyn_days  = list(_DEFAULT_DAYS)
                    # SUS arrays'leri 14'e kırp
                    nd = len(_DEFAULT_DATES)
                    for key in ["otd_daily","otd_rem","md_daily","md_rem","ta_daily","ta_rem","assembly","ta_fixture_usage"]:
                        for c in SUS_CARDS:
                            arr = st.session_state.sus.get(key, {}).get(c, [])
                            if len(arr) > nd: st.session_state.sus[key][c] = arr[:nd]
                    for ln in st.session_state.sus.get("otd_alloc", {}):
                        arr = st.session_state.sus["otd_alloc"][ln]
                        if isinstance(arr[0], list):
                            for row in arr:
                                if len(row) > nd: row[:] = row[:nd]
                        elif len(arr) > nd:
                            st.session_state.sus["otd_alloc"][ln] = arr[:nd]
                    for ln in st.session_state.sus.get("md_alloc", {}):
                        for row in st.session_state.sus["md_alloc"][ln]:
                            if isinstance(row, list) and len(row) > nd: row[:] = row[:nd]
                    for ln in st.session_state.sus.get("otd_rates", {}):
                        arr = st.session_state.sus["otd_rates"][ln]
                        if len(arr) > nd: st.session_state.sus["otd_rates"][ln] = arr[:nd]
                    for ln in st.session_state.sus.get("md_rates", {}):
                        for row in st.session_state.sus["md_rates"][ln]:
                            if isinstance(row, list) and len(row) > nd: row[:] = row[:nd]
                    st.session_state.sus = recalc_stocks(st.session_state.sus)
                    st.session_state.date_end_idx = nd - 1
                else:
                    extend_horizon(ph)
                    st.session_state.date_end_idx = len(st.session_state.dyn_dates) - 1
                _persist_horizon_to_qp()
                st.session_state.pending_horizon = 0
                st.success(f"✅ Ufku güncellendi (Sicil: {st.session_state.auth_sicil})")
                st.rerun()
        with cap2:
            if st.button("✗ Vazgeç", use_container_width=True, key="ph_cancel_authed"):
                st.session_state.pending_horizon = 0; st.rerun()
    else:
        _ph_sicil = st.sidebar.text_input("Sicil:", type="password", placeholder="Sicil numaranız", key="ph_sicil_input", label_visibility="collapsed")
        cap1, cap2 = st.sidebar.columns(2)
        with cap1:
            if st.button("🔓 Doğrula & Uygula", type="primary", use_container_width=True, key="ph_sicil_apply"):
                if _ph_sicil.strip() in YETKILI_SICILLER:
                    st.session_state.auth = True
                    st.session_state.auth_sicil = _ph_sicil.strip()
                    if ph == -1:
                        st.session_state.dyn_dates = list(_DEFAULT_DATES)
                        st.session_state.dyn_days  = list(_DEFAULT_DAYS)
                        nd = len(_DEFAULT_DATES)
                        for key in ["otd_daily","otd_rem","md_daily","md_rem","ta_daily","ta_rem","assembly","ta_fixture_usage"]:
                            for c in SUS_CARDS:
                                arr = st.session_state.sus.get(key, {}).get(c, [])
                                if len(arr) > nd: st.session_state.sus[key][c] = arr[:nd]
                        for ln in st.session_state.sus.get("otd_alloc", {}):
                            arr = st.session_state.sus["otd_alloc"][ln]
                            if isinstance(arr[0], list):
                                for row in arr:
                                    if len(row) > nd: row[:] = row[:nd]
                            elif len(arr) > nd:
                                st.session_state.sus["otd_alloc"][ln] = arr[:nd]
                        for ln in st.session_state.sus.get("md_alloc", {}):
                            for row in st.session_state.sus["md_alloc"][ln]:
                                if isinstance(row, list) and len(row) > nd: row[:] = row[:nd]
                        for ln in st.session_state.sus.get("otd_rates", {}):
                            arr = st.session_state.sus["otd_rates"][ln]
                            if len(arr) > nd: st.session_state.sus["otd_rates"][ln] = arr[:nd]
                        for ln in st.session_state.sus.get("md_rates", {}):
                            for row in st.session_state.sus["md_rates"][ln]:
                                if isinstance(row, list) and len(row) > nd: row[:] = row[:nd]
                        st.session_state.sus = recalc_stocks(st.session_state.sus)
                        st.session_state.date_end_idx = nd - 1
                    else:
                        extend_horizon(ph)
                        st.session_state.date_end_idx = len(st.session_state.dyn_dates) - 1
                    _persist_horizon_to_qp()
                    st.session_state.pending_horizon = 0
                    st.success(f"✅ Yetkilendirildi & uygulandı (Sicil: {_ph_sicil.strip()})")
                    st.rerun()
                else:
                    st.error("❌ Yetkisiz sicil.")
        with cap2:
            if st.button("✗ Vazgeç", use_container_width=True, key="ph_sicil_cancel"):
                st.session_state.pending_horizon = 0; st.rerun()

# ── Plan Durum Özeti ──
st.sidebar.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sb-section"><p class="sb-section-title">📊 Plan Durumu</p></div>', unsafe_allow_html=True)
_v_otd = sum(1 for c in SUS_CARDS for v in sus["otd_rem"].get(c,[]) if v<0)
_v_md  = sum(1 for c in SUS_CARDS for v in sus["md_rem"].get(c,[]) if v<0)
_v_ta  = sum(1 for c in SUS_CARDS for v in sus["ta_rem"].get(c,[]) if v<0)
_v_all = _v_otd + _v_md + _v_ta

# ═══ v3.8: İhlal Detay Modal Fonksiyonları ═══
def _render_violation_details(stage_code, rem_key, stage_full, stage_short, next_stage, color):
    """Belirli bir aşama için ihlal detaylarını gösterir."""
    s = st.session_state.sus
    st.markdown(f"""<div style="background:linear-gradient(135deg,{color}22,{color}11);border-left:4px solid {color};padding:14px 18px;border-radius:10px;margin-bottom:16px;">
        <div style="color:{color};font-size:1.05rem;font-weight:800;letter-spacing:0.5px;">{stage_short} — {stage_full}</div>
        <div style="color:#cbd5e1;font-size:0.85rem;margin-top:4px;">{stage_short} = "Kalan Stok {stage_code}". Bir günün sonunda {stage_full} aşamasında biriken stok miktarıdır. <strong style="color:#ef4444;">Negatif değer</strong>, o gün sonunda <strong>{next_stage}</strong> aşamasına yeterli üretim aktarılamadığını gösterir — yani montaj hattı duraklayabilir.</div>
    </div>""", unsafe_allow_html=True)

    viols = []
    for c in SUS_CARDS:
        if rem_key == "md_rem" and not PROCESS_MAP.get(c): continue
        rem = s[rem_key].get(c, [])
        prev_v = None
        for i, v in enumerate(rem):
            if v < 0:
                # Hat bulma (sadece OTD/MD için anlamlı)
                hat = "—"
                if rem_key == "otd_rem":
                    hat = next((ln for ln in ["OD0","OD2","OD3","OD4","OD6"]
                                if i < len(s["otd_alloc"].get(ln, []))
                                and s["otd_alloc"][ln][i] == c), "—")
                # Açık miktarı artıyor mu (kötüye gidiyor mu)
                trend = "→"
                if prev_v is not None:
                    if v < prev_v: trend = "↓ Kötüleşiyor"
                    elif v > prev_v: trend = "↑ İyileşiyor"
                viols.append({
                    "Kart": c,
                    "Gün": i+1,
                    "Tarih": SUS_DATES[i] if i < len(SUS_DATES) else f"G{i+1}",
                    "Hat": hat,
                    "Açık": f"{v:,}",
                    "Trend": trend if i > 0 else "İlk gün"
                })
                prev_v = v
            else:
                prev_v = v

    if not viols:
        st.success(f"✅ {stage_short} aşamasında hiç ihlal yok — tampon stoklar pozitif.")
        return

    # KPI özetler
    k1, k2, k3 = st.columns(3)
    with k1: st.metric("Toplam İhlal", f"{len(viols)} gün×kart")
    with k2: st.metric("Etkilenen Kart", f"{len(set(v['Kart'] for v in viols))}")
    worst_card = max(set(v["Kart"] for v in viols), key=lambda c: sum(1 for v in viols if v["Kart"]==c))
    with k3: st.metric("En Çok Etkilenen", worst_card)

    # Detaylı tablo
    st.markdown("**📋 İhlal Listesi (gün × kart):**")
    df_v = pd.DataFrame(viols)
    st.dataframe(df_v, use_container_width=True, hide_index=True, height=min(420, 40+35*len(df_v)))

    # Kart bazında özet
    st.markdown("**📊 Kart Bazında Toplam Açık:**")
    by_card = {}
    for v in viols:
        c = v["Kart"]
        # Açık string'den int'e çevir
        amt = int(v["Açık"].replace(",", ""))
        by_card[c] = by_card.get(c, 0) + amt
    by_card_df = pd.DataFrame([{"Kart":c, "Toplam Açık":a, "İhlal Günü":sum(1 for v in viols if v["Kart"]==c)} for c, a in sorted(by_card.items(), key=lambda x:x[1])])
    st.dataframe(by_card_df, use_container_width=True, hide_index=True)

    # Ne yapılmalı?
    st.markdown("**💡 Çözüm Önerileri:**")
    suggestions = []
    for c in sorted(by_card.keys(), key=lambda x: by_card[x])[:3]:  # en kötü 3 kart
        amt = abs(by_card[c])
        if stage_code == "OTD":
            suggestions.append(f"• **{c}**: OTD hatlarında ek mesai/hat tahsisi ile {amt:,} adet ek üretim gerekli.")
        elif stage_code == "MD":
            suggestions.append(f"• **{c}**: MD hattında setup süresini azaltarak veya ek vardiya ile {amt:,} adet üretim eklenebilir.")
        else:
            suggestions.append(f"• **{c}**: TA fikstürünün kapasitesi artırılmalı veya farklı fikstüre yönlendirilmeli — {amt:,} adet açık.")
    for sg in suggestions:
        st.markdown(sg)
    st.caption("💬 Detaylı optimize önerileri için ana sayfadaki 'Optimize Et' sekmesini kullanın.")

@st.dialog("KSO — Otomatik Dizgi Sonrası Tampon Stok", width="large")
def show_kso_dialog():
    _render_violation_details("OTD", "otd_rem", "Otomatik Dizgi → Manuel Dizgi geçişi", "KSO", "Manuel Dizgi (MD)", "#ef4444")

@st.dialog("KSM — Manuel Dizgi Sonrası Tampon Stok", width="large")
def show_ksm_dialog():
    _render_violation_details("MD", "md_rem", "Manuel Dizgi → Test & Ayar geçişi", "KSM", "Test & Ayar (TA)", "#3b82f6")

@st.dialog("KST — Test & Ayar Sonrası Tampon Stok", width="large")
def show_kst_dialog():
    _render_violation_details("TA", "ta_rem", "Test & Ayar → Son Montaj geçişi", "KST", "Son Montaj", "#a855f7")

# Tıklanabilir ihlal kartları
st.sidebar.markdown('<div class="sb-stat-buttons">', unsafe_allow_html=True)
_kso_label = f"KSO İhlal   ·   {_v_otd}" if _v_otd else "KSO İhlal   ·   ✓"
_ksm_label = f"KSM İhlal   ·   {_v_md}" if _v_md else "KSM İhlal   ·   ✓"
_kst_label = f"KST İhlal   ·   {_v_ta}" if _v_ta else "KST İhlal   ·   ✓"
if st.sidebar.button(_kso_label, key="btn_kso_dlg", use_container_width=True,
                     type=("primary" if _v_otd else "secondary")):
    show_kso_dialog()
if st.sidebar.button(_ksm_label, key="btn_ksm_dlg", use_container_width=True,
                     type=("primary" if _v_md else "secondary")):
    show_ksm_dialog()
if st.sidebar.button(_kst_label, key="btn_kst_dlg", use_container_width=True,
                     type=("primary" if _v_ta else "secondary")):
    show_kst_dialog()
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Toplam özet kartı (tıklanabilir değil, sadece görsel)
_stat_cls = "sb-stat-val" if _v_all == 0 else "sb-stat-val sb-stat-bad"
st.sidebar.markdown(f"""
<div class="sb-stat" style="margin-top:8px;border:1px solid {'rgba(239,68,68,0.3)' if _v_all else 'rgba(34,197,94,0.3)'};background:{'rgba(239,68,68,0.06)' if _v_all else 'rgba(34,197,94,0.06)'};">
    <span class="sb-stat-label" style="font-weight:600;">Toplam</span>
    <span class="{_stat_cls}" style="font-size:1rem;">{'⚠️ ' + str(_v_all) + ' ihlal' if _v_all else '✅ Fizibil'}</span>
</div>
""", unsafe_allow_html=True)

# ── Oturum Bilgisi ──
if st.session_state.auth:
    st.sidebar.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown(f"""<div style="padding:8px 12px;border-radius:8px;background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">
        <div style="font-size:0.68rem;color:#22c55e;font-weight:600;">🔓 Oturum Açık</div>
        <div style="font-size:0.78rem;color:#93c5fd;margin-top:2px;">Sicil: {st.session_state.auth_sicil}</div>
    </div>""", unsafe_allow_html=True)

# =====================================================================
# SEKMELER (sayfa başına taşındı, emojiler kaldırıldı)
# =====================================================================
# ── Üst marka banner'ı (sol hizalı, estetik) ──
_lh_big = f'<img src="data:image/png;base64,{logo_b64}" style="height:46px;margin-right:18px;filter:drop-shadow(0 3px 10px rgba(37,99,235,0.5));">' if logo_b64 else ""
st.markdown(f"""<div style="display:flex;align-items:center;justify-content:flex-start;gap:6px;margin:0 0 18px;padding:18px 28px;background:linear-gradient(135deg,rgba(2,10,31,0.92) 0%,rgba(8,24,58,0.88) 35%,rgba(15,40,90,0.80) 100%);border-radius:14px;backdrop-filter:blur(14px);border:1px solid rgba(147,197,253,0.18);box-shadow:0 4px 28px rgba(0,0,0,0.4),inset 0 1px 0 rgba(147,197,253,0.08);position:relative;overflow:hidden;">
    <div style="position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,#3b82f6,#1d4ed8);border-radius:14px 0 0 14px;"></div>
    {_lh_big}
    <div style="text-align:left;flex-grow:1;">
        <div style="color:#fff;font-size:1.55rem;font-weight:800;letter-spacing:0.5px;line-height:1.1;text-shadow:0 2px 8px rgba(0,0,0,0.4);">Çerkezköy Elektronik</div>
        <div style="color:#93c5fd;font-size:0.78rem;letter-spacing:3px;text-transform:uppercase;font-weight:600;margin-top:6px;">Şasi → Montaj Planlama Sistemi</div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
        <div style="color:#94a3b8;font-size:0.7rem;letter-spacing:1.5px;text-transform:uppercase;font-weight:600;">Karar Destek Sistemi</div>
        <div style="display:flex;gap:6px;">
            <div style="width:6px;height:6px;border-radius:50%;background:#22c55e;box-shadow:0 0 8px rgba(34,197,94,0.6);"></div>
            <span style="color:#86efac;font-size:0.7rem;font-weight:600;">Aktif</span>
        </div>
    </div>
</div>""", unsafe_allow_html=True)

tab_panel, tab_montaj, tab_opt, tab_rapor, tab_veri = st.tabs(
    ["Kontrol Paneli & Üretim Planı", "Montaj Planı", "Optimize Et", "Rapor & Geçişler", "Veri Yönetimi"]
)


# =============  TAB 1: KONTROL PANELİ + ÜRETİM PLANI  =================
with tab_panel:
    # ── KPI Metrikleri (orijinal) ──
    viol_otd = sum(1 for c in SUS_CARDS for v in sus["otd_rem"].get(c,[]) if v<0)
    viol_md  = sum(1 for c in SUS_CARDS for v in sus["md_rem"].get(c,[]) if v<0)
    viol_ta  = sum(1 for c in SUS_CARDS for v in sus["ta_rem"].get(c,[]) if v<0)
    viol_all = viol_otd + viol_md + viol_ta
    total_otd = sum(sum(v) for v in sus["otd_daily"].values())
    total_md  = sum(sum(v) for v in sus["md_daily"].values())
    total_ta  = sum(sum(v) for v in sus["ta_daily"].values())
    total_asm = sum(sum(v) for v in sus["assembly"].values())

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("OTD Üretim", f"{total_otd:,}")
    with c2: st.metric("MD Üretim",  f"{total_md:,}")
    with c3: st.metric("TA Üretim",  f"{total_ta:,}")
    with c4: st.metric("Montaj Talebi", f"{total_asm:,}")
    with c5:
        if viol_all == 0: st.metric("Durum", "FİZİBİL ✅")
        else: st.metric("Stok İhlali", f"{viol_all} gün×kart", delta=f"KSO:{viol_otd} KSM:{viol_md} KST:{viol_ta}", delta_color="inverse")
    st.write("---")

    # ── YENİ: Tümünü Optimize Et + Durum Rozetleri ──
    tb1, tb2 = st.columns([2, 8])
    with tb1:
        if st.button("🚀  Tümünü Optimize Et", type="primary", use_container_width=True, key="tum_opt_btn"):
            with st.spinner("Tüm aşamalar analiz ediliyor ve optimize ediliyor…"):
                result = run_optimization(sus)
                if result["proposals"]:
                    applied = copy.deepcopy(sus)
                    for p in result["proposals"]:
                        c_k, d_k = p["card"], p["day"]-1
                        if p["type"].startswith("OTD"):
                            applied["otd_daily"][c_k][d_k] = p["new"]
                            if p.get("line"):
                                al = applied["otd_alloc"].get(p["line"], [""]*N_DAYS)
                                if d_k < len(al): al[d_k] = c_k
                        elif p["type"].startswith("MD"):
                            applied["md_daily"][c_k][d_k] = p["new"]
                    applied = recalc_stocks(applied)
                    st.session_state.sus = applied
                    st.session_state.otd_opt_res = None
                    st.session_state.md_opt_res  = None
                    st.session_state.ta_opt_res  = None
                    st.session_state.preview_active = False
                    st.session_state.preview_alloc = None
                    st.success(f"✅ {len(result['proposals'])} değişiklik uygulandı. Stoklar yeniden hesaplandı.")
                    st.rerun()
                else:
                    st.success(result["message"])
    with tb2:
        def _rozet(opt_res_key, label):
            r = st.session_state.get(opt_res_key)
            if r is None:
                return f'<span class="rozet-ref">📋 {label}: Referans</span>'
            if r["status"] == "feasible":
                return f'<span class="rozet-opt">✅ {label}: Optimize Hazır</span>'
            return f'<span class="rozet-partial">⚠️ {label}: Kısmi Optimize</span>'
        st.markdown(
            f'{_rozet("otd_opt_res","OTD")} &nbsp; {_rozet("md_opt_res","MD")} &nbsp; {_rozet("ta_opt_res","TA")}',
            unsafe_allow_html=True
        )
    st.write("---")

    # ==================================================================
    # OTD EXPANDER
    # ==================================================================
    with st.expander("⚡ OTD — Otomatik Dizgi (Hat Alokasyonu & Üretim & Stok)", expanded=False):

        # ── Kontrol satırı ──
        hc1, hc2, hc3, hc4 = st.columns([3, 1, 2, 2])
        with hc1:
            rozet_html = _rozet("otd_opt_res", "OTD")
            st.markdown(rozet_html, unsafe_allow_html=True)
        with hc2:
            # Upload butonu — dosya seçici
            up_otd = st.file_uploader(
                "📤", type=["json","csv","xlsx"], key="up_otd_exp",
                label_visibility="collapsed",
                help="JSON: {otd_alloc:{...}, otd_daily:{...}}  |  CSV: Kart,07.05,...,23.05"
            )
            pf_otd = process_upload_file(up_otd, "last_otd_up")
            if pf_otd is not None:
                ext = pf_otd.name.rsplit(".", 1)[-1].lower()
                parsed, err = (parse_upload_json(pf_otd) if ext == "json"
                               else parse_upload_csv(pf_otd, "otd_daily"))
                if err:
                    st.error(f"Okuma hatası: {err}")
                else:
                    updated = [k for k in ("otd_alloc","otd_daily","otd_rates") if k in parsed]
                    if updated:
                        for k in updated: st.session_state.sus[k] = parsed[k]
                        st.session_state.sus = recalc_stocks(st.session_state.sus)
                        st.session_state.otd_opt_res = None
                        st.session_state.preview_active = False
                        st.session_state.preview_alloc = None
                        st.success(f"✅ OTD verisi güncellendi: {', '.join(updated)}")
                        st.rerun()
                    else:
                        st.error("Geçerli OTD anahtarı bulunamadı.")
        with hc3:
            st.markdown(
                '<div style="font-size:0.72rem;color:#64748b;padding-top:6px;">'
                'JSON: <code>otd_alloc</code>, <code>otd_daily</code><br>'
                'CSV: Kart, 07.05 … 23.05</div>',
                unsafe_allow_html=True
            )
        with hc4:
            if st.button("⚡  OTD'yi Optimize Et", type="primary",
                         use_container_width=True, key="btn_otd_exp"):
                with st.spinner("OTD analiz ve optimize ediliyor…"):
                    st.session_state.otd_opt_res = run_stage_opt(sus, "OTD")
                st.rerun()

        # ── İçerik: referans tek görünüm VEYA öncesi/sonrası ──
        otd_res = st.session_state.otd_opt_res

        if otd_res is None:
            # ═══ v3: Referans / Manuel Düzenleme modları ═══
            _ref_tab, _edit_tab = st.tabs(["📋 Görüntüle", "✏️ Manuel Düzenle"])

            with _ref_tab:
                # Referans plan (optimize edilmemiş) — orijinal davranış
                st.markdown("**Hat – Kart Alokasyonu**")
                st.markdown(make_alloc(sus["otd_alloc"], ["OD0","OD2","OD3","OD4","OD6"], d_idx=DATE_INDICES, rates_dict=sus.get("otd_rates",{})), unsafe_allow_html=True)
                # ═══ v3.1: Oranlar ayrı tablo — varsayılan kapalı ═══
                with st.expander("📊 Verimlilik Oranları (OTD)", expanded=False):
                    st.caption("Kart renkli hücreler %100'den düşük oranları gösterir. Gri = %100 (tam verim).")
                    st.markdown(make_rates_table(sus.get("otd_rates",{}), sus["otd_alloc"], ["OD0","OD2","OD3","OD4","OD6"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**Günlük Üretim**")
                st.markdown(make_grid(sus["otd_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**📦 Kalan Stok — KSO**")
                st.caption("🔴 Negatif = stok açığı — üretim talebi karşılayamıyor")
                st.markdown(make_grid(sus["otd_rem"], "o", d_idx=DATE_INDICES), unsafe_allow_html=True)

            with _edit_tab:
                st.markdown("""<div style="background:rgba(37,99,235,0.12);border:1px solid rgba(37,99,235,0.3);border-radius:10px;padding:12px 16px;margin-bottom:12px;">
                    <span style="color:#93c5fd;font-weight:700;">✏️ Manuel Alokasyon Düzenleme</span><br>
                    <span style="color:#cbd5e1;font-size:0.82rem;">Tablodaki hücrelere tıklayarak kart ataması yapın. Setup değişiklikleri otomatik algılanır ve oran önerilir.</span>
                </div>""", unsafe_allow_html=True)

                # ═══ v3.4: Optimize Önerisi — referans tablo ═══
                with st.expander("🤖 Optimize Önerisi (hangi kart nereye atanmalı?)", expanded=False):
                    _opt_ref = run_stage_opt(sus, "OTD")
                    if _opt_ref["proposals"]:
                        st.caption("Optimizer'ın önerdiği değişiklikler — editörde referans olarak kullanabilirsiniz:")
                        for p in _opt_ref["proposals"]:
                            st.markdown(
                                f'<div style="display:flex;align-items:center;gap:8px;padding:6px 10px;margin:3px 0;border-radius:6px;background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.15);">'
                                f'<span style="color:#22c55e;font-weight:700;min-width:36px;">{p.get("line","—")}</span>'
                                f'<span style="color:#93c5fd;">Gün {p["day"]} ({p["date"]})</span>'
                                f'<span style="color:#fff;font-weight:600;">→ {p["card"]}</span>'
                                f'<span style="color:#64748b;font-size:0.78rem;margin-left:auto;">({p["impact"]})</span>'
                                f'</div>', unsafe_allow_html=True)
                        st.markdown(f'<div style="color:{"#22c55e" if _opt_ref["status"]=="feasible" else "#f59e0b"};font-weight:600;margin-top:8px;">{_opt_ref["message"]}</div>', unsafe_allow_html=True)
                    else:
                        st.success("✅ Mevcut OTD planında ihlal yok — optimize önerisi bulunmuyor.")

                with st.expander("📖 Mevcut Alokasyon & Oranlar (salt okunur)", expanded=False):
                    st.markdown(make_alloc_rates_combined(sus["otd_alloc"], sus.get("otd_rates",{}), ["OD0","OD2","OD3","OD4","OD6"], d_idx=DATE_INDICES), unsafe_allow_html=True)

                with st.expander("📖 Hat — Kart Uyumluluk Tablosu", expanded=False):
                    compat_rows = []
                    for ln in ["OD0","OD2","OD3","OD4","OD6"]:
                        cards = sorted([c for c in TEMPO.get(ln, {}) if TEMPO[ln][c] > 0])
                        compat_rows.append({"Hat": ln, "Üretilebilir Kartlar": ", ".join(cards),
                                            "Tempoları": " | ".join([f"{c}:{TEMPO[ln][c]}" for c in cards])})
                    st.dataframe(pd.DataFrame(compat_rows), use_container_width=True, hide_index=True)

                # ═══ Kart editörü ═══
                st.markdown("**🎯 Kart Ataması** — hücreye tıklayın, listeden kart seçin:")
                edit_data = {}
                for ln in ["OD0","OD2","OD3","OD4","OD6"]:
                    row = sus["otd_alloc"].get(ln, [""]*N_DAYS)
                    if isinstance(row[0], list): row = row[0]
                    edit_data[ln] = {f"{SUS_DAYS[i]} {SUS_DATES[i]}": (row[i] if i < len(row) else "") for i in range(N_DAYS)}
                df_edit = pd.DataFrame(edit_data).T
                df_edit.index.name = "Hat"

                edited_df = st.data_editor(
                    df_edit, use_container_width=True, num_rows="fixed",
                    key="otd_alloc_editor",
                    column_config={
                        col: st.column_config.SelectboxColumn(
                            col, options=[""] + SUS_CARDS, default="", width="small"
                        ) for col in df_edit.columns
                    }
                )

                # ═══ Butonlar ═══
                ec1, ec2, ec3 = st.columns([2, 2, 4])
                with ec1:
                    if st.button("🔍 Etkiyi Önizle", type="primary", use_container_width=True, key="btn_preview_alloc"):
                        # Düzenlemeyi session state'e kaydet
                        _new_alloc = {}
                        for ln in ["OD0","OD2","OD3","OD4","OD6"]:
                            rv = []
                            for i in range(N_DAYS):
                                cn = f"{SUS_DAYS[i]} {SUS_DATES[i]}"
                                cell = str(edited_df.loc[ln, cn]).strip() if cn in edited_df.columns else ""
                                rv.append(cell if cell in SUS_CARDS else "")
                            _new_alloc[ln] = rv
                        # Oranları hesapla
                        _new_rates = {}
                        _setups = detect_setup_changes(_new_alloc, sus["otd_alloc"], ["OD0","OD2","OD3","OD4","OD6"])
                        for ln in ["OD0","OD2","OD3","OD4","OD6"]:
                            old_rates = sus.get("otd_rates", {}).get(ln, [1]*N_DAYS)
                            old_alloc_row = sus["otd_alloc"].get(ln, [""]*N_DAYS)
                            if isinstance(old_alloc_row[0], list): old_alloc_row = old_alloc_row[0]
                            rvals = []
                            for i in range(N_DAYS):
                                if _new_alloc[ln][i] == (old_alloc_row[i] if i < len(old_alloc_row) else ""):
                                    rvals.append(old_rates[i] if i < len(old_rates) else 1.0)
                                elif not _new_alloc[ln][i]:
                                    rvals.append(1.0)
                                else:
                                    prev = _new_alloc[ln][i-1] if i > 0 else ""
                                    rvals.append(SETUP_DEFAULT_RATE if (prev and prev != _new_alloc[ln][i]) else 1.0)
                            _new_rates[ln] = rvals
                        st.session_state.preview_active = True
                        st.session_state.preview_alloc = _new_alloc
                        st.session_state.preview_rates = _new_rates
                        st.session_state.preview_setups = _setups
                        st.rerun()
                with ec2:
                    if st.session_state.preview_active:
                        if st.button("✗ Önizlemeyi Kapat", use_container_width=True, key="btn_cancel_preview"):
                            st.session_state.preview_active = False
                            st.session_state.preview_alloc = None
                            st.session_state.preview_rates = None
                            st.session_state.preview_setups = None
                            st.rerun()

                # ═══ v3.4: Kalıcı önizleme — session state'den okur, kapanmaz ═══
                if st.session_state.preview_active and st.session_state.preview_alloc:
                    p_alloc = st.session_state.preview_alloc
                    p_rates = st.session_state.preview_rates
                    p_setups = st.session_state.preview_setups or []
                    setup_items = [s for s in p_setups if s["suggested_rate"] < 1.0]

                    # ── Setup oranları düzenleme (kalıcı — kapanmaz) ──
                    if setup_items:
                        st.write("---")
                        st.markdown(f"""<div style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);border-radius:10px;padding:12px 16px;">
                            <span style="color:#f59e0b;font-weight:700;">⚠️ {len(setup_items)} Setup Değişikliği</span>
                            <span style="color:#cbd5e1;font-size:0.82rem;"> — Oranları düzenleyebilirsiniz, sayfa kapanmaz:</span>
                        </div>""", unsafe_allow_html=True)

                        for si, s in enumerate(setup_items):
                            sc1, sc2, sc3 = st.columns([4, 2, 2])
                            with sc1:
                                st.markdown(
                                    f'<div style="color:#cbd5e1;font-size:0.85rem;padding-top:6px;">'
                                    f'🔄 <strong style="color:#f59e0b;">{s["line"]}</strong> Gün {s["day"]} ({s["date"]}): '
                                    f'<span style="color:#ef4444;">{s["prev_card"]}</span> → <span style="color:#22c55e;">{s["new_card"]}</span>'
                                    f'</div>', unsafe_allow_html=True)
                            with sc2:
                                cur_rate = p_rates[s["line"]][s["day_idx"]]
                                adj_rate = st.number_input(
                                    f'Oran {s["line"]} G{s["day"]}', value=float(cur_rate),
                                    min_value=0.0, max_value=1.0, step=0.05, format="%.2f",
                                    key=f"setup_rate_{s['line']}_{s['day_idx']}",
                                    label_visibility="collapsed"
                                )
                                # Oranı session state'e geri yaz
                                if adj_rate != cur_rate:
                                    st.session_state.preview_rates[s["line"]][s["day_idx"]] = adj_rate
                            with sc3:
                                pct = int(adj_rate * 100)
                                clr = "#ef4444" if pct < 60 else "#f59e0b" if pct < 100 else "#22c55e"
                                st.markdown(f'<div style="padding-top:8px;"><span style="color:{clr};font-weight:800;font-size:1rem;">%{pct}</span></div>', unsafe_allow_html=True)

                    # Güncel oranlarla hesapla
                    p_rates = st.session_state.preview_rates  # güncel (düzenlenmiş olabilir)

                    # ── Birleşik önizleme ──
                    st.markdown("**📊 Düzenlenmiş Alokasyon & Oranlar:**")
                    st.markdown(make_alloc_rates_combined(p_alloc, p_rates, ["OD0","OD2","OD3","OD4","OD6"], d_idx=DATE_INDICES), unsafe_allow_html=True)

                    # ── Hesapla ──
                    new_daily = alloc_to_daily(p_alloc, TEMPO, ["OD0","OD2","OD3","OD4","OD6"], p_rates)
                    preview_plan = copy.deepcopy(sus)
                    preview_plan["otd_alloc"] = p_alloc
                    preview_plan["otd_rates"] = p_rates
                    preview_plan["otd_daily"] = new_daily
                    preview_plan = recalc_stocks(preview_plan)
                    impact = compute_manual_impact(sus, preview_plan)

                    # ── Değişiklikler (ilk gösterilen) ──
                    st.write("---")
                    st.markdown("### 🔍 Değişiklik Etki Analizi")
                    ic1, ic2, ic3, ic4 = st.columns(4)
                    old_viol = sum(1 for c in SUS_CARDS for v in sus["otd_rem"].get(c,[]) if v<0)
                    new_viol = sum(1 for c in SUS_CARDS for v in preview_plan["otd_rem"].get(c,[]) if v<0)
                    old_total = sum(sum(v) for v in sus["otd_daily"].values())
                    new_total = sum(sum(v) for v in preview_plan["otd_daily"].values())
                    with ic1: st.metric("KSO İhlal (Önce)", f"{old_viol} gün×kart")
                    with ic2: st.metric("KSO İhlal (Sonra)", f"{new_viol} gün×kart", delta=f"{new_viol-old_viol:+d}", delta_color="inverse")
                    with ic3: st.metric("OTD Üretim (Önce)", f"{old_total:,}")
                    with ic4: st.metric("OTD Üretim (Sonra)", f"{new_total:,}", delta=f"{new_total-old_total:+,}")

                    if impact["changes"]:
                        st.markdown("**📋 Stok Değişimleri:**")
                        changes_df = pd.DataFrame(impact["changes"])
                        changes_df = changes_df.rename(columns={"card":"Kart","stage":"Aşama","day":"Gün","date":"Tarih","old":"Önce","new":"Sonra","diff":"Fark","status":"Durum"})
                        changes_df["Durum"] = changes_df["Durum"].map({"fixed":"✅ Çözüldü","new_violation":"❌ Yeni İhlal","changed":"🔄 Değişti"})
                        st.dataframe(changes_df[["Kart","Aşama","Gün","Tarih","Önce","Sonra","Fark","Durum"]], use_container_width=True, hide_index=True, height=min(400, 40+35*len(changes_df)))
                        s = impact["summary"]
                        st.markdown(
                            f'<div style="background:rgba(0,15,50,0.5);border-radius:10px;padding:12px;margin-top:8px;backdrop-filter:blur(6px);">'
                            f'<span style="color:#22c55e;font-weight:700;">✅ {s["fixed"]} ihlal çözüldü</span> &nbsp;|&nbsp; '
                            f'<span style="color:#ef4444;font-weight:700;">❌ {s["new_violations"]} yeni ihlal</span> &nbsp;|&nbsp; '
                            f'<span style="color:#93c5fd;">{s["unchanged"]} stok değeri değişti</span></div>',
                            unsafe_allow_html=True)

                    with st.expander("📈 Detaylı Tablolar (Üretim & Stok)", expanded=False):
                        st.markdown("**Yeni Günlük Üretim:**")
                        st.markdown(make_grid_plan(new_daily, sus["otd_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                        st.markdown("**📦 Yeni Kalan Stok — KSO:**")
                        st.markdown(make_grid_plan(preview_plan["otd_rem"], sus["otd_rem"], "o", d_idx=DATE_INDICES), unsafe_allow_html=True)

                    # ── Uygula — SİCİL DOĞRULAMASI ──
                    st.write("---")
                    if st.session_state.auth:
                        if st.button("✅ Alokasyonu Uygula", type="primary", use_container_width=True, key="btn_apply_final"):
                            st.session_state.sus = preview_plan
                            st.session_state.otd_opt_res = None
                            st.session_state.manual_impact = impact
                            st.session_state.preview_active = False
                            st.session_state.preview_alloc = None
                            st.session_state.preview_rates = None
                            st.session_state.preview_setups = None
                            st.success(f"✅ Uygulandı! (Sicil: {st.session_state.auth_sicil})")
                            st.rerun()
                    else:
                        st.markdown("""<div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);border-radius:10px;padding:12px 16px;">
                            <span style="color:#ef4444;font-weight:700;">🔒 Yetkilendirme Gerekli</span>
                            <span style="color:#cbd5e1;font-size:0.82rem;"> — Değişiklik uygulamak için sicil numaranızı girin.</span>
                        </div>""", unsafe_allow_html=True)
                        ap1, ap2 = st.columns([3, 1])
                        with ap1:
                            apply_sicil = st.text_input("Sicil:", type="password", placeholder="Sicil numaranız", key="apply_sicil_input", label_visibility="collapsed")
                        with ap2:
                            if st.button("🔓 Doğrula & Uygula", type="primary", use_container_width=True, key="apply_sicil_btn"):
                                if apply_sicil.strip() in YETKILI_SICILLER:
                                    st.session_state.auth = True
                                    st.session_state.auth_sicil = apply_sicil.strip()
                                    st.session_state.sus = preview_plan
                                    st.session_state.otd_opt_res = None
                                    st.session_state.manual_impact = impact
                                    st.session_state.preview_active = False
                                    st.session_state.preview_alloc = None
                                    st.session_state.preview_rates = None
                                    st.session_state.preview_setups = None
                                    st.success(f"✅ Yetkilendirildi ve uygulandı! (Sicil: {apply_sicil.strip()})")
                                    st.rerun()
                                else:
                                    st.error("❌ Yetkisiz sicil numarası.")

        else:
            # Optimizasyon sonucu mevcut — iç sekmeler: Referans | Optimize
            ot1, ot2 = st.tabs(["📋 Referans Plan (Mevcut)", "⚡ Optimize Sonucu"])
            np = otd_res["new_plan"]

            with ot1:
                st.markdown("**Hat – Kart Alokasyonu**")
                st.markdown(make_alloc(sus["otd_alloc"], ["OD0","OD2","OD3","OD4","OD6"], d_idx=DATE_INDICES, rates_dict=sus.get("otd_rates",{})), unsafe_allow_html=True)
                st.markdown("**Günlük Üretim**")
                st.markdown(make_grid(sus["otd_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**📦 Kalan Stok — KSO**")
                st.caption("🔴 Negatif = stok açığı")
                st.markdown(make_grid(sus["otd_rem"], "o", d_idx=DATE_INDICES), unsafe_allow_html=True)

            with ot2:
                st.markdown(f"**{otd_res['message']}**")
                proposals = otd_res.get("proposals", [])
                if proposals:
                    st.caption("🟩 Yeşil çerçeve = referanstan farklı hücreler")
                    st.markdown("**Hat – Kart Alokasyonu (Optimize)**")
                    st.markdown(make_alloc_compare(np["otd_alloc"], sus["otd_alloc"], ["OD0","OD2","OD3","OD4","OD6"], d_idx=DATE_INDICES, rates_dict=sus.get("otd_rates",{})), unsafe_allow_html=True)
                    st.markdown("**Günlük Üretim (Optimize)**")
                    st.markdown(make_grid_plan(np["otd_daily"], sus["otd_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                    st.markdown("**📦 Kalan Stok — KSO (Optimize)**")
                    st.markdown(make_grid_plan(np["otd_rem"], sus["otd_rem"], "o", d_idx=DATE_INDICES), unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("**📋 Değişiklik Önerileri:**")
                    approvals_otd = {}
                    for i, p in enumerate(proposals):
                        pc1, pc2 = st.columns([7, 1])
                        with pc1:
                            st.markdown(
                                f'<div class="status-card" style="padding:8px 14px;">'
                                f'<span style="color:#22c55e;font-weight:700;">🟢 {p["card"]}</span>'
                                f' | Gün {p["day"]} ({p["date"]}) | Hat: {p.get("line","—")}'
                                f' | {p["old"]:,} → <span style="color:#22c55e;">{p["new"]:,}</span>'
                                f' &nbsp;<span style="color:#93c5fd;font-size:0.8rem;">({p["impact"]})</span>'
                                f'<br><span style="color:#64748b;font-size:0.78rem;">📌 {p["reason"]}</span></div>',
                                unsafe_allow_html=True
                            )
                        with pc2:
                            approvals_otd[i] = st.checkbox("✓", value=True, key=f"otd_appr_{i}")

                    ac1, ac2 = st.columns([2, 2])
                    with ac1:
                        if st.button("✅ Seçilen OTD Değişikliklerini Uygula",
                                     type="primary", use_container_width=True, key="otd_apply_btn"):
                            applied_plan, cnt = apply_stage_proposals(proposals, sus, "OTD", approvals_otd)
                            st.session_state.sus = applied_plan
                            st.session_state.otd_opt_res = None
                            st.success(f"✅ {cnt} OTD değişikliği uygulandı.")
                            st.rerun()
                    with ac2:
                        if st.button("✗ İptal et", use_container_width=True, key="otd_cancel_btn"):
                            st.session_state.otd_opt_res = None
                            st.rerun()
                else:
                    st.success("✅ Mevcut OTD planında ihlal yok.")
                    if st.button("Tamam", key="otd_ok_btn"):
                        st.session_state.otd_opt_res = None
                        st.rerun()

    # ==================================================================
    # MD EXPANDER
    # ==================================================================
    with st.expander("✋ MD — Manuel Dizgi (Hat Alokasyonu & Üretim & Stok)", expanded=False):

        hc1, hc2, hc3, hc4 = st.columns([3, 1, 2, 2])
        with hc1:
            st.markdown(_rozet("md_opt_res", "MD"), unsafe_allow_html=True)
        with hc2:
            up_md = st.file_uploader(
                "📤", type=["json","csv","xlsx"], key="up_md_exp",
                label_visibility="collapsed",
                help="JSON: {md_alloc:{...}, md_daily:{...}}  |  CSV: Kart,07.05,...,23.05"
            )
            pf_md = process_upload_file(up_md, "last_md_up")
            if pf_md is not None:
                ext = pf_md.name.rsplit(".", 1)[-1].lower()
                parsed, err = (parse_upload_json(pf_md) if ext == "json"
                               else parse_upload_csv(pf_md, "md_daily"))
                if err:
                    st.error(f"Okuma hatası: {err}")
                else:
                    updated = [k for k in ("md_alloc","md_daily") if k in parsed]
                    if updated:
                        for k in updated: st.session_state.sus[k] = parsed[k]
                        st.session_state.sus = recalc_stocks(st.session_state.sus)
                        st.session_state.md_opt_res = None
                        st.success(f"✅ MD verisi güncellendi: {', '.join(updated)}")
                        st.rerun()
                    else:
                        st.error("Geçerli MD anahtarı bulunamadı.")
        with hc3:
            st.markdown(
                '<div style="font-size:0.72rem;color:#64748b;padding-top:6px;">'
                'JSON: <code>md_alloc</code>, <code>md_daily</code><br>'
                'CSV: Kart, 07.05 … 23.05</div>',
                unsafe_allow_html=True
            )
        with hc4:
            if st.button("✋  MD'yi Optimize Et", type="primary",
                         use_container_width=True, key="btn_md_exp"):
                with st.spinner("MD analiz ve optimize ediliyor…"):
                    st.session_state.md_opt_res = run_stage_opt(sus, "MD")
                st.rerun()

        md_res = st.session_state.md_opt_res

        if md_res is None:
            _md_ref_tab, _md_edit_tab = st.tabs(["📋 Görüntüle", "✏️ Manuel Düzenle"])

            with _md_ref_tab:
                st.markdown("**Hat – Kart Alokasyonu**")
                st.markdown(make_alloc(sus["md_alloc"], ["MD1","MD2"], d_idx=DATE_INDICES, rates_dict=sus.get("md_rates",{})), unsafe_allow_html=True)
                with st.expander("📊 Verimlilik Oranları (MD)", expanded=False):
                    st.caption("Hat bölünmesi (örn. 0.5+0.5) durumlarında satırlar ayrı gösterilir. %100 = tam verim, <%100 = bölünme/setup.")
                    st.markdown(make_rates_table(sus.get("md_rates",{}), sus["md_alloc"], ["MD1","MD2"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**Günlük Üretim**")
                st.markdown(make_grid(sus["md_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**📦 Kalan Stok — KSM**")
                st.markdown(make_grid(sus["md_rem"], "m", d_idx=DATE_INDICES), unsafe_allow_html=True)

            with _md_edit_tab:
                st.markdown("""<div style="background:rgba(37,99,235,0.12);border:1px solid rgba(37,99,235,0.3);border-radius:10px;padding:12px 16px;margin-bottom:12px;">
                    <span style="color:#93c5fd;font-weight:700;">✏️ MD Manuel Alokasyon Düzenleme</span><br>
                    <span style="color:#cbd5e1;font-size:0.82rem;">MD2 hattının paralel satırları ayrı satır olarak düzenlenebilir (MD2-1, MD2-2).</span>
                </div>""", unsafe_allow_html=True)

                with st.expander("📖 Hat — Kart Uyumluluk Tablosu", expanded=False):
                    md_compat = []
                    for ln in ["MD1","MD2"]:
                        cards = sorted([c for c in MD_TEMPO.get(ln, {}) if MD_TEMPO[ln][c] > 0])
                        md_compat.append({"Hat": ln, "Üretilebilir": ", ".join(cards),
                                          "Tempoları": " | ".join([f"{c}:{MD_TEMPO[ln][c]}" for c in cards])})
                    st.dataframe(pd.DataFrame(md_compat), use_container_width=True, hide_index=True)

                # Çok satırlı yapıyı düzleştir: MD1-1, MD2-1, MD2-2 ...
                md_row_labels = []
                md_row_data = {}
                for ln in ["MD1","MD2"]:
                    rows = sus["md_alloc"].get(ln, [])
                    if not rows: continue
                    if not isinstance(rows[0], list): rows = [rows]
                    for ri, row in enumerate(rows):
                        label = f"{ln}-{ri+1}"
                        md_row_labels.append((label, ln, ri))
                        md_row_data[label] = {f"{SUS_DAYS[i]} {SUS_DATES[i]}": (row[i] if i < len(row) else "") for i in range(N_DAYS)}

                st.markdown("**🎯 MD Kart Ataması:**")
                df_md_edit = pd.DataFrame(md_row_data).T
                df_md_edit.index.name = "Hat-Satır"
                # Sadece MD'ye uğrayan kartları seçenek olarak göster
                md_cards = [c for c in SUS_CARDS if PROCESS_MAP.get(c)]
                edited_md = st.data_editor(
                    df_md_edit, use_container_width=True, num_rows="fixed",
                    key="md_alloc_editor",
                    column_config={
                        col: st.column_config.SelectboxColumn(
                            col, options=[""] + md_cards, default="", width="small"
                        ) for col in df_md_edit.columns
                    }
                )

                ec1, ec2, _ = st.columns([2, 2, 4])
                with ec1:
                    if st.button("🔍 MD Etkisini Önizle", type="primary", use_container_width=True, key="btn_md_preview"):
                        # Düzlenmiş satırları tekrar MD1/MD2 yapısına geri çevir
                        new_md_alloc = {"MD1": [], "MD2": []}
                        for label, ln, ri in md_row_labels:
                            rv = []
                            for i in range(N_DAYS):
                                cn = f"{SUS_DAYS[i]} {SUS_DATES[i]}"
                                cell = str(edited_md.loc[label, cn]).strip() if cn in edited_md.columns else ""
                                rv.append(cell if cell in md_cards else "")
                            new_md_alloc[ln].append(rv)
                        # Setup tespiti (her satırı ayrı bir "hat" gibi değerlendir)
                        flat_new = {}
                        flat_old = {}
                        for label, ln, ri in md_row_labels:
                            flat_new[label] = new_md_alloc[ln][ri]
                            old_rows = sus["md_alloc"].get(ln, [])
                            if old_rows and isinstance(old_rows[0], list):
                                flat_old[label] = old_rows[ri] if ri < len(old_rows) else [""]*N_DAYS
                            else:
                                flat_old[label] = old_rows if ri == 0 else [""]*N_DAYS
                        md_setups = detect_setup_changes(flat_new, flat_old, [lbl for lbl,_,_ in md_row_labels])

                        # MD oranlarını hesapla — mevcut oranları koru, setup değişiminde %50 öner
                        new_md_rates = {"MD1": [], "MD2": []}
                        for label, ln, ri in md_row_labels:
                            old_rates_lines = sus.get("md_rates", {}).get(ln, [])
                            old_rates = old_rates_lines[ri] if ri < len(old_rates_lines) else [1.0]*N_DAYS
                            old_alloc_row = flat_old[label]
                            rvals = []
                            for i in range(N_DAYS):
                                new_c = new_md_alloc[ln][ri][i]
                                if new_c == (old_alloc_row[i] if i < len(old_alloc_row) else ""):
                                    rvals.append(old_rates[i] if i < len(old_rates) else 1.0)
                                elif not new_c:
                                    rvals.append(1.0)
                                else:
                                    prev = new_md_alloc[ln][ri][i-1] if i > 0 else ""
                                    rvals.append(SETUP_DEFAULT_RATE if (prev and prev != new_c) else 1.0)
                            new_md_rates[ln].append(rvals)

                        st.session_state.md_preview_active = True
                        st.session_state.md_preview_alloc = new_md_alloc
                        st.session_state.md_preview_rates = new_md_rates
                        st.session_state.md_preview_setups = md_setups
                        st.rerun()
                with ec2:
                    if st.session_state.md_preview_active:
                        if st.button("✗ MD Önizleme Kapat", use_container_width=True, key="btn_md_cancel"):
                            st.session_state.md_preview_active = False
                            st.session_state.md_preview_alloc = None
                            st.session_state.md_preview_rates = None
                            st.session_state.md_preview_setups = None
                            st.rerun()

                if st.session_state.md_preview_active and st.session_state.md_preview_alloc:
                    p_alloc = st.session_state.md_preview_alloc
                    p_rates = st.session_state.md_preview_rates or {"MD1":[[1.0]*N_DAYS]*len(p_alloc.get("MD1",[])),
                                                                    "MD2":[[1.0]*N_DAYS]*len(p_alloc.get("MD2",[]))}
                    p_setups = st.session_state.md_preview_setups or []
                    setup_items = [s for s in p_setups if s["suggested_rate"] < 1.0]

                    # Setup oran düzenleme paneli
                    if setup_items:
                        st.write("---")
                        st.markdown(f"""<div style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);border-radius:10px;padding:12px 16px;">
                            <span style="color:#f59e0b;font-weight:700;">⚠️ {len(setup_items)} MD Setup Değişikliği</span>
                            <span style="color:#cbd5e1;font-size:0.82rem;"> — Oranları düzenleyebilirsiniz:</span>
                        </div>""", unsafe_allow_html=True)
                        for si, s in enumerate(setup_items):
                            sc1, sc2, sc3 = st.columns([4, 2, 2])
                            # label "MD1-1" → ln, ri
                            try:
                                parts = s["line"].split("-")
                                ln_k = parts[0]
                                ri_k = int(parts[1]) - 1
                            except Exception:
                                ln_k, ri_k = s["line"], 0
                            with sc1:
                                st.markdown(
                                    f'<div style="color:#cbd5e1;font-size:0.85rem;padding-top:6px;">'
                                    f'🔄 <strong style="color:#f59e0b;">{s["line"]}</strong> Gün {s["day"]} ({s["date"]}): '
                                    f'<span style="color:#ef4444;">{s["prev_card"]}</span> → <span style="color:#22c55e;">{s["new_card"]}</span>'
                                    f'</div>', unsafe_allow_html=True)
                            with sc2:
                                try:
                                    cur_rate = p_rates[ln_k][ri_k][s["day_idx"]]
                                except (KeyError, IndexError):
                                    cur_rate = 1.0
                                adj_rate = st.number_input(
                                    f'Oran {s["line"]} G{s["day"]}', value=float(cur_rate),
                                    min_value=0.0, max_value=1.0, step=0.05, format="%.2f",
                                    key=f"md_setup_rate_{s['line']}_{s['day_idx']}",
                                    label_visibility="collapsed"
                                )
                                if adj_rate != cur_rate:
                                    st.session_state.md_preview_rates[ln_k][ri_k][s["day_idx"]] = adj_rate
                            with sc3:
                                pct = int(adj_rate * 100)
                                clr = "#ef4444" if pct < 60 else "#f59e0b" if pct < 100 else "#22c55e"
                                st.markdown(f'<div style="padding-top:8px;"><span style="color:{clr};font-weight:800;font-size:1rem;">%{pct}</span></div>', unsafe_allow_html=True)

                    p_rates = st.session_state.md_preview_rates

                    # MD için oran-aware alloc_to_daily — multi-row destekli
                    md_new_daily = {c: [0]*N_DAYS for c in SUS_CARDS}
                    for ln in ["MD1","MD2"]:
                        rows = p_alloc.get(ln, [])
                        rates_rows = p_rates.get(ln, [[1.0]*N_DAYS]*len(rows))
                        for ri, row in enumerate(rows):
                            row_rates = rates_rows[ri] if ri < len(rates_rows) else [1.0]*N_DAYS
                            for i, card in enumerate(row):
                                if i < N_DAYS and card and card in MD_TEMPO.get(ln, {}):
                                    rate = row_rates[i] if i < len(row_rates) else 1.0
                                    md_new_daily[card][i] += int(MD_TEMPO[ln][card] * rate)

                    # Düzenlenmiş alokasyon + oranlar görünümü
                    st.markdown("**📊 Düzenlenmiş MD Alokasyon & Oranlar:**")
                    st.markdown(make_alloc(p_alloc, ["MD1","MD2"], d_idx=DATE_INDICES, rates_dict=p_rates), unsafe_allow_html=True)

                    preview_plan = copy.deepcopy(sus)
                    preview_plan["md_alloc"] = p_alloc
                    preview_plan["md_rates"] = p_rates
                    preview_plan["md_daily"] = md_new_daily
                    preview_plan = recalc_stocks(preview_plan)
                    impact = compute_manual_impact(sus, preview_plan)

                    st.write("---")
                    st.markdown("### 🔍 MD Değişiklik Etki Analizi")
                    ic1, ic2, ic3, ic4 = st.columns(4)
                    old_viol = sum(1 for c in SUS_CARDS if PROCESS_MAP.get(c) for v in sus["md_rem"].get(c,[]) if v<0)
                    new_viol = sum(1 for c in SUS_CARDS if PROCESS_MAP.get(c) for v in preview_plan["md_rem"].get(c,[]) if v<0)
                    old_total = sum(sum(v) for v in sus["md_daily"].values())
                    new_total = sum(sum(v) for v in preview_plan["md_daily"].values())
                    with ic1: st.metric("KSM İhlal (Önce)", f"{old_viol} gün×kart")
                    with ic2: st.metric("KSM İhlal (Sonra)", f"{new_viol} gün×kart", delta=f"{new_viol-old_viol:+d}", delta_color="inverse")
                    with ic3: st.metric("MD Üretim (Önce)", f"{old_total:,}")
                    with ic4: st.metric("MD Üretim (Sonra)", f"{new_total:,}", delta=f"{new_total-old_total:+,}")

                    if impact["changes"]:
                        st.markdown("**📋 Stok Değişimleri (MD odaklı):**")
                        cdf = pd.DataFrame([c for c in impact["changes"] if c["stage"] in ("KSM","KST","KSO")])
                        if not cdf.empty:
                            cdf = cdf.rename(columns={"card":"Kart","stage":"Aşama","day":"Gün","date":"Tarih","old":"Önce","new":"Sonra","diff":"Fark","status":"Durum"})
                            cdf["Durum"] = cdf["Durum"].map({"fixed":"✅ Çözüldü","new_violation":"❌ Yeni İhlal","changed":"🔄 Değişti"})
                            st.dataframe(cdf[["Kart","Aşama","Gün","Tarih","Önce","Sonra","Fark","Durum"]], use_container_width=True, hide_index=True, height=min(400, 40+35*len(cdf)))

                    with st.expander("📈 MD Detaylı Tablolar", expanded=False):
                        st.markdown("**Yeni MD Günlük Üretim:**")
                        st.markdown(make_grid_plan(md_new_daily, sus["md_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                        st.markdown("**📦 Yeni KSM:**")
                        st.markdown(make_grid_plan(preview_plan["md_rem"], sus["md_rem"], "m", d_idx=DATE_INDICES), unsafe_allow_html=True)

                    st.write("---")
                    if st.session_state.auth:
                        if st.button("✅ MD Alokasyonu Uygula", type="primary", use_container_width=True, key="btn_md_apply_final"):
                            st.session_state.sus = preview_plan
                            st.session_state.md_opt_res = None
                            st.session_state.md_preview_active = False
                            st.session_state.md_preview_alloc = None
                            st.session_state.md_preview_setups = None
                            st.session_state.md_preview_rates = None
                            st.success(f"✅ MD uygulandı! (Sicil: {st.session_state.auth_sicil})")
                            st.rerun()
                    else:
                        st.markdown("""<div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);border-radius:10px;padding:12px 16px;">
                            <span style="color:#ef4444;font-weight:700;">🔒 Yetkilendirme Gerekli</span> <span style="color:#cbd5e1;font-size:0.82rem;">— Sicil numaranızı girin.</span>
                        </div>""", unsafe_allow_html=True)
                        ap1, ap2 = st.columns([3, 1])
                        with ap1:
                            apply_sicil_md = st.text_input("Sicil:", type="password", placeholder="Sicil numaranız", key="apply_sicil_md", label_visibility="collapsed")
                        with ap2:
                            if st.button("🔓 MD Doğrula & Uygula", type="primary", use_container_width=True, key="apply_sicil_md_btn"):
                                if apply_sicil_md.strip() in YETKILI_SICILLER:
                                    st.session_state.auth = True
                                    st.session_state.auth_sicil = apply_sicil_md.strip()
                                    st.session_state.sus = preview_plan
                                    st.session_state.md_opt_res = None
                                    st.session_state.md_preview_active = False
                                    st.session_state.md_preview_alloc = None
                                    st.session_state.md_preview_setups = None
                                    st.session_state.md_preview_rates = None
                                    st.success(f"✅ Uygulandı! (Sicil: {apply_sicil_md.strip()})")
                                    st.rerun()
                                else:
                                    st.error("❌ Yetkisiz sicil numarası.")

        else:
            mt1, mt2 = st.tabs(["📋 Referans Plan (Mevcut)", "⚡ Optimize Sonucu"])
            np = md_res["new_plan"]

            with mt1:
                st.markdown("**Hat – Kart Alokasyonu**")
                st.markdown(make_alloc(sus["md_alloc"], ["MD1","MD2"], d_idx=DATE_INDICES, rates_dict=sus.get("md_rates",{})), unsafe_allow_html=True)
                st.markdown("**Günlük Üretim**")
                st.markdown(make_grid(sus["md_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**📦 Kalan Stok — KSM**")
                st.markdown(make_grid(sus["md_rem"], "m", d_idx=DATE_INDICES), unsafe_allow_html=True)

            with mt2:
                st.markdown(f"**{md_res['message']}**")
                proposals = md_res.get("proposals", [])
                if proposals:
                    st.caption("🟩 Yeşil çerçeve = referanstan farklı hücreler")
                    st.markdown("**Günlük Üretim (Optimize)**")
                    st.markdown(make_grid_plan(np["md_daily"], sus["md_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                    st.markdown("**📦 Kalan Stok — KSM (Optimize)**")
                    st.markdown(make_grid_plan(np["md_rem"], sus["md_rem"], "m", d_idx=DATE_INDICES), unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("**📋 Değişiklik Önerileri:**")
                    approvals_md = {}
                    for i, p in enumerate(proposals):
                        pc1, pc2 = st.columns([7, 1])
                        with pc1:
                            st.markdown(
                                f'<div class="status-card" style="padding:8px 14px;">'
                                f'<span style="color:#3b82f6;font-weight:700;">🔵 {p["card"]}</span>'
                                f' | Gün {p["day"]} ({p["date"]}) | Hat: {p.get("line","—")}'
                                f' | {p["old"]:,} → <span style="color:#22c55e;">{p["new"]:,}</span>'
                                f' &nbsp;<span style="color:#93c5fd;font-size:0.8rem;">({p["impact"]})</span>'
                                f'<br><span style="color:#64748b;font-size:0.78rem;">📌 {p["reason"]}</span></div>',
                                unsafe_allow_html=True
                            )
                        with pc2:
                            approvals_md[i] = st.checkbox("✓", value=True, key=f"md_appr_{i}")

                    mc1, mc2 = st.columns([2, 2])
                    with mc1:
                        if st.button("✅ Seçilen MD Değişikliklerini Uygula",
                                     type="primary", use_container_width=True, key="md_apply_btn"):
                            applied_plan, cnt = apply_stage_proposals(proposals, sus, "MD", approvals_md)
                            st.session_state.sus = applied_plan
                            st.session_state.md_opt_res = None
                            st.success(f"✅ {cnt} MD değişikliği uygulandı.")
                            st.rerun()
                    with mc2:
                        if st.button("✗ İptal et", use_container_width=True, key="md_cancel_btn"):
                            st.session_state.md_opt_res = None
                            st.rerun()
                else:
                    st.success("✅ Mevcut MD planında ihlal yok.")
                    if st.button("Tamam", key="md_ok_btn"):
                        st.session_state.md_opt_res = None
                        st.rerun()

    # ==================================================================
    # TA EXPANDER
    # ==================================================================
    with st.expander("🔬 TA — Test & Ayar (Üretim & Stok & Montaj Planı)", expanded=False):

        hc1, hc2, hc3, hc4 = st.columns([3, 1, 2, 2])
        with hc1:
            st.markdown(_rozet("ta_opt_res", "TA"), unsafe_allow_html=True)
        with hc2:
            up_ta = st.file_uploader(
                "📤", type=["json","csv","xlsx"], key="up_ta_exp",
                label_visibility="collapsed",
                help="JSON: {ta_daily:{...}, assembly:{...}}  |  CSV: Kart,07.05,...,23.05"
            )
            pf_ta = process_upload_file(up_ta, "last_ta_up")
            if pf_ta is not None:
                ext = pf_ta.name.rsplit(".", 1)[-1].lower()
                parsed, err = (parse_upload_json(pf_ta) if ext == "json"
                               else parse_upload_csv(pf_ta, "ta_daily"))
                if err:
                    st.error(f"Okuma hatası: {err}")
                else:
                    updated = [k for k in ("ta_daily","assembly") if k in parsed]
                    if updated:
                        for k in updated: st.session_state.sus[k] = parsed[k]
                        st.session_state.sus = recalc_stocks(st.session_state.sus)
                        st.session_state.ta_opt_res = None
                        st.success(f"✅ TA verisi güncellendi: {', '.join(updated)}")
                        st.rerun()
                    else:
                        st.error("Geçerli TA anahtarı bulunamadı.")
        with hc3:
            st.markdown(
                '<div style="font-size:0.72rem;color:#64748b;padding-top:6px;">'
                'JSON: <code>ta_daily</code>, <code>assembly</code><br>'
                'CSV: Kart, 07.05 … 23.05</div>',
                unsafe_allow_html=True
            )
        with hc4:
            if st.button("🔬  TA'yı Optimize Et", type="primary",
                         use_container_width=True, key="btn_ta_exp"):
                with st.spinner("TA analiz ediliyor…"):
                    st.session_state.ta_opt_res = run_stage_opt(sus, "TA")
                st.rerun()

        ta_res = st.session_state.ta_opt_res

        if ta_res is None:
            _ta_ref_tab, _ta_edit_tab = st.tabs(["📋 Görüntüle", "✏️ Manuel Düzenle"])

            with _ta_ref_tab:
                st.markdown("**Günlük TA Üretim**")
                st.markdown(make_grid(sus["ta_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**🔧 Fikstür Kullanımı (gün başına)**")
                st.caption("🔴 Kırmızı = 2× fikstür sayısını aşan (kısıt ihlali) · 🟡 Sarı = limit tam (2×)")
                st.markdown(make_fixture_grid(sus["ta_fixture_usage"], sus["ta_fixture_count"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**📦 Kalan Stok — KST**")
                st.markdown(make_grid(sus["ta_rem"], "t", d_idx=DATE_INDICES), unsafe_allow_html=True)

            with _ta_edit_tab:
                st.markdown("""<div style="background:rgba(37,99,235,0.12);border:1px solid rgba(37,99,235,0.3);border-radius:10px;padding:12px 16px;margin-bottom:12px;">
                    <span style="color:#93c5fd;font-weight:700;">✏️ TA Fikstür Kullanım Düzenleme</span><br>
                    <span style="color:#cbd5e1;font-size:0.82rem;">Günlük fikstür kullanım sayısını girin. Kısıt: <code>Fikstür[c,t] ≤ 2 × N_fix[c]</code>. Üretim: <code>ta_daily = Fikstür × Adet/cycle</code></span>
                </div>""", unsafe_allow_html=True)

                # ═══ Fikstür sayısı + adet/cycle parametreleri (manuel düzenlenebilir) ═══
                with st.expander("⚙️ TA Parametreleri (Fikstür Sayısı & Adet/Cycle)", expanded=False):
                    param_df = pd.DataFrame({
                        "Kart": SUS_CARDS,
                        "Test Sistemi": [TA_TEST_SYS.get(c,"—") for c in SUS_CARDS],
                        "Fikstür Sayısı": [sus["ta_fixture_count"].get(c, TA_FIKSTUR_DEFAULT.get(c,0)) for c in SUS_CARDS],
                        "Adet/Cycle": [sus["ta_per_cycle"].get(c, TA_ADET_DEFAULT.get(c,0)) for c in SUS_CARDS],
                    })
                    edited_params = st.data_editor(
                        param_df, use_container_width=True, num_rows="fixed", key="ta_param_editor",
                        column_config={
                            "Kart": st.column_config.TextColumn("Kart", disabled=True),
                            "Test Sistemi": st.column_config.TextColumn("Test Sistemi", disabled=True),
                            "Fikstür Sayısı": st.column_config.NumberColumn("Fikstür Sayısı", min_value=0, max_value=20, step=1),
                            "Adet/Cycle": st.column_config.NumberColumn("Adet/Cycle", min_value=0, max_value=500, step=1),
                        },
                        hide_index=True,
                    )
                    pc1, pc2 = st.columns([2,4])
                    with pc1:
                        if st.button("💾 Parametreleri Kaydet", type="secondary", key="btn_save_ta_params"):
                            new_fc = {row["Kart"]: int(row["Fikstür Sayısı"]) for _, row in edited_params.iterrows()}
                            new_pc = {row["Kart"]: int(row["Adet/Cycle"])   for _, row in edited_params.iterrows()}
                            st.session_state.sus["ta_fixture_count"] = new_fc
                            st.session_state.sus["ta_per_cycle"]    = new_pc
                            # ta_daily'yi mevcut fikstür kullanımıyla yeniden hesapla
                            new_td = fixture_usage_to_ta_daily(st.session_state.sus["ta_fixture_usage"], new_pc)
                            st.session_state.sus["ta_daily"] = new_td
                            st.session_state.sus = recalc_stocks(st.session_state.sus)
                            st.success("✅ TA parametreleri kaydedildi, üretim ve stoklar yeniden hesaplandı.")
                            st.rerun()
                    with pc2:
                        if st.button("🔄 Varsayılana Sıfırla", key="btn_reset_ta_params"):
                            st.session_state.sus["ta_fixture_count"] = dict(TA_FIKSTUR_DEFAULT)
                            st.session_state.sus["ta_per_cycle"]    = dict(TA_ADET_DEFAULT)
                            new_td = fixture_usage_to_ta_daily(st.session_state.sus["ta_fixture_usage"], TA_ADET_DEFAULT)
                            st.session_state.sus["ta_daily"] = new_td
                            st.session_state.sus = recalc_stocks(st.session_state.sus)
                            st.success("✅ TA parametreleri varsayılana döndürüldü.")
                            st.rerun()

                # ═══ Fikstür kullanım editörü ═══
                st.markdown("**🔧 Günlük Fikstür Kullanım Sayıları (kart × gün):**")
                fix_data = {}
                for c in SUS_CARDS:
                    row = sus["ta_fixture_usage"].get(c, [0]*N_DAYS)
                    fix_data[c] = {f"{SUS_DAYS[i]} {SUS_DATES[i]}": int(row[i] if i < len(row) else 0) for i in range(N_DAYS)}
                df_fix = pd.DataFrame(fix_data).T
                df_fix.index.name = "Kart"
                edited_fix = st.data_editor(
                    df_fix, use_container_width=True, num_rows="fixed", key="ta_fix_editor",
                    column_config={
                        col: st.column_config.NumberColumn(col, min_value=0, max_value=30, step=1, width="small")
                        for col in df_fix.columns
                    }
                )

                ec1, ec2, _ = st.columns([2, 2, 4])
                with ec1:
                    if st.button("🔍 TA Etkisini Önizle", type="primary", use_container_width=True, key="btn_ta_preview"):
                        new_usage = {}
                        for c in SUS_CARDS:
                            rv = []
                            for i in range(N_DAYS):
                                cn = f"{SUS_DAYS[i]} {SUS_DATES[i]}"
                                rv.append(int(edited_fix.loc[c, cn]) if cn in edited_fix.columns else 0)
                            new_usage[c] = rv
                        st.session_state.ta_preview_active = True
                        st.session_state.ta_preview_usage  = new_usage
                        st.session_state.ta_preview_fcount = dict(sus["ta_fixture_count"])
                        st.session_state.ta_preview_percycle = dict(sus["ta_per_cycle"])
                        st.rerun()
                with ec2:
                    if st.session_state.ta_preview_active:
                        if st.button("✗ TA Önizleme Kapat", use_container_width=True, key="btn_ta_cancel"):
                            st.session_state.ta_preview_active = False
                            st.session_state.ta_preview_usage  = None
                            st.rerun()

                if st.session_state.ta_preview_active and st.session_state.ta_preview_usage:
                    p_use = st.session_state.ta_preview_usage
                    p_fc  = st.session_state.ta_preview_fcount  or sus["ta_fixture_count"]
                    p_pc  = st.session_state.ta_preview_percycle or sus["ta_per_cycle"]

                    # Kısıt ihlali tespiti
                    fix_viols = detect_fixture_violations(p_use, p_fc)
                    if fix_viols:
                        st.markdown(f"""<div style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.4);border-radius:10px;padding:10px 14px;margin:10px 0;">
                            <span style="color:#ef4444;font-weight:700;">⚠️ {len(fix_viols)} Fikstür Kısıt İhlali</span>
                            <span style="color:#cbd5e1;font-size:0.82rem;"> — Bu günlerde fikstür kullanımı 2× sayıyı aşıyor.</span>
                        </div>""", unsafe_allow_html=True)
                        for v in fix_viols[:10]:
                            st.markdown(f'<div style="color:#fca5a5;font-size:0.82rem;padding:2px 0 2px 14px;">• {v["card"]} Gün {v["day"]} ({v["date"]}): {v["used"]} kullanım > {v["cap"]} limit (fazla: {v["excess"]})</div>', unsafe_allow_html=True)

                    new_ta_daily = fixture_usage_to_ta_daily(p_use, p_pc)
                    preview_plan = copy.deepcopy(sus)
                    preview_plan["ta_fixture_usage"] = p_use
                    preview_plan["ta_fixture_count"] = p_fc
                    preview_plan["ta_per_cycle"]    = p_pc
                    preview_plan["ta_daily"]        = new_ta_daily
                    preview_plan = recalc_stocks(preview_plan)
                    impact = compute_manual_impact(sus, preview_plan)

                    st.write("---")
                    st.markdown("### 🔍 TA Değişiklik Etki Analizi")
                    ic1, ic2, ic3, ic4 = st.columns(4)
                    old_viol = sum(1 for c in SUS_CARDS for v in sus["ta_rem"].get(c,[]) if v<0)
                    new_viol = sum(1 for c in SUS_CARDS for v in preview_plan["ta_rem"].get(c,[]) if v<0)
                    old_total = sum(sum(v) for v in sus["ta_daily"].values())
                    new_total = sum(sum(v) for v in preview_plan["ta_daily"].values())
                    with ic1: st.metric("KST İhlal (Önce)", f"{old_viol} gün×kart")
                    with ic2: st.metric("KST İhlal (Sonra)", f"{new_viol} gün×kart", delta=f"{new_viol-old_viol:+d}", delta_color="inverse")
                    with ic3: st.metric("TA Üretim (Önce)", f"{old_total:,}")
                    with ic4: st.metric("TA Üretim (Sonra)", f"{new_total:,}", delta=f"{new_total-old_total:+,}")

                    if impact["changes"]:
                        st.markdown("**📋 KST/KSM/KSO Stok Değişimleri:**")
                        cdf = pd.DataFrame(impact["changes"])
                        cdf = cdf.rename(columns={"card":"Kart","stage":"Aşama","day":"Gün","date":"Tarih","old":"Önce","new":"Sonra","diff":"Fark","status":"Durum"})
                        cdf["Durum"] = cdf["Durum"].map({"fixed":"✅ Çözüldü","new_violation":"❌ Yeni İhlal","changed":"🔄 Değişti"})
                        st.dataframe(cdf[["Kart","Aşama","Gün","Tarih","Önce","Sonra","Fark","Durum"]], use_container_width=True, hide_index=True, height=min(400, 40+35*len(cdf)))

                    with st.expander("📈 TA Detaylı Tablolar", expanded=False):
                        st.markdown("**Yeni Fikstür Kullanımı:**")
                        st.markdown(make_fixture_grid(p_use, p_fc, d_idx=DATE_INDICES), unsafe_allow_html=True)
                        st.markdown("**Yeni TA Günlük Üretim:**")
                        st.markdown(make_grid_plan(new_ta_daily, sus["ta_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                        st.markdown("**📦 Yeni KST:**")
                        st.markdown(make_grid_plan(preview_plan["ta_rem"], sus["ta_rem"], "t", d_idx=DATE_INDICES), unsafe_allow_html=True)

                    st.write("---")
                    if st.session_state.auth:
                        if st.button("✅ TA Fikstür Kullanımını Uygula", type="primary", use_container_width=True, key="btn_ta_apply_final"):
                            st.session_state.sus = preview_plan
                            st.session_state.ta_opt_res = None
                            st.session_state.ta_preview_active = False
                            st.session_state.ta_preview_usage = None
                            st.success(f"✅ TA uygulandı! (Sicil: {st.session_state.auth_sicil})")
                            st.rerun()
                    else:
                        st.markdown("""<div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);border-radius:10px;padding:12px 16px;">
                            <span style="color:#ef4444;font-weight:700;">🔒 Yetkilendirme Gerekli</span> <span style="color:#cbd5e1;font-size:0.82rem;">— Sicil numaranızı girin.</span>
                        </div>""", unsafe_allow_html=True)
                        ap1, ap2 = st.columns([3, 1])
                        with ap1:
                            apply_sicil_ta = st.text_input("Sicil:", type="password", placeholder="Sicil numaranız", key="apply_sicil_ta", label_visibility="collapsed")
                        with ap2:
                            if st.button("🔓 TA Doğrula & Uygula", type="primary", use_container_width=True, key="apply_sicil_ta_btn"):
                                if apply_sicil_ta.strip() in YETKILI_SICILLER:
                                    st.session_state.auth = True
                                    st.session_state.auth_sicil = apply_sicil_ta.strip()
                                    st.session_state.sus = preview_plan
                                    st.session_state.ta_opt_res = None
                                    st.session_state.ta_preview_active = False
                                    st.session_state.ta_preview_usage = None
                                    st.success(f"✅ Uygulandı! (Sicil: {apply_sicil_ta.strip()})")
                                    st.rerun()
                                else:
                                    st.error("❌ Yetkisiz sicil numarası.")

        else:
            tt1, tt2 = st.tabs(["📋 Referans Plan (Mevcut)", "⚡ Optimize Sonucu"])
            np = ta_res["new_plan"]

            with tt1:
                st.markdown("**Günlük Üretim**")
                st.markdown(make_grid(sus["ta_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**📦 Kalan Stok — KST**")
                st.markdown(make_grid(sus["ta_rem"], "t", d_idx=DATE_INDICES), unsafe_allow_html=True)

            with tt2:
                st.markdown(f"**{ta_res['message']}**")
                proposals = ta_res.get("proposals", [])
                if proposals:
                    st.caption("🟩 Yeşil çerçeve = referanstan farklı hücreler")
                    st.markdown("**Günlük Üretim (Optimize)**")
                    st.markdown(make_grid_plan(np["ta_daily"], sus["ta_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                    st.markdown("**📦 Kalan Stok — KST (Optimize)**")
                    st.markdown(make_grid_plan(np["ta_rem"], sus["ta_rem"], "t", d_idx=DATE_INDICES), unsafe_allow_html=True)

                    st.markdown("---")
                    approvals_ta = {}
                    for i, p in enumerate(proposals):
                        pc1, pc2 = st.columns([7, 1])
                        with pc1:
                            st.markdown(
                                f'<div class="status-card" style="padding:8px 14px;">'
                                f'<span style="color:#a855f7;font-weight:700;">🟣 {p["card"]}</span>'
                                f' | Gün {p["day"]} ({p["date"]}) | {p["old"]:,} → <span style="color:#22c55e;">{p["new"]:,}</span>'
                                f'<br><span style="color:#64748b;font-size:0.78rem;">📌 {p["reason"]}</span></div>',
                                unsafe_allow_html=True
                            )
                        with pc2:
                            approvals_ta[i] = st.checkbox("✓", value=True, key=f"ta_appr_{i}")

                    tc1, tc2 = st.columns([2, 2])
                    with tc1:
                        if st.button("✅ Seçilen TA Değişikliklerini Uygula",
                                     type="primary", use_container_width=True, key="ta_apply_btn"):
                            applied_plan, cnt = apply_stage_proposals(proposals, sus, "TA", approvals_ta)
                            st.session_state.sus = applied_plan
                            st.session_state.ta_opt_res = None
                            st.success(f"✅ {cnt} TA değişikliği uygulandı.")
                            st.rerun()
                    with tc2:
                        if st.button("✗ İptal et", use_container_width=True, key="ta_cancel_btn"):
                            st.session_state.ta_opt_res = None
                            st.rerun()
                else:
                    st.success("✅ Mevcut TA planında ihlal yok.")
                    if st.button("Tamam", key="ta_ok_btn"):
                        st.session_state.ta_opt_res = None
                        st.rerun()


# =============  TAB 2: MONTAJ PLANI  (YENİ — talep karşılama analizi)  =====
with tab_montaj:
    st.markdown("""<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <span style="font-size:2rem;">🎯</span>
        <div><h2 style="margin:0;font-size:1.3rem;">Montaj Planı — Talep Karşılama Analizi</h2>
        <p style="color:#93c5fd;margin:0;font-size:0.8rem;">TA çıkışı montaj talebini karşılayabiliyor mu? Açıklar nereden geliyor?</p></div>
    </div>""", unsafe_allow_html=True)

    # ── Kapsama Hesabı ──
    total_demand = sum(sum(v) for v in sus["assembly"].values())
    total_ta_out = sum(sum(v) for v in sus["ta_daily"].values())
    kst_neg_cells = sum(1 for c in SUS_CARDS for v in sus["ta_rem"].get(c,[]) if v < 0)
    kst_total_cells = len(SUS_CARDS) * N_DAYS
    coverage_pct = 100.0 * (1 - kst_neg_cells / max(1, kst_total_cells))

    # Karşılanamayan toplam talep miktarı (KST'nin negatif tepe değerleri)
    uncovered = 0
    for c in SUS_CARDS:
        rem = sus["ta_rem"].get(c, [])
        if rem and min(rem) < 0:
            uncovered += abs(min(rem))

    # ── KPI Satırı ──
    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    with kc1: st.metric("Toplam Talep", f"{total_demand:,}")
    with kc2: st.metric("Toplam TA Üretim", f"{total_ta_out:,}")
    with kc3: st.metric("KST Açık Hücreleri", f"{kst_neg_cells}/{kst_total_cells}")
    with kc4: st.metric("Talep Kapsama", f"%{coverage_pct:.1f}")
    with kc5:
        if kst_neg_cells == 0:
            st.metric("Durum", "KARŞILANIYOR ✅")
        else:
            st.metric("Karşılanamayan", f"-{uncovered:,}", delta_color="inverse")
    st.write("---")

    m_ozet, m_detay, m_oncesonra = st.tabs(["📊 Özet", "🔍 Detay", "🆚 Önce/Sonra"])

    # ─── ÖZET ───
    with m_ozet:
        st.markdown("#### 🎯 Montaj Talebi (kart × gün)")
        st.markdown(make_grid(sus["assembly"], d_idx=DATE_INDICES), unsafe_allow_html=True)

        st.markdown("#### 📦 KST — Talep Karşılama Stoğu")
        st.caption("🔴 Negatif = o gün talep karşılanamıyor (TA çıkışı + başlangıç stoğu < birikimli talep)")
        st.markdown(make_grid(sus["ta_rem"], "t", d_idx=DATE_INDICES), unsafe_allow_html=True)

        # Kart-bazlı kapsama özet kartları
        st.markdown("#### 📋 Kart Bazlı Kapsama Özeti")
        rows = []
        for c in SUS_CARDS:
            dem = sum(sus["assembly"].get(c, []))
            prod = sum(sus["ta_daily"].get(c, []))
            rem = sus["ta_rem"].get(c, [])
            min_kst = min(rem) if rem else 0
            neg_days = sum(1 for v in rem if v < 0)
            durum = "✅ Tam" if neg_days == 0 else f"❌ {neg_days} gün açık"
            rows.append({"Kart": c, "Toplam Talep": dem, "Toplam TA Üretim": prod,
                         "Min KST": min_kst, "Açık Gün Sayısı": neg_days, "Durum": durum})
        coverage_df = pd.DataFrame(rows).sort_values("Açık Gün Sayısı", ascending=False)
        st.dataframe(coverage_df, use_container_width=True, hide_index=True)

    # ─── DETAY ───
    with m_detay:
        st.markdown("#### 🔍 Günlük Talep vs Karşılama")
        sel_card = st.selectbox("Kart seçin:", SUS_CARDS, key="montaj_detay_card")

        dem  = sus["assembly"].get(sel_card, [0]*N_DAYS)
        ta   = sus["ta_daily"].get(sel_card, [0]*N_DAYS)
        kst  = sus["ta_rem"].get(sel_card, [0]*N_DAYS)
        kso  = sus["otd_rem"].get(sel_card, [0]*N_DAYS)
        ksm  = sus["md_rem"].get(sel_card, [0]*N_DAYS) if PROCESS_MAP.get(sel_card) else [None]*N_DAYS

        fig = go.Figure()
        fig.add_trace(go.Bar(x=SUS_DATES, y=dem, name="Talep", marker_color="#3b82f6"))
        fig.add_trace(go.Bar(x=SUS_DATES, y=ta, name="TA Üretim", marker_color="#22c55e"))
        fig.add_trace(go.Scatter(x=SUS_DATES, y=kst, name="KST", mode="lines+markers", line=dict(color="#fbbf24", width=2)))
        fig.add_hline(y=0, line_dash="dash", line_color="red")
        fig.update_layout(template="plotly_dark", height=340, barmode="group",
                          margin=dict(l=30,r=10,t=30,b=30), paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(255,255,255,0.03)",
                          title=f"{sel_card} — Günlük Talep, TA Üretim ve KST")
        st.plotly_chart(fig, use_container_width=True)

        # Açık zinciri: KST eksiyse, KSM veya KSO de mi eksi?
        st.markdown("#### 🔗 Açık Zinciri Analizi")
        st.caption("Bir günde KST negatifse, açığın hangi aşamadan kaynaklandığını gösterir.")
        chain_rows = []
        for i in range(N_DAYS):
            if kst[i] < 0:
                kso_status = "❌ Açık" if kso[i] < 0 else "✅ OK"
                if PROCESS_MAP.get(sel_card):
                    ksm_status = "❌ Açık" if ksm[i] < 0 else "✅ OK"
                else:
                    ksm_status = "— (MD yok)"
                # Kök neden
                if kso[i] < 0:
                    kok = "OTD yetersiz"
                elif PROCESS_MAP.get(sel_card) and ksm[i] < 0:
                    kok = "MD yetersiz"
                else:
                    kok = "TA yetersiz"
                chain_rows.append({
                    "Gün": i+1, "Tarih": SUS_DATES[i], "Talep": dem[i], "TA Üretim": ta[i],
                    "KST": kst[i], "KSO": kso[i], "KSM": ksm[i] if ksm[i] is not None else "—",
                    "OTD Durum": kso_status, "MD Durum": ksm_status, "Kök Neden": kok
                })
        if chain_rows:
            st.dataframe(pd.DataFrame(chain_rows), use_container_width=True, hide_index=True)
        else:
            st.success(f"✅ {sel_card} için açık yok — talep tüm günlerde karşılanıyor.")

    # ─── ÖNCE/SONRA ───
    with m_oncesonra:
        st.markdown("#### 🆚 Optimize Öncesi/Sonrası Karşılama")
        any_opt = any([st.session_state.otd_opt_res, st.session_state.md_opt_res, st.session_state.ta_opt_res])
        if not any_opt:
            st.info("Optimize sonucu henüz yok. OTD/MD/TA aşamalarından birini optimize edin, sonra burada karşılaştırın.")
        else:
            # En son optimize edilmiş planı al
            ref_plan = sus
            opt_plan = None
            if st.session_state.ta_opt_res:  opt_plan = st.session_state.ta_opt_res["new_plan"]
            elif st.session_state.md_opt_res: opt_plan = st.session_state.md_opt_res["new_plan"]
            elif st.session_state.otd_opt_res: opt_plan = st.session_state.otd_opt_res["new_plan"]

            if opt_plan:
                old_neg = sum(1 for c in SUS_CARDS for v in ref_plan["ta_rem"].get(c,[]) if v<0)
                new_neg = sum(1 for c in SUS_CARDS for v in opt_plan["ta_rem"].get(c,[]) if v<0)
                old_cov = 100.0 * (1 - old_neg/max(1,kst_total_cells))
                new_cov = 100.0 * (1 - new_neg/max(1,kst_total_cells))

                cc1, cc2, cc3 = st.columns(3)
                with cc1: st.metric("Açık (Önce)", f"{old_neg} hücre")
                with cc2: st.metric("Açık (Sonra)", f"{new_neg} hücre", delta=f"{new_neg-old_neg:+d}", delta_color="inverse")
                with cc3: st.metric("Kapsama Değişimi", f"%{new_cov:.1f}", delta=f"{new_cov-old_cov:+.1f}")

                cmp_card = st.selectbox("Karşılaştırılacak kart:", SUS_CARDS, key="montaj_cmp_card")
                bc1, bc2 = st.columns(2)
                with bc1:
                    st.markdown("**KST — Önce**")
                    old_vals = ref_plan["ta_rem"].get(cmp_card, [0]*N_DAYS)
                    fig1 = go.Figure()
                    fig1.add_trace(go.Bar(x=SUS_DATES, y=old_vals, marker_color=["#ef4444" if v<0 else "#3b82f6" for v in old_vals]))
                    fig1.add_hline(y=0, line_dash="dash", line_color="red")
                    fig1.update_layout(template="plotly_dark", height=280, margin=dict(l=30,r=10,t=10,b=30), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.03)")
                    st.plotly_chart(fig1, use_container_width=True)
                with bc2:
                    st.markdown("**KST — Sonra**")
                    new_vals = opt_plan["ta_rem"].get(cmp_card, [0]*N_DAYS)
                    fig2 = go.Figure()
                    fig2.add_trace(go.Bar(x=SUS_DATES, y=new_vals, marker_color=["#ef4444" if v<0 else "#22c55e" for v in new_vals]))
                    fig2.add_hline(y=0, line_dash="dash", line_color="red")
                    fig2.update_layout(template="plotly_dark", height=280, margin=dict(l=30,r=10,t=10,b=30), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.03)")
                    st.plotly_chart(fig2, use_container_width=True)


# =============  TAB 2: OPTİMİZASYON  (orijinal, değişmedi)  ==========
with tab_opt:
    st.markdown("""<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <span style="font-size:2rem;">🚀</span>
        <div><h2 style="margin:0;font-size:1.3rem;">Üretim Planı Optimizasyonu</h2>
        <p style="color:#93c5fd;margin:0;font-size:0.8rem;">Mevcut planı analiz et → İhlalleri tespit et → Düzeltme öner → Onay al</p></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("#### 📊 Mevcut Plan Durumu")
    viol_cards = set()
    for c in SUS_CARDS:
        for rk in ["otd_rem","md_rem","ta_rem"]:
            if rk=="md_rem" and not PROCESS_MAP.get(c): continue
            if any(v<0 for v in sus[rk].get(c,[])):
                viol_cards.add(c)

    if not viol_cards:
        st.success("✅ Mevcut plan fizibil — tüm tampon stoklar pozitif. İyileştirme önerileri için optimize edin.")
    else:
        st.error(f"⚠️ {len(viol_cards)} kartta stok ihlali var: **{', '.join(sorted(viol_cards))}**")

    st.write("---")

    if st.button("🚀 OPTİMİZE ET — Planı Analiz Et ve Düzelt", type="primary", use_container_width=True):
        with st.spinner("Plan analiz ediliyor ve optimizasyon çalıştırılıyor..."):
            result = run_optimization(sus)
            st.session_state.opt_result = result

    opt = st.session_state.opt_result
    if opt:
        if opt["status"] == "feasible":
            st.success(f"✅ {opt['message']}")
        elif opt["status"] == "optimal":
            st.success(f"✅ {opt['message']}")
        else:
            st.warning(f"⚠️ {opt['message']}")

        proposals = opt.get("proposals", [])
        if proposals:
            st.markdown("#### 📋 Değişiklik Önerileri")
            st.caption("Her öneriyi inceleyip onaylayabilir veya reddedebilirsiniz.")
            approvals = {}
            for i, p in enumerate(proposals):
                col1, col2 = st.columns([5, 1])
                with col1:
                    icon = "🟢" if p["type"].startswith("OTD") else "🔵" if p["type"].startswith("MD") else "🟣"
                    st.markdown(f"""<div class="status-card">
                        <div style="color:#fff;font-weight:600;font-size:0.9rem;">{icon} {p['type']} — {p['card']} | Gün {p['day']} ({p['date']}) | Hat: {p.get('line','—')}</div>
                        <div style="color:#93c5fd;font-size:0.82rem;margin-top:4px;">📌 Sebep: {p['reason']}</div>
                        <div style="color:#cbd5e1;font-size:0.82rem;">Değişiklik: <span style="color:#ef4444;">{p['old']:,}</span> → <span style="color:#22c55e;">{p['new']:,}</span> ({p['impact']})</div>
                    </div>""", unsafe_allow_html=True)
                with col2:
                    approvals[i] = st.checkbox("Onayla", value=True, key=f"appr_{i}")

            st.write("---")
            if st.button("✅ Onaylanan Değişiklikleri Uygula", type="primary", use_container_width=True):
                applied = copy.deepcopy(sus)
                applied_count = 0
                for i, p in enumerate(proposals):
                    if approvals.get(i, False):
                        c_k, d_k = p["card"], p["day"]-1
                        if p["type"].startswith("OTD"):
                            applied["otd_daily"][c_k][d_k] = p["new"]
                            if p.get("line"):
                                alloc = applied["otd_alloc"].get(p["line"], [""]*N_DAYS)
                                if d_k < len(alloc): alloc[d_k] = c_k
                        elif p["type"].startswith("MD"):
                            applied["md_daily"][c_k][d_k] = p["new"]
                        applied_count += 1
                applied = recalc_stocks(applied)
                st.session_state.sus = applied
                st.session_state.opt_result = None
                st.success(f"✅ {applied_count} değişiklik uygulandı. Stoklar yeniden hesaplandı.")
                st.rerun()

        suggestions = opt.get("suggestions", [])
        if suggestions:
            st.markdown("#### 💡 Tavsiyeler")
            for s in suggestions:
                if s.startswith("✅") or s.startswith("📈"):
                    st.markdown(f'<div style="color:#22c55e;font-size:0.9rem;padding:4px 0;">{s}</div>', unsafe_allow_html=True)
                elif s.startswith("•"):
                    st.markdown(f'<div style="color:#f59e0b;font-size:0.85rem;padding:2px 0 2px 16px;">{s}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="color:#cbd5e1;font-size:0.88rem;padding:4px 0;">{s}</div>', unsafe_allow_html=True)

        if proposals and opt.get("new_plan"):
            with st.expander("📊 Önce / Sonra Karşılaştırması"):
                compare_card = st.selectbox("Kart seç:", sorted(viol_cards) if viol_cards else SUS_CARDS, key="cmp_card")
                if compare_card:
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        st.markdown("**Mevcut KSO:**")
                        old_vals = sus["otd_rem"].get(compare_card, [0]*N_DAYS)
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=SUS_DATES, y=old_vals, name="Mevcut", marker_color=["#ef4444" if v<0 else "#3b82f6" for v in old_vals]))
                        fig.add_hline(y=0, line_dash="dash", line_color="red")
                        fig.update_layout(template="plotly_dark",height=280,margin=dict(l=30,r=10,t=10,b=30),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(255,255,255,0.03)")
                        st.plotly_chart(fig, use_container_width=True)
                    with bc2:
                        st.markdown("**Optimize KSO:**")
                        new_vals = opt["new_plan"]["otd_rem"].get(compare_card, [0]*N_DAYS)
                        fig2 = go.Figure()
                        fig2.add_trace(go.Bar(x=SUS_DATES, y=new_vals, name="Optimize", marker_color=["#ef4444" if v<0 else "#22c55e" for v in new_vals]))
                        fig2.add_hline(y=0, line_dash="dash", line_color="red")
                        fig2.update_layout(template="plotly_dark",height=280,margin=dict(l=30,r=10,t=10,b=30),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(255,255,255,0.03)")
                        st.plotly_chart(fig2, use_container_width=True)


# =============  TAB 3: RAPOR & GEÇİŞLER  (orijinal, değişmedi)  =======
with tab_rapor:
    st.markdown("### 📑 Rapor & Aşamalar Arası Geçişler")

    st.subheader("🔄 Kart Bazında OTD → MD → TA Geçiş Özeti")
    trans = []
    for c in SUS_CARDS:
        ot=sum(sus["otd_daily"].get(c,[])); mt=sum(sus["md_daily"].get(c,[])); tt=sum(sus["ta_daily"].get(c,[]))
        at=sum(sus["assembly"].get(c,[])); si=sus["init"].get(c,{})
        denge = tt + si.get("t",0) - at
        trans.append({"Kart":c,"MD?":"Evet" if PROCESS_MAP.get(c) else "—","OTD Ürt.":ot,"OTD₀":si.get("o",0),"MD Ürt.":mt if PROCESS_MAP.get(c) else 0,"MD₀":si.get("m",0) if PROCESS_MAP.get(c) else 0,"TA Ürt.":tt,"TA₀":si.get("t",0),"Montaj":at,"Denge":denge})
    df_t = pd.DataFrame(trans)
    def sd(val):
        if isinstance(val,(int,float)) and val<0: return "background:rgba(239,68,68,0.3);color:#ef4444;font-weight:700"
        return ""
    try: st.dataframe(df_t.style.map(sd,subset=["Denge"]).format({k:"{:,.0f}" for k in ["OTD Ürt.","OTD₀","MD Ürt.","MD₀","TA Ürt.","TA₀","Montaj","Denge"]}), use_container_width=True, hide_index=True, height=540)
    except: st.dataframe(df_t.style.applymap(sd,subset=["Denge"]).format({k:"{:,.0f}" for k in ["OTD Ürt.","OTD₀","MD Ürt.","MD₀","TA Ürt.","TA₀","Montaj","Denge"]}), use_container_width=True, hide_index=True, height=540)

    st.write("---")
    st.subheader("🚨 Tüm Stok İhlalleri")
    viols = []
    for sn,rk,sl in [("OTD","otd_rem","KSO"),("MD","md_rem","KSM"),("TA","ta_rem","KST")]:
        for c in SUS_CARDS:
            if rk=="md_rem" and not PROCESS_MAP.get(c): continue
            for i,v in enumerate(sus[rk].get(c,[])):
                if v<0: viols.append({"Kart":c,"Aşama":sl,"Gün":i+1,"Tarih":SUS_DATES[i],"Açık":v})
    if viols:
        st.dataframe(pd.DataFrame(viols), use_container_width=True, hide_index=True, height=min(500,40+35*len(viols)))
    else:
        st.success("Stok ihlali yok ✅")


# =============  TAB 4: VERİ YÖNETİMİ  (orijinal, değişmedi)  ==========
with tab_veri:
    st.subheader("⚙️ Veri Yönetimi")
    st.caption("Stok güncelleme, TA fikstür girişi, Excel yükleme — yetkili personel ile.")

    if not st.session_state.auth:
        st.markdown('<div class="status-card status-yellow"><p style="color:#f59e0b;margin:0 0 8px;font-weight:600;">🔒 Yetkili girişi gerekli</p><p style="color:#cbd5e1;margin:0;font-size:0.85rem;">Veri değişikliği için sicil numaranızı girin.</p></div>', unsafe_allow_html=True)
        pw1,pw2 = st.columns([3,1])
        with pw1: sicil = st.text_input("Sicil No:", type="password", label_visibility="collapsed", placeholder="Sicil numaranız")
        with pw2:
            if st.button("Giriş Yap", use_container_width=True):
                if sicil.strip() in YETKILI_SICILLER:
                    st.session_state.auth = True; st.session_state.auth_sicil = sicil.strip(); st.rerun()
                else: st.error("Yetkisiz sicil.")
    else:
        st.success(f"🔓 Giriş: Sicil {st.session_state.auth_sicil}")
        if st.button("Oturumu Kapat", type="secondary"):
            st.session_state.auth = False; st.session_state.auth_sicil = None; st.rerun()
        st.write("---")

        veri_modu = st.radio("İşlem:", ["📦 Stok Güncelle", "🔬 TA Fikstür Güncelle", "📄 Excel Yükle", "🔄 Varsayılana Dön"], horizontal=True)

        if veri_modu == "📦 Stok Güncelle":
            st.caption("Başlangıç stoklarını güncelleyin (OTD / MD / TA).")
            edit_card = st.selectbox("Kart:", SUS_CARDS, key="stk_card")
            si = sus["init"].get(edit_card, {})
            ec1,ec2,ec3 = st.columns(3)
            with ec1: new_o = st.number_input("OTD Stok₀", value=si.get("o",0), step=10, key="no")
            with ec2: new_m = st.number_input("MD Stok₀",  value=si.get("m",0), step=10, key="nm")
            with ec3: new_t = st.number_input("TA Stok₀",  value=si.get("t",0), step=10, key="nt")
            if st.button("💾 Stoğu Kaydet ve Yeniden Hesapla", type="primary"):
                sus["init"][edit_card] = {"o":new_o,"m":new_m,"t":new_t}
                st.session_state.sus = recalc_stocks(sus)
                st.success(f"{edit_card} stokları güncellendi, tampon stoklar yeniden hesaplandı.")
                st.rerun()

        elif veri_modu == "🔬 TA Fikstür Güncelle":
            st.caption("TA üretim miktarlarını güncelleyin.")
            ta_card = st.selectbox("Kart:", SUS_CARDS, key="ta_card")
            st.markdown(f"**Mevcut TA Üretim — {ta_card}:**")
            current = sus["ta_daily"].get(ta_card, [0]*N_DAYS)
            cols = st.columns(14)
            new_ta = []
            for i, col in enumerate(cols):
                with col:
                    new_ta.append(col.number_input(f"{SUS_DATES[i]}", value=current[i], step=10, key=f"ta_{ta_card}_{i}", label_visibility="collapsed"))
            if st.button("💾 TA Üretimi Kaydet ve Yeniden Hesapla", type="primary"):
                sus["ta_daily"][ta_card] = new_ta
                st.session_state.sus = recalc_stocks(sus)
                st.success(f"{ta_card} TA üretimi güncellendi.")
                st.rerun()

        elif veri_modu == "📄 Excel Yükle":
            st.caption("Stok verisi içeren CSV/Excel yükleyin (Kart, OTD Stok, MD Stok, TA Stok sütunları).")
            up = st.file_uploader("Dosya seç:", type=["csv","xlsx"], key="stk_up")
            if up:
                try:
                    if up.name.endswith(".csv"): df_up = pd.read_csv(up)
                    else: df_up = pd.read_excel(up)
                    st.dataframe(df_up, use_container_width=True, hide_index=True)
                    if st.button("✅ Uygula", type="primary"):
                        for _, row in df_up.iterrows():
                            c_k = str(row.iloc[0]).strip()
                            if c_k in SUS_CARDS:
                                sus["init"][c_k] = {"o":int(row.iloc[1]),"m":int(row.iloc[2]),"t":int(row.iloc[3])}
                        st.session_state.sus = recalc_stocks(sus)
                        st.success("Stoklar yüklendi ve yeniden hesaplandı.")
                        st.rerun()
                except Exception as e: st.error(f"Hata: {e}")

        elif veri_modu == "🔄 Varsayılana Dön":
            st.warning("Tüm değişiklikleri sıfırlayıp orijinal Excel verisine dönülecek.")
            if st.button("🔄 Varsayılana Dön", type="primary"):
                st.session_state.sus = get_default_sus()
                st.session_state.opt_result = None
                st.session_state.otd_opt_res = None
                st.session_state.md_opt_res  = None
                st.session_state.ta_opt_res  = None
                st.session_state.manual_edit_alloc = None
                st.session_state.manual_edit_before = None
                st.session_state.manual_impact = None
                st.session_state.preview_active = False
                st.session_state.preview_alloc = None
                st.session_state.preview_rates = None
                st.session_state.preview_setups = None
                st.session_state.dyn_dates = list(_DEFAULT_DATES)
                st.session_state.dyn_days  = list(_DEFAULT_DAYS)
                st.session_state.date_start_idx = 0
                st.session_state.date_end_idx = 13
                st.success("Tüm veriler varsayılana döndürüldü.")
                st.rerun()
