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
# VARSAYILAN SUS VERİSİ
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

# =====================================================================
# SESSION STATE
# =====================================================================
if "sus" not in st.session_state:
    st.session_state.sus = get_default_sus()
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

sus = st.session_state.sus

# =====================================================================
# OPTİMİZASYON MOTORU  (orijinal, değişmedi)
# =====================================================================
def recalc_stocks(plan):
    p = copy.deepcopy(plan)
    init = p["init"]
    for c in SUS_CARDS:
        otd = p["otd_daily"].get(c, [0]*14)
        asm = p["assembly"].get(c, [0]*14)
        md  = p["md_daily"].get(c, [0]*14)
        ta  = p["ta_daily"].get(c, [0]*14)
        needs_md = PROCESS_MAP.get(c, False)
        cum_otd = 0; cum_down = 0; otd_rem = []
        for i in range(14):
            cum_otd  += otd[i]
            cum_down += (md[i] if needs_md else ta[i])
            otd_rem.append(init.get(c,{}).get("o",0) + cum_otd - cum_down)
        p["otd_rem"][c] = otd_rem
        if needs_md:
            cum_md = 0; cum_ta_d = 0; md_rem = []
            for i in range(14):
                cum_md   += md[i]
                cum_ta_d += ta[i]
                md_rem.append(init.get(c,{}).get("m",0) + cum_md - cum_ta_d)
            p["md_rem"][c] = md_rem
        cum_ta = 0; cum_asm = 0; ta_rem = []
        for i in range(14):
            cum_ta  += ta[i]
            cum_asm += asm[i]
            ta_rem.append(init.get(c,{}).get("t",0) + cum_ta - cum_asm)
        p["ta_rem"][c] = ta_rem
    return p

