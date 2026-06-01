import streamlit as st
import pandas as pd
import json, base64, os, copy
import plotly.graph_objects as go

# =====================================================================
# SAYFA YAPILANDIRMASI
# =====================================================================
st.set_page_config(page_title="Beko Çerkezköy — Şasi Montaj Planlaması", page_icon="📺", layout="wide")

# =====================================================================
# SABİTLER
# =====================================================================
YETKILI_SICILLER = {"26127996"}

KART_RENKLERI = {
    "F4":"#FFB3BA","GB":"#A8E6CF","GL":"#B3D4FF","GX":"#FFFACD","LG":"#D9B3FF",
    "MR":"#FFCBA4","V1":"#B5EAD7","XC":"#C3B1E1","XD":"#FFE0B2","XGB":"#81D4FA",
    "XGS":"#80CBC4","XR":"#F48FB1","Y3":"#C5E1A5","Y4":"#FFCCBC",
}

SUS_DATES = ["07.05","08.05","09.05","11.05","12.05","13.05","14.05","15.05","16.05","18.05","20.05","21.05","22.05","23.05"]
SUS_DAYS  = ["Perş","Cum","Cmt","Pzt","Sal","Çar","Perş","Cum","Cmt","Pzt","Çar","Perş","Cum","Cmt"]
SUS_CARDS = ["F4","GB","GL","GX","LG","MR","V1","XC","XD","XGB","XGS","XR","Y3","Y4"]
PROCESS_MAP = {"F4":True,"GB":True,"GL":True,"GX":False,"LG":False,"MR":True,"V1":True,"XC":False,"XD":False,"XGB":True,"XGS":True,"XR":False,"Y3":True,"Y4":True}

# Hat kapasiteleri (Tempolar verisinden)
TEMPO = {
    "OD0":{"F4":100,"GX":800,"V1":1000,"XGB":927,"XGS":1040,"Y3":880,"Y4":850},
    "OD2":{"F4":200,"GX":700,"LG":450,"V1":1150,"XC":1140,"XD":770,"XGB":880,"XGS":1000,"XR":610,"Y3":920,"Y4":850},
    "OD3":{"V1":1150,"XC":1140,"XD":770,"XGB":880,"XGS":1000,"XR":610,"Y3":920,"Y4":850},
    "OD4":{"F4":500,"LG":550,"V1":0,"XGB":700,"XGS":750},
    "OD6":{"F4":400,"GB":700,"GL":750,"Y3":870,"Y4":750},
}
MD_TEMPO = {"MD1":{"XGS":1100,"XGB":950,"Y4":1000,"F4":0,"GB":800,"GL":780,"MR":600,"V1":1000,"Y3":890},
            "MD2":{"XGS":1100,"XGB":950,"Y4":1000,"F4":0,"GB":800,"GL":780,"MR":600,"V1":1000,"Y3":890}}