def run_optimization(current_plan):
    plan = copy.deepcopy(current_plan)
    proposals = []
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
    applied = copy.deepcopy(plan)
    for v in sorted(violations, key=lambda x: (x["day"], -x["deficit"])):
        c, stage, day, deficit = v["card"], v["stage"], v["day"], v["deficit"]
        if stage == "OTD":
            alloc = applied["otd_alloc"]
            for d in range(max(0, day-2), day+1):
                for line in ["OD0","OD2","OD3","OD4","OD6"]:
                    line_alloc = alloc.get(line, [""]*14)
                    if d < len(line_alloc) and line_alloc[d] == "":
                        cap = TEMPO.get(line, {}).get(c, 0)
                        if cap > 0:
                            old_val = applied["otd_daily"][c][d]
                            add = min(cap, deficit)
                            proposals.append({"type":"OTD üretim ekle","card":c,"day":d+1,"date":SUS_DATES[d],"line":line,"old":old_val,"new":old_val+add,"reason":f"{c} KSO Gün {day+1}'de −{deficit:,} açık","impact":f"+{add:,} adet üretim"})
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
                alloc = new_plan["otd_alloc"].get(p["line"], [""]*14)
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
                alloc = applied["otd_alloc"].get(p["line"], [""]*14)
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
            f"background:radial-gradient(ellipse at 50% 40%,rgba(0,15,50,0.52) 0%,rgba(0,10,35,0.78) 70%,rgba(0,5,25,0.88) 100%);"
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
    footer{{visibility:hidden!important;}}
    header[data-testid="stHeader"]{{background:rgba(0,15,45,0.82)!important;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);}}
    @keyframes fadeSlideIn{{from{{opacity:0;transform:translateY(12px);}}to{{opacity:1;transform:translateY(0);}}}}
    .block-container{{max-width:1300px;animation:fadeSlideIn 0.5s ease-out;}}
    .stTabs [data-baseweb="tab-panel"]{{animation:fadeSlideIn 0.35s ease-out;}}
    section[data-testid="stSidebar"]{{background:rgba(0,12,40,0.88)!important;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);}}
    section[data-testid="stSidebar"] .stSelectbox label,section[data-testid="stSidebar"] h2{{color:#fff!important;}}
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
</style>""", unsafe_allow_html=True)

# =====================================================================
# TABLO FONKSİYONLARI  (orijinal, değişmedi)
# =====================================================================

# ═══ v3: Alokasyondan günlük üretime dönüşüm ═══
def alloc_to_daily(alloc_dict, tempo_dict, lines, rates_dict=None):
    """OTD alokasyonunu günlük üretim miktarlarına dönüştürür."""
    daily = {c: [0]*14 for c in SUS_CARDS}
    for ln in lines:
        row_data = alloc_dict.get(ln, [""]*14)
        rows = row_data if (row_data and isinstance(row_data[0], list)) else [row_data]
        rates = rates_dict.get(ln, [1]*14) if rates_dict else [1]*14
        for row in rows:
            for i, card in enumerate(row):
                if i < 14 and card and card in SUS_CARDS:
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
            old_rem = old_plan[rem_key].get(c, [0]*14)
            new_rem = new_plan[rem_key].get(c, [0]*14)
            for i in range(14):
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
def make_grid(card_data, init_key=None, d_idx=None):
    idx = d_idx if d_idx is not None else list(range(14))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Kart</th>'
    if init_key: h += '<th>Stok₀</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    tot = [0]*len(idx)
    for c in SUS_CARDS:
        vals = card_data.get(c, [0]*14)
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
    idx = d_idx if d_idx is not None else list(range(14))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Kart</th>'
    if init_key: h += '<th>Stok₀</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    tot = [0]*len(idx)
    for c in SUS_CARDS:
        vals = card_data.get(c, [0]*14)
        ref_vals = ref_data.get(c, [0]*14) if ref_data else None
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
    idx = d_idx if d_idx is not None else list(range(14))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    for ln in lines:
        rows = alloc_dict.get(ln, [])
        if not rows: continue
        disp = rows if isinstance(rows[0], list) else [rows]
        rates = rates_dict.get(ln, [1]*14) if rates_dict else None
        for ri, row in enumerate(disp):
            h += f'<tr><td class="otd-rh">{ln if ri==0 else ""}</td>'
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
    idx = d_idx if d_idx is not None else list(range(14))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    for ln in lines:
        rows_new = alloc_new.get(ln, [])
        rows_ref = alloc_ref.get(ln, [])
        if not rows_new: continue
        disp_new = rows_new if isinstance(rows_new[0], list) else [rows_new]
        disp_ref = rows_ref if (rows_ref and isinstance(rows_ref[0], list)) else [rows_ref] if rows_ref else [[""] * 14]
        rates = rates_dict.get(ln, [1]*14) if rates_dict else None
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
    """Verimlilik oranları tablosu — alokasyondaki kart rengini arka plan olarak kullanır."""
    idx = d_idx if d_idx is not None else list(range(14))
    h = '<table class="otd-table"><thead><tr><th style="text-align:left;">Hat</th>'
    for i in idx: h += f'<th>{SUS_DAYS[i]}<br><span style="font-size:0.58rem;opacity:0.7">{SUS_DATES[i]}</span></th>'
    h += '</tr></thead><tbody>'
    for ln in lines:
        rates = rates_dict.get(ln, [1]*14)
        alloc_row = alloc_dict.get(ln, [""]*14)
        if isinstance(alloc_row[0] if alloc_row else "", list): alloc_row = alloc_row[0]
        h += f'<tr><td class="otd-rh">{ln}</td>'
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
# LOGO & BAŞLIK  (orijinal, değişmedi)
# =====================================================================
lh = f'<img src="data:image/png;base64,{logo_b64}" style="height:55px;margin-right:14px;vertical-align:middle;">' if logo_b64 else ""
st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:4px;">{lh}<div>'
            f'<h1 style="color:#fff;margin:0;font-size:1.4rem;font-weight:700;">Çerkezköy Elektronik — Şasi ➜ Montaj Planlaması</h1></div></div>', unsafe_allow_html=True)
st.write("---")

# =====================================================================
# SIDEBAR  (orijinal, değişmedi)
# =====================================================================
st.sidebar.header("Filtre & Ayarlar")
kart_sec = ["Tümü"] + sorted(SUS_CARDS)
secili = st.sidebar.selectbox("Kart:", kart_sec)
hl = None if secili == "Tümü" else secili
if hl:
    r = KART_RENKLERI.get(hl,"#fff")
    st.sidebar.markdown(f'<div style="background:{r};color:#1e293b;padding:8px 14px;border-radius:8px;font-weight:700;text-align:center;font-size:1.1rem;margin-top:6px;">{hl}</div>', unsafe_allow_html=True)
    st.sidebar.caption("MD geçişi var" if PROCESS_MAP.get(hl) else "MD'yi atlar (OTD → TA)")

# ═══ v3: Tarih Aralığı Filtresi ═══
st.sidebar.write("---")
st.sidebar.markdown("**📅 Tarih Aralığı**")
_date_labels = [f"{SUS_DAYS[i]} {SUS_DATES[i]}" for i in range(14)]
_d_start, _d_end = st.sidebar.select_slider(
    "Görüntülenecek tarih aralığı:",
    options=list(range(14)),
    value=(st.session_state.date_start_idx, st.session_state.date_end_idx),
    format_func=lambda x: _date_labels[x],
    key="date_slider"
)
st.session_state.date_start_idx = _d_start
st.session_state.date_end_idx   = _d_end
DATE_INDICES = list(range(_d_start, _d_end + 1))
st.sidebar.caption(f"{len(DATE_INDICES)} gün görüntüleniyor: {SUS_DATES[_d_start]} — {SUS_DATES[_d_end]}")

# =====================================================================
# SEKMELER
# =====================================================================
tab_panel, tab_opt, tab_rapor, tab_veri = st.tabs(
    ["📊 Kontrol Paneli & Üretim Planı", "🚀 Optimize Et", "📑 Rapor & Geçişler", "⚙️ Veri Yönetimi"]
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
                                al = applied["otd_alloc"].get(p["line"], [""]*14)
                                if d_k < len(al): al[d_k] = c_k
                        elif p["type"].startswith("MD"):
                            applied["md_daily"][c_k][d_k] = p["new"]
                    applied = recalc_stocks(applied)
                    st.session_state.sus = applied
                    st.session_state.otd_opt_res = None
                    st.session_state.md_opt_res  = None
                    st.session_state.ta_opt_res  = None
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
    with st.expander("⚡ OTD — Otomatik Dizgi (Hat Alokasyonu & Üretim & Stok)", expanded=True):

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
                    <span style="color:#cbd5e1;font-size:0.82rem;">Aşağıdaki tabloda hücrelere tıklayarak kart ataması yapın veya değiştirin. Boş bırakmak için hücreyi temizleyin.<br>
                    Geçerli kartlar: """ + ", ".join(SUS_CARDS) + """</span>
                </div>""", unsafe_allow_html=True)

                # Hat-kart uyum bilgisi
                with st.expander("📖 Hat — Kart Uyumluluk Tablosu", expanded=False):
                    compat_rows = []
                    for ln in ["OD0","OD2","OD3","OD4","OD6"]:
                        cards = sorted([c for c in TEMPO.get(ln, {}) if TEMPO[ln][c] > 0])
                        compat_rows.append({"Hat": ln, "Üretilebilir Kartlar": ", ".join(cards),
                                            "Tempoları": " | ".join([f"{c}:{TEMPO[ln][c]}" for c in cards])})
                    st.dataframe(pd.DataFrame(compat_rows), use_container_width=True, hide_index=True)

                # DataFrame oluştur — mevcut alokasyondan
                edit_data = {}
                for ln in ["OD0","OD2","OD3","OD4","OD6"]:
                    row = sus["otd_alloc"].get(ln, [""]*14)
                    if isinstance(row[0], list): row = row[0]  # flatten if nested
                    edit_data[ln] = {f"{SUS_DAYS[i]} {SUS_DATES[i]}": (row[i] if i < len(row) else "") for i in range(14)}
                df_edit = pd.DataFrame(edit_data).T
                df_edit.index.name = "Hat"

                # Düzenlenebilir tablo
                st.markdown("**🎯 Kart Ataması** — hücreye tıklayın ve listeden kart seçin:")
                edited_df = st.data_editor(
                    df_edit,
                    use_container_width=True,
                    num_rows="fixed",
                    key="otd_alloc_editor",
                    column_config={
                        col: st.column_config.SelectboxColumn(
                            col, options=[""] + SUS_CARDS, default="", width="small"
                        ) for col in df_edit.columns
                    }
                )

                # ═══ v3.1: Oran editörü — alokasyonla birleşik görünüm ═══
                st.markdown("**📊 Verimlilik Oranları** — her hücrenin üretim oranı (0.0 – 1.0, varsayılan 1.0 = %100):")
                st.caption("💡 Setup değişikliği olan günlerde oran < 1.0 olarak girin (ör: 0.5 = %50 verimlilik)")
                rate_data = {}
                for ln in ["OD0","OD2","OD3","OD4","OD6"]:
                    rates = sus.get("otd_rates", {}).get(ln, [1]*14)
                    rate_data[ln] = {f"{SUS_DAYS[i]} {SUS_DATES[i]}": rates[i] if i < len(rates) else 1.0 for i in range(14)}
                df_rates = pd.DataFrame(rate_data).T
                df_rates.index.name = "Hat"
                edited_rates = st.data_editor(
                    df_rates,
                    use_container_width=True,
                    num_rows="fixed",
                    key="otd_rate_editor",
                    column_config={
                        col: st.column_config.NumberColumn(
                            col, min_value=0.0, max_value=1.0, step=0.05, format="%.2f", width="small"
                        ) for col in df_rates.columns
                    }
                )

                # Uygula / Önizle butonları
                ec1, ec2, ec3 = st.columns([2, 2, 4])
                with ec1:
                    btn_preview = st.button("🔍 Etkiyi Önizle", type="secondary", use_container_width=True, key="btn_preview_alloc")
                with ec2:
                    btn_apply = st.button("✅ Alokasyonu Uygula", type="primary", use_container_width=True, key="btn_apply_alloc")

                if btn_preview or btn_apply:
                    # edited_df → alloc dict'e dönüştür
                    new_alloc = copy.deepcopy(sus["otd_alloc"])
                    new_rates = copy.deepcopy(sus.get("otd_rates", {}))
                    for ln in ["OD0","OD2","OD3","OD4","OD6"]:
                        row_vals = []
                        rate_vals = []
                        for i in range(14):
                            col_name = f"{SUS_DAYS[i]} {SUS_DATES[i]}"
                            cell = str(edited_df.loc[ln, col_name]).strip() if col_name in edited_df.columns else ""
                            row_vals.append(cell if cell in SUS_CARDS else "")
                            rv = edited_rates.loc[ln, col_name] if col_name in edited_rates.columns else 1.0
                            rate_vals.append(float(rv) if rv else 1.0)
                        new_alloc[ln] = row_vals
                        new_rates[ln] = rate_vals

                    # Alokasyondan günlük üretime dönüştür
                    new_daily = alloc_to_daily(new_alloc, TEMPO, ["OD0","OD2","OD3","OD4","OD6"], new_rates)

                    # Yeni plan oluştur ve stokları hesapla
                    preview_plan = copy.deepcopy(sus)
                    preview_plan["otd_alloc"] = new_alloc
                    preview_plan["otd_rates"] = new_rates
                    preview_plan["otd_daily"] = new_daily
                    preview_plan = recalc_stocks(preview_plan)

                    # Etki hesapla
                    impact = compute_manual_impact(sus, preview_plan)

                    st.write("---")
                    st.markdown("### 📊 Değişiklik Etki Analizi")

                    # KPI karşılaştırma
                    ic1, ic2, ic3, ic4 = st.columns(4)
                    old_viol = sum(1 for c in SUS_CARDS for v in sus["otd_rem"].get(c,[]) if v<0)
                    new_viol = sum(1 for c in SUS_CARDS for v in preview_plan["otd_rem"].get(c,[]) if v<0)
                    old_total = sum(sum(v) for v in sus["otd_daily"].values())
                    new_total = sum(sum(v) for v in preview_plan["otd_daily"].values())
                    with ic1: st.metric("KSO İhlal (Önce)", f"{old_viol} gün×kart")
                    with ic2: st.metric("KSO İhlal (Sonra)", f"{new_viol} gün×kart", delta=f"{new_viol-old_viol:+d}", delta_color="inverse")
                    with ic3: st.metric("Toplam OTD Üretim (Önce)", f"{old_total:,}")
                    with ic4: st.metric("Toplam OTD Üretim (Sonra)", f"{new_total:,}", delta=f"{new_total-old_total:+,}")

                    # Detaylı değişiklikler
                    if impact["changes"]:
                        st.markdown("**📋 Stok Değişimleri:**")
                        changes_df = pd.DataFrame(impact["changes"])
                        changes_df = changes_df.rename(columns={"card":"Kart","stage":"Aşama","day":"Gün","date":"Tarih","old":"Önce","new":"Sonra","diff":"Fark","status":"Durum"})
                        changes_df["Durum"] = changes_df["Durum"].map({"fixed":"✅ Çözüldü","new_violation":"❌ Yeni İhlal","changed":"🔄 Değişti"})
                        st.dataframe(changes_df[["Kart","Aşama","Gün","Tarih","Önce","Sonra","Fark","Durum"]], use_container_width=True, hide_index=True, height=min(400, 40+35*len(changes_df)))

                        # Özet
                        s = impact["summary"]
                        st.markdown(
                            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:12px;margin-top:8px;">'
                            f'<span style="color:#22c55e;font-weight:700;">✅ {s["fixed"]} ihlal çözüldü</span> &nbsp;|&nbsp; '
                            f'<span style="color:#ef4444;font-weight:700;">❌ {s["new_violations"]} yeni ihlal</span> &nbsp;|&nbsp; '
                            f'<span style="color:#93c5fd;">{s["unchanged"]} stok değeri değişti</span></div>',
                            unsafe_allow_html=True
                        )

                    # Önizle: alokasyon + stok tabloları
                    st.markdown("**🔄 Yeni Alokasyon:**")
                    st.markdown(make_alloc_compare(new_alloc, sus["otd_alloc"], ["OD0","OD2","OD3","OD4","OD6"], d_idx=DATE_INDICES, rates_dict=new_rates), unsafe_allow_html=True)
                    st.markdown("**Yeni Günlük Üretim:**")
                    st.markdown(make_grid_plan(new_daily, sus["otd_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                    st.markdown("**📦 Yeni Kalan Stok — KSO:**")
                    st.markdown(make_grid_plan(preview_plan["otd_rem"], sus["otd_rem"], "o", d_idx=DATE_INDICES), unsafe_allow_html=True)

                    if btn_apply:
                        st.session_state.sus = preview_plan
                        st.session_state.otd_opt_res = None
                        st.session_state.manual_impact = impact
                        st.success("✅ Manuel alokasyon uygulandı, stoklar yeniden hesaplandı!")
                        st.rerun()

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
            st.markdown("**Hat – Kart Alokasyonu**")
            st.markdown(make_alloc(sus["md_alloc"], ["MD1","MD2"], d_idx=DATE_INDICES), unsafe_allow_html=True)
            st.markdown("**Günlük Üretim**")
            st.markdown(make_grid(sus["md_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
            st.markdown("**📦 Kalan Stok — KSM**")
            st.markdown(make_grid(sus["md_rem"], "m", d_idx=DATE_INDICES), unsafe_allow_html=True)

        else:
            mt1, mt2 = st.tabs(["📋 Referans Plan (Mevcut)", "⚡ Optimize Sonucu"])
            np = md_res["new_plan"]

            with mt1:
                st.markdown("**Hat – Kart Alokasyonu**")
                st.markdown(make_alloc(sus["md_alloc"], ["MD1","MD2"], d_idx=DATE_INDICES), unsafe_allow_html=True)
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
            st.markdown("**Günlük Üretim**")
            st.markdown(make_grid(sus["ta_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
            st.markdown("**📦 Kalan Stok — KST**")
            st.markdown(make_grid(sus["ta_rem"], "t", d_idx=DATE_INDICES), unsafe_allow_html=True)
            st.markdown("**🎯 Montaj Planı (Talep)**")
            st.markdown(make_grid(sus["assembly"], d_idx=DATE_INDICES), unsafe_allow_html=True)

        else:
            tt1, tt2 = st.tabs(["📋 Referans Plan (Mevcut)", "⚡ Optimize Sonucu"])
            np = ta_res["new_plan"]

            with tt1:
                st.markdown("**Günlük Üretim**")
                st.markdown(make_grid(sus["ta_daily"], d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**📦 Kalan Stok — KST**")
                st.markdown(make_grid(sus["ta_rem"], "t", d_idx=DATE_INDICES), unsafe_allow_html=True)
                st.markdown("**🎯 Montaj Planı (Talep)**")
                st.markdown(make_grid(sus["assembly"], d_idx=DATE_INDICES), unsafe_allow_html=True)

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
                                alloc = applied["otd_alloc"].get(p["line"], [""]*14)
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
                st.success("Tüm veriler varsayılana döndürüldü.")
                st.rerun()