# =====================================================================
# VARSAYILAN SUS VERİSİ (session state'e yüklenir)
# =====================================================================
def get_default_sus():
    return {
        "otd_alloc":{"OD0":["XGS","XGS","XGB","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","XGS","",""],"OD2":["XGB","LG","LG","LG","XC","XGS","LG","LG","LG","LG","XGS","XGS","XGS","XGS"],"OD3":["XC","XC","XR","XR","XR","XR","XR","XR","XR","XC","XC","","",""],"OD4":["LG","LG","LG","LG","LG","LG","LG","LG","LG","","","","",""],"OD6":["Y4","Y4","","","","","","","","","","","",""]},
        "otd_rates":{"OD0":[1,1,1,1,1,1,1,1,1,1,1,1,1,1],"OD2":[1,.3,.7,1,.5,1,1,1,1,1,1,1,1,1],"OD3":[1,1,1,1,1,1,1,1,1,1,1,1,1,1],"OD4":[1,1,.5,1,1,1,.5,1,1,1,.5,1,1,1],"OD6":[1,1,1,1,1,1,1,1,1,1,1,1,1,1]},
        "otd_daily":{"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[550,685,590,1000,550,550,725,1000,1000,450,0,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[1140,1140,0,0,570,0,0,0,0,1140,1140,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[880,0,927,0,0,0,0,0,0,0,0,0,0,0],"XGS":[1040,1040,0,1040,1040,2040,1040,1040,1040,1040,2040,2040,1000,1000],"XR":[0,0,610,610,610,610,610,610,610,0,0,0,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y4":[750,750,0,0,0,0,0,0,0,0,0,0,0,0]},
        "otd_rem":{"F4":[238,238,238,238,238,238,238,238,238,238,238,238,238,238],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[200,200,200,200,200,200,200,200,200,200,200,200,200,200],"LG":[-107,-207,-172,-232,118,18,-82,-137,83,303,-27,-27,-27,-27],"MR":[108,108,108,108,108,108,108,108,108,108,108,108,108,108],"V1":[400,400,400,400,400,400,400,400,400,400,400,400,400,400],"XC":[654,634,614,-546,-1126,-556,-556,-556,-556,-556,584,1724,1724,1724],"XD":[1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069,1069],"XGB":[206,611,136,588,588,588,588,588,588,588,588,588,588,588],"XGS":[955,895,835,-265,-325,-385,555,-605,-1765,-2925,-2985,-2045,-1105,-205],"XR":[380,150,-80,70,220,370,520,670,820,970,510,50,50,50],"Y3":[38,38,38,38,38,38,38,38,38,38,38,38,38,38],"Y4":[910,1160,1410,910,410,410,410,410,410,410,410,410,410,410]},
        "md_alloc":{"MD1":[["XGS"]*14],"MD2":[["XGB","XGB","XGB","XGB","","","","XGS","XGS","XGS","","","",""],["Y4","Y4","Y4","Y4","Y4","","","","","","","","",""]]},
        "md_daily":{"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[475,475,475,475,0,0,0,0,0,0,0,0,0,0],"XGS":[1100,1100,1100,1100,1100,1100,1100,2200,2200,2200,1100,1100,1100,1100],"XR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y4":[500,500,500,500,500,0,0,0,0,0,0,0,0,0]},
        "md_rem":{"F4":[28,28,28,28,28,28,28,28,28,28,28,28,28,28],"GB":[1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188,1188],"GL":[644,644,644,644,644,644,644,644,644,644,644,644,644,644],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"MR":[347,347,347,347,347,347,347,347,347,347,347,347,347,347],"V1":[27,27,27,27,27,27,27,27,27,27,27,27,27,27],"XC":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[-241,-594,-947,-1300,-825,-825,-825,-825,-825,-825,-1653,-1653,-1653,-1653],"XGS":[-717,-737,-477,-217,43,-257,-557,-857,-57,743,1543,1243,943,3143],"XR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y3":[24,24,24,24,24,24,24,24,24,24,24,24,24,24],"Y4":[-74,112,141,13,-115,-243,-871,-871,-871,-871,-871,-871,-871,-871]},
        "ta_daily":{"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"LG":[650,650,650,650,650,650,650,780,780,780,780,0,0,0],"MR":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"V1":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[1160,1160,1160,1160,580,0,0,0,0,0,0,0,0,0],"XD":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"XGB":[828,828,828,828,0,0,0,0,0,0,828,0,0,0],"XGS":[840,1120,840,840,840,1400,1400,1400,1400,1400,1400,1400,1400,0],"XR":[0,230,230,460,460,460,460,460,460,460,460,460,0,0],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"Y4":[628,314,471,628,628,628,628,0,0,0,0,0,0,0]},
        "ta_rem":{"F4":[349,349,349,349,349,349,349,349,349,349,349,349,349,349],"GB":[575,575,575,575,575,-90,-90,-90,-90,-90,-90,-90,-90,-90],"GL":[416,416,416,416,416,416,416,416,416,416,416,416,416,416],"GX":[667,667,667,117,117,117,-180,-180,-180,-180,-180,-180,-180,-180],"LG":[421,821,1421,1520,1220,369,-231,-729,-1092,-1313,-734,21,21,-5],"MR":[308,308,308,308,308,308,308,-45,-96,-96,-96,-96,-96,-96],"V1":[-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9,-9],"XC":[1166,926,746,1156,1886,2466,2466,2466,2466,2466,2268,2268,1769,1282],"XD":[225,123,123,119,119,119,119,119,119,119,119,-616,-990,-1215],"XGB":[458,21,-237,-9,819,819,818,818,818,818,818,806,463,183],"XGS":[610,200,321,861,1701,2080,2534,2876,3076,1691,507,636,823,1380],"XR":[508,508,523,753,268,255,248,100,60,520,741,793,992,491],"Y3":[157,157,157,157,157,157,157,157,157,157,157,157,157,50],"Y4":[-99,529,843,214,-58,62,690,1318,1318,1318,1318,1318,1318,1318]},
        "assembly":{"F4":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GB":[0,0,0,0,0,665,0,0,0,0,0,0,0,0],"GL":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"GX":[0,0,0,550,0,0,297,0,0,0,0,0,0,0],"LG":[279,250,50,551,950,1501,1250,1148,1143,1001,201,25,0,26],"MR":[0,0,0,0,0,0,0,353,51,0,0,0,0,0],"V1":[258,0,0,0,0,0,0,0,0,0,0,0,0,0],"XC":[618,1400,1340,750,430,0,0,0,0,0,198,0,499,487],"XD":[625,102,0,4,0,0,0,0,0,0,0,735,374,225],"XGB":[205,1265,1086,600,0,0,1,0,0,0,0,840,343,280],"XGS":[1681,1250,999,300,0,461,946,1058,1200,2785,2584,1271,1213,843],"XR":[2,0,215,0,945,473,467,608,500,0,239,408,261,501],"Y3":[0,0,0,0,0,0,0,0,0,0,0,0,0,107],"Y4":[881,0,0,1100,900,508,0,0,0,0,0,0,0,0]},
        "init":{"F4":{"o":238,"m":28,"t":349},"GB":{"o":0,"m":1188,"t":575},"GL":{"o":0,"m":644,"t":416},"GX":{"o":200,"m":60,"t":667},"LG":{"o":543,"m":257,"t":700},"MR":{"o":108,"m":347,"t":308},"V1":{"o":400,"m":27,"t":249},"XC":{"o":1814,"m":57,"t":1784},"XD":{"o":1069,"m":12,"t":850},"XGB":{"o":681,"m":587,"t":663},"XGS":{"o":2055,"m":123,"t":2291},"XR":{"o":380,"m":6,"t":510},"Y3":{"o":38,"m":24,"t":157},"Y4":{"o":1410,"m":554,"t":782}},
    }

if "sus" not in st.session_state:
    st.session_state.sus = get_default_sus()
if "opt_result" not in st.session_state:
    st.session_state.opt_result = None
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.auth_sicil = None

sus = st.session_state.sus

# =====================================================================
# OPTİMİZASYON MOTORU
# =====================================================================
def recalc_stocks(plan):
    """Üretim planından tampon stokları yeniden hesaplar."""
    p = copy.deepcopy(plan)
    init = p["init"]
    # KSO: OTD stok = init_o + cum_otd_production - cum_downstream_demand
    # Basitleştirilmiş: OTD çıkış stoğu = önceki stok + bugünkü OTD üretim - bugünkü (MD veya TA) tüketim
    for c in SUS_CARDS:
        # OTD kalan stok yeniden hesapla
        otd = p["otd_daily"].get(c, [0]*14)
        asm = p["assembly"].get(c, [0]*14)
        md = p["md_daily"].get(c, [0]*14)
        ta = p["ta_daily"].get(c, [0]*14)
        needs_md = PROCESS_MAP.get(c, False)

        # KSO: OTD buffer = init_otd + cumOTD - cumDownstream(MD if needs_md else TA)
        cum_otd = 0
        cum_down = 0  # downstream = MD daily if needs_md else TA daily
        otd_rem = []
        for i in range(14):
            cum_otd += otd[i]
            cum_down += (md[i] if needs_md else ta[i])
            otd_rem.append(init.get(c,{}).get("o",0) + cum_otd - cum_down)
        p["otd_rem"][c] = otd_rem

        # KSM: MD buffer (only for MD cards)
        if needs_md:
            cum_md = 0
            cum_ta_d = 0
            md_rem = []
            for i in range(14):
                cum_md += md[i]
                cum_ta_d += ta[i]
                md_rem.append(init.get(c,{}).get("m",0) + cum_md - cum_ta_d)
            p["md_rem"][c] = md_rem

        # KST: TA buffer
        cum_ta = 0
        cum_asm = 0
        ta_rem = []
        for i in range(14):
            cum_ta += ta[i]
            cum_asm += asm[i]
            ta_rem.append(init.get(c,{}).get("t",0) + cum_ta - cum_asm)
        p["ta_rem"][c] = ta_rem
    return p

def run_optimization(current_plan):
    """Mevcut planı analiz eder, ihlalleri tespit eder, düzeltme önerileri üretir."""
    plan = copy.deepcopy(current_plan)
    proposals = []
    # Adım 1: Tüm negatif stokları bul
    violations = []
    for stage, rem_key, stage_label in [("OTD","otd_rem","KSO"),("MD","md_rem","KSM"),("TA","ta_rem","KST")]:
        for c in SUS_CARDS:
            if stage == "MD" and not PROCESS_MAP.get(c): continue
            rem = plan[rem_key].get(c, [0]*14)
            for i, v in enumerate(rem):
                if v < 0:
                    violations.append({"card":c,"stage":stage,"day":i,"deficit":abs(v),"rem_key":rem_key,"label":stage_label})

    if not violations:
        return {"status":"optimal","proposals":[],"message":"Plan zaten fizibil — tüm tampon stoklar pozitif!","new_plan":plan}

    # Adım 2: Her ihlal için düzeltme önerisi üret
    applied = copy.deepcopy(plan)
    for v in sorted(violations, key=lambda x: (x["day"], -x["deficit"])):
        c, stage, day, deficit = v["card"], v["stage"], v["day"], v["deficit"]
        # Mevcut stok negatif — üretimi artırarak düzeltmeye çalış
        if stage == "OTD":
            # Boş hat bul veya mevcut hatta ek kapasite var mı kontrol et
            alloc = applied["otd_alloc"]
            for d in range(max(0, day-2), day+1):  # 2 gün öncesinden başla
                for line in ["OD0","OD2","OD3","OD4","OD6"]:
                    line_alloc = alloc.get(line, [""]*14)
                    if d < len(line_alloc) and line_alloc[d] == "":
                        cap = TEMPO.get(line, {}).get(c, 0)
                        if cap > 0:
                            old_val = applied["otd_daily"][c][d]
                            add = min(cap, deficit)
                            proposals.append({
                                "type":"OTD üretim ekle","card":c,"day":d+1,"date":SUS_DATES[d],
                                "line":line,"old":old_val,"new":old_val+add,
                                "reason":f"{c} KSO Gün {day+1}'de −{deficit:,} açık",
                                "impact":f"+{add:,} adet üretim"
                            })
                            applied["otd_daily"][c][d] += add
                            line_alloc[d] = c
                            deficit -= add
                            if deficit <= 0: break
                    if deficit <= 0: break
                if deficit <= 0: break

        elif stage == "MD":
            # MD'de boş slot bul
            for d in range(max(0, day-2), day+1):
                for line in ["MD1","MD2"]:
                    rows = applied["md_alloc"].get(line, [])
                    for row in rows:
                        if d < len(row) and row[d] == "":
                            cap = MD_TEMPO.get(line,{}).get(c, 0)
                            if cap > 0:
                                old_val = applied["md_daily"][c][d]
                                add = min(cap, deficit)
                                proposals.append({
                                    "type":"MD üretim ekle","card":c,"day":d+1,"date":SUS_DATES[d],
                                    "line":line,"old":old_val,"new":old_val+add,
                                    "reason":f"{c} KSM Gün {day+1}'de −{deficit:,} açık",
                                    "impact":f"+{add:,} adet MD üretim"
                                })
                                applied["md_daily"][c][d] += add
                                row[d] = c
                                deficit -= add
                                if deficit <= 0: break
                        if deficit <= 0: break
                    if deficit <= 0: break
                if deficit <= 0: break

    # Stokları yeniden hesapla
    applied = recalc_stocks(applied)

    # Kalan ihlalleri kontrol et
    remaining = 0
    for c in SUS_CARDS:
        for rem_key in ["otd_rem","md_rem","ta_rem"]:
            if rem_key == "md_rem" and not PROCESS_MAP.get(c): continue
            remaining += sum(1 for v in applied[rem_key].get(c,[]) if v < 0)

    suggestions = []
    if remaining > 0:
        suggestions.append("Tüm ihlaller otomatik çözülemedi — aşağıdaki öneriler uygulanabilir:")
        # Kalan ihlalleri analiz et
        for c in SUS_CARDS:
            for rem_key, label in [("otd_rem","OTD"),("md_rem","MD"),("ta_rem","TA")]:
                if rem_key == "md_rem" and not PROCESS_MAP.get(c): continue
                negs = [(i,v) for i,v in enumerate(applied[rem_key].get(c,[])) if v < 0]
                if negs:
                    worst_day, worst_val = min(negs, key=lambda x: x[1])
                    suggestions.append(f"• {c} {label}: Gün {worst_day+1}'de {worst_val:,} açık — mesai veya hat eklenmesi gerekli")
    else:
        suggestions.append("✅ Tüm öneriler uygulandığında plan tamamen fizibil hale gelir.")
        # İyileştirme önerileri
        suggestions.append("📈 Daha iyi hale getirmek için:")
        # En düşük stoklu kartları bul
        for c in SUS_CARDS:
            min_ta = min(applied["ta_rem"].get(c,[999]))
            if 0 <= min_ta < 200:
                suggestions.append(f"• {c} TA stoğu minimum {min_ta} — güvenlik marjı düşük, TA fikstür artışı düşünülebilir")

    status = "feasible" if remaining == 0 else "partial"
    return {"status":status,"proposals":proposals,"new_plan":applied,
            "remaining_violations":remaining,"suggestions":suggestions,
            "message":"Plan optimize edildi!" if remaining==0 else f"{remaining} ihlal kaldı — ek müdahale gerekli"}


# =====================================================================
# CSS
# =====================================================================
bg_css = ""
for img_name in ["aaa.jpg","aaa.jpeg","aaa.png"]:
    if os.path.exists(img_name):
        with open(img_name,"rb") as f: bg_b64 = base64.b64encode(f.read()).decode()
        bg_css = f".stApp{{background:linear-gradient(rgba(0,20,60,0.88),rgba(0,10,40,0.92)),url('data:image/jpeg;base64,{bg_b64}');background-size:cover;background-position:center;background-attachment:fixed;}}"
        break
logo_b64 = ""
for ln in ["pngwing.com.png","pngwing_com.png","logo.png"]:
    if os.path.exists(ln):
        with open(ln,"rb") as f: logo_b64 = base64.b64encode(f.read()).decode()
        break

st.markdown(f"""<style>
    {bg_css}
    footer{{visibility:hidden!important;}}
    header[data-testid="stHeader"]{{background:rgba(0,20,60,0.95)!important;backdrop-filter:blur(10px);}}
    @keyframes fadeSlideIn{{from{{opacity:0;transform:translateY(12px);}}to{{opacity:1;transform:translateY(0);}}}}
    .block-container{{max-width:1300px;animation:fadeSlideIn 0.5s ease-out;}}
    .stTabs [data-baseweb="tab-panel"]{{animation:fadeSlideIn 0.35s ease-out;}}
    section[data-testid="stSidebar"]{{background:rgba(0,15,45,0.95)!important;}}
    section[data-testid="stSidebar"] .stSelectbox label,section[data-testid="stSidebar"] h2{{color:#fff!important;}}
    div[data-testid="stMetric"]{{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:16px;backdrop-filter:blur(10px);}}
    div[data-testid="stMetric"] label{{color:#93c5fd!important;}}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"]{{color:#fff!important;}}
    .stTabs [data-baseweb="tab-list"]{{gap:8px;}}
    .stTabs [data-baseweb="tab"]{{background:rgba(255,255,255,0.05);border-radius:8px;color:#93c5fd;}}
    .stTabs [aria-selected="true"]{{background:#2563eb!important;color:#fff!important;}}
    h1,h2,h3{{color:#fff!important;}}
    .stCaption{{color:#cbd5e1!important;}}
    hr{{border-color:rgba(255,255,255,0.1)!important;}}
    .otd-table{{width:100%;border-collapse:separate;border-spacing:3px;font-family:'Segoe UI',sans-serif;}}
    .otd-table th{{background:rgba(37,99,235,0.3);color:#93c5fd;padding:8px 5px;font-size:0.75rem;font-weight:600;text-align:center;border-radius:6px;}}
    .otd-table td{{padding:7px 5px;text-align:center;font-weight:700;font-size:0.78rem;border-radius:6px;color:#1e293b;}}
    .otd-rh{{background:rgba(0,0,0,0.35)!important;color:#93c5fd!important;font-weight:700;text-align:left!important;padding-left:10px!important;min-width:48px;}}
    .otd-none{{background:rgba(255,255,255,0.04)!important;color:#475569!important;font-weight:400;}}
    .status-card{{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:16px;margin-bottom:8px;}}
    .status-green{{border-left:4px solid #22c55e;}} .status-yellow{{border-left:4px solid #f59e0b;}} .status-red{{border-left:4px solid #ef4444;}}
    .big-num{{font-size:1.6rem;font-weight:800;color:#fff;line-height:1.1;}}
    .big-label{{font-size:0.72rem;color:#93c5fd;margin-top:2px;}}
</style>""", unsafe_allow_html=True)


# =====================================================================
# TABLO FONKSİYONLARI
# =====================================================================
def make_grid(card_data, init_key=None):
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Kart</th>'
    if init_key: h += '<th>Stok₀</th>'
    for i in range(14): h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    tot = [0]*14
    for c in SUS_CARDS:
        vals = card_data.get(c, [0]*14)
        bg = KART_RENKLERI.get(c,"#888")
        h += f'<tr><td style="background:{bg};color:#1e293b;font-weight:700;text-align:left;padding-left:8px;border-radius:6px;">{c}</td>'
        if init_key:
            iv = sus["init"].get(c,{}).get(init_key,0)
            h += f'<td style="color:#93c5fd;font-weight:600;">{iv:,}</td>'
        for i,v in enumerate(vals):
            tot[i] += v
            if v < 0: h += f'<td style="background:rgba(239,68,68,0.25);color:#ef4444;font-weight:700;">{v:,}</td>'
            elif v == 0: h += '<td style="color:#475569;">—</td>'
            else: h += f'<td style="color:#fff;">{v:,}</td>'
        h += '</tr>'
    h += '<tr style="border-top:2px solid rgba(37,99,235,0.4);"><td class="otd-rh">TOPLAM</td>'
    if init_key: h += '<td></td>'
    for t in tot: h += f'<td style="color:#93c5fd;font-weight:800;">{t:,}</td>'
    h += '</tr></tbody></table>'
    return h

def make_alloc(alloc_dict, lines):
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
    for i in range(14): h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    for ln in lines:
        rows = alloc_dict.get(ln, [])
        if not rows: continue
        disp = rows if isinstance(rows[0], list) else [rows]
        for ri, row in enumerate(disp):
            h += f'<tr><td class="otd-rh">{ln if ri==0 else ""}</td>'
            for v in row:
                if v:
                    bg = KART_RENKLERI.get(v,"#666")
                    h += f'<td style="background:{bg};color:#1e293b;font-weight:700;">{v}</td>'
                else: h += '<td class="otd-none">—</td>'
            h += '</tr>'
    h += '</tbody></table>'
    return h


# =====================================================================
# LOGO & BAŞLIK
# =====================================================================
lh = f'<img src="data:image/png;base64,{logo_b64}" style="height:55px;margin-right:14px;vertical-align:middle;">' if logo_b64 else ""
st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:4px;">{lh}<div>'
            f'<h1 style="color:#fff;margin:0;font-size:1.4rem;font-weight:700;">Çerkezköy Elektronik — Şasi ➜ Montaj Planlaması</h1></div></div>', unsafe_allow_html=True)
st.write("---")

# =====================================================================
# SIDEBAR
# =====================================================================
st.sidebar.header("Filtre & Ayarlar")
kart_sec = ["Tümü"] + sorted(SUS_CARDS)
secili = st.sidebar.selectbox("Kart:", kart_sec)
hl = None if secili == "Tümü" else secili
if hl:
    r = KART_RENKLERI.get(hl,"#fff")
    st.sidebar.markdown(f'<div style="background:{r};color:#1e293b;padding:8px 14px;border-radius:8px;font-weight:700;text-align:center;font-size:1.1rem;margin-top:6px;">{hl}</div>', unsafe_allow_html=True)
    st.sidebar.caption("MD geçişi var" if PROCESS_MAP.get(hl) else "MD'yi atlar (OTD → TA)")

# =====================================================================
# SEKMELER
# =====================================================================
tab_panel, tab_opt, tab_rapor, tab_veri = st.tabs(
    ["📊 Kontrol Paneli & Üretim Planı", "🚀 Optimize Et", "📑 Rapor & Geçişler", "⚙️ Veri Yönetimi"]
)


# =============  TAB 1: KONTROL PANELİ + ÜRETİM PLANI  =================
with tab_panel:
    # İhlal sayımı
    viol_otd = sum(1 for c in SUS_CARDS for v in sus["otd_rem"].get(c,[]) if v<0)
    viol_md = sum(1 for c in SUS_CARDS for v in sus["md_rem"].get(c,[]) if v<0)
    viol_ta = sum(1 for c in SUS_CARDS for v in sus["ta_rem"].get(c,[]) if v<0)
    viol_all = viol_otd + viol_md + viol_ta
    total_otd = sum(sum(v) for v in sus["otd_daily"].values())
    total_md = sum(sum(v) for v in sus["md_daily"].values())
    total_ta = sum(sum(v) for v in sus["ta_daily"].values())
    total_asm = sum(sum(v) for v in sus["assembly"].values())

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("OTD Üretim", f"{total_otd:,}")
    with c2: st.metric("MD Üretim", f"{total_md:,}")
    with c3: st.metric("TA Üretim", f"{total_ta:,}")
    with c4: st.metric("Montaj Talebi", f"{total_asm:,}")
    with c5:
        if viol_all == 0: st.metric("Durum", "FİZİBİL ✅")
        else: st.metric("Stok İhlali", f"{viol_all} gün×kart", delta=f"KSO:{viol_otd} KSM:{viol_md} KST:{viol_ta}", delta_color="inverse")
    st.write("---")

    # ── OTD ──
    with st.expander("⚡ OTD — Otomatik Dizgi (Hat Alokasyonu & Üretim & Stok)", expanded=True):
        st.markdown("**Hat – Kart Alokasyonu**")
        st.markdown(make_alloc(sus["otd_alloc"], ["OD0","OD2","OD3","OD4","OD6"]), unsafe_allow_html=True)
        st.markdown("**Günlük Üretim**")
        st.markdown(make_grid(sus["otd_daily"]), unsafe_allow_html=True)
        st.markdown("**📦 Kalan Stok — KSO**")
        st.caption("🔴 Negatif = stok açığı — üretim talebi karşılayamıyor")
        st.markdown(make_grid(sus["otd_rem"], "o"), unsafe_allow_html=True)

    # ── MD ──
    with st.expander("✋ MD — Manuel Dizgi (Hat Alokasyonu & Üretim & Stok)", expanded=False):
        st.markdown("**Hat – Kart Alokasyonu**")
        st.markdown(make_alloc(sus["md_alloc"], ["MD1","MD2"]), unsafe_allow_html=True)
        st.markdown("**Günlük Üretim**")
        st.markdown(make_grid(sus["md_daily"]), unsafe_allow_html=True)
        st.markdown("**📦 Kalan Stok — KSM**")
        st.markdown(make_grid(sus["md_rem"], "m"), unsafe_allow_html=True)

    # ── TA ──
    with st.expander("🔬 TA — Test & Ayar (Üretim & Stok & Montaj Planı)", expanded=False):
        st.markdown("**Günlük Üretim**")
        st.markdown(make_grid(sus["ta_daily"]), unsafe_allow_html=True)
        st.markdown("**📦 Kalan Stok — KST**")
        st.markdown(make_grid(sus["ta_rem"], "t"), unsafe_allow_html=True)
        st.markdown("**🎯 Montaj Planı (Talep)**")
        st.markdown(make_grid(sus["assembly"]), unsafe_allow_html=True)


# =============  TAB 2: OPTİMİZASYON  =================================
with tab_opt:
    st.markdown("""<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <span style="font-size:2rem;">🚀</span>
        <div><h2 style="margin:0;font-size:1.3rem;">Üretim Planı Optimizasyonu</h2>
        <p style="color:#93c5fd;margin:0;font-size:0.8rem;">Mevcut planı analiz et → İhlalleri tespit et → Düzeltme öner → Onay al</p></div>
    </div>""", unsafe_allow_html=True)

    # Mevcut durum özeti
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
        # Durum göstergesi
        if opt["status"] == "feasible":
            st.success(f"✅ {opt['message']}")
        elif opt["status"] == "optimal":
            st.success(f"✅ {opt['message']}")
        else:
            st.warning(f"⚠️ {opt['message']}")

        # Öneriler
        proposals = opt.get("proposals", [])
        if proposals:
            st.markdown("#### 📋 Değişiklik Önerileri")
            st.caption("Her öneriyi inceleyip onaylayabilir veya reddedebilirsiniz.")

            # Onay tablosu
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
                        c, d = p["card"], p["day"]-1
                        if p["type"].startswith("OTD"):
                            applied["otd_daily"][c][d] = p["new"]
                            if p.get("line"):
                                alloc = applied["otd_alloc"].get(p["line"], [""]*14)
                                if d < len(alloc): alloc[d] = c
                        elif p["type"].startswith("MD"):
                            applied["md_daily"][c][d] = p["new"]
                        applied_count += 1
                applied = recalc_stocks(applied)
                st.session_state.sus = applied
                st.session_state.opt_result = None
                st.success(f"✅ {applied_count} değişiklik uygulandı. Stoklar yeniden hesaplandı.")
                st.rerun()

        # Tavsiyeler
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

        # Önce/Sonra karşılaştırma
        if proposals and opt.get("new_plan"):
            with st.expander("📊 Önce / Sonra Karşılaştırması"):
                compare_card = st.selectbox("Kart seç:", sorted(viol_cards) if viol_cards else SUS_CARDS, key="cmp_card")
                if compare_card:
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        st.markdown("**Mevcut KSO:**")
                        old_vals = sus["otd_rem"].get(compare_card, [0]*14)
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=SUS_DATES, y=old_vals, name="Mevcut", marker_color=["#ef4444" if v<0 else "#3b82f6" for v in old_vals]))
                        fig.add_hline(y=0, line_dash="dash", line_color="red")
                        fig.update_layout(template="plotly_dark",height=280,margin=dict(l=30,r=10,t=10,b=30),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(255,255,255,0.03)")
                        st.plotly_chart(fig, use_container_width=True)
                    with bc2:
                        st.markdown("**Optimize KSO:**")
                        new_vals = opt["new_plan"]["otd_rem"].get(compare_card, [0]*14)
                        fig2 = go.Figure()
                        fig2.add_trace(go.Bar(x=SUS_DATES, y=new_vals, name="Optimize", marker_color=["#ef4444" if v<0 else "#22c55e" for v in new_vals]))
                        fig2.add_hline(y=0, line_dash="dash", line_color="red")
                        fig2.update_layout(template="plotly_dark",height=280,margin=dict(l=30,r=10,t=10,b=30),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(255,255,255,0.03)")
                        st.plotly_chart(fig2, use_container_width=True)


# =============  TAB 3: RAPOR & GEÇİŞLER  ==============================
with tab_rapor:
    st.markdown("### 📑 Rapor & Aşamalar Arası Geçişler")

    # Kart bazında geçiş tablosu
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
    # Stok ihlalleri listesi
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


# =============  TAB 4: VERİ YÖNETİMİ  ================================
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
            with ec2: new_m = st.number_input("MD Stok₀", value=si.get("m",0), step=10, key="nm")
            with ec3: new_t = st.number_input("TA Stok₀", value=si.get("t",0), step=10, key="nt")
            if st.button("💾 Stoğu Kaydet ve Yeniden Hesapla", type="primary"):
                sus["init"][edit_card] = {"o":new_o,"m":new_m,"t":new_t}
                st.session_state.sus = recalc_stocks(sus)
                st.success(f"{edit_card} stokları güncellendi, tampon stoklar yeniden hesaplandı.")
                st.rerun()

        elif veri_modu == "🔬 TA Fikstür Güncelle":
            st.caption("TA üretim miktarlarını güncelleyin.")
            ta_card = st.selectbox("Kart:", SUS_CARDS, key="ta_card")
            st.markdown(f"**Mevcut TA Üretim — {ta_card}:**")
            current = sus["ta_daily"].get(ta_card, [0]*14)
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
                            c = str(row.iloc[0]).strip()
                            if c in SUS_CARDS:
                                sus["init"][c] = {"o":int(row.iloc[1]),"m":int(row.iloc[2]),"t":int(row.iloc[3])}
                        st.session_state.sus = recalc_stocks(sus)
                        st.success("Stoklar yüklendi ve yeniden hesaplandı.")
                        st.rerun()
                except Exception as e: st.error(f"Hata: {e}")

        elif veri_modu == "🔄 Varsayılana Dön":
            st.warning("Tüm değişiklikleri sıfırlayıp orijinal Excel verisine dönülecek.")
            if st.button("🔄 Varsayılana Dön", type="primary"):
                st.session_state.sus = get_default_sus()
                st.session_state.opt_result = None
                st.success("Tüm veriler varsayılana döndürüldü.")
                st.rerun()
