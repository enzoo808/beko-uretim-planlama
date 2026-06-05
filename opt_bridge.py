"""
opt_bridge.py — Dashboard ↔ Hibrit Optimizasyon Köprüsü
========================================================
dashboard.py'ın `run_optimization(plan)` arayüzünü AYNEN korur ama
arkada Greedy yerine HİBRİT motoru (Faz 1: OR-Tools/SCIP + Faz 2: PuLP/CBC)
çağırır.

KULLANIM (dashboard.py'da TEK satır değişir):
    Eski:  def run_optimization(current_plan): ... (820. satır gövdesi)
    Yeni:  from opt_bridge import run_optimization

Bu modül, dashboard.py'ın slot1+slot2 veri modelini hibrit motorunun
flat (k,l,t)-anahtarlı modeline çevirir, çözer, sonucu dashboard'un
beklediği `{status, proposals, new_plan, ...}` şemasında geri verir.

Yazar: Mehmet Ensar & Ege — YTÜ Endüstri Müh. Bitirme Projesi
"""

from __future__ import annotations
import copy
from typing import Any
from hybrid_solver import solve as hybrid_solve


def _dashboard_module():
    """dashboard.py'ı tembel import et (dairesel import'tan kaçınmak için)."""
    import dashboard as _dash
    return _dash


# ===================================================================
# 1. PLAN → DATA dönüşümü (dashboard formatı → hibrit formatı)
# ===================================================================

def _plan_to_data(plan: dict,
                  sus_cards: list,
                  otd_lines: list,
                  md_lines: list,
                  tempo: dict,
                  n_days: int,
                  process_map: dict) -> dict:
    """
    dashboard.py'ın plan formatından hibrit motorunun data formatına çevirir.

    dashboard.py veri yapısı:
      plan["assembly"][card] = [g1, g2, ..., g14]   # son montaj talebi
      plan["init"][card] = {"o": int, "m": int, "t": int}   # başlangıç stok
      plan["otd_alloc"][line] = [g1, g2, ...]       # slot1 atamaları
      tempo[line][card] = int                        # hat-kart kapasitesi

    Hibrit data yapısı:
      data["demand"][(k,t)] = float
      data["tempo_otd"][(k,l)] = float
      data["init_kso"][k] = float, vb.
    """
    # Kart sınıflandırması
    kartlar_md   = [c for c in sus_cards if process_map.get(c, False)]
    kartlar_skip = [c for c in sus_cards if not process_map.get(c, False)]

    # MD hatları — dashboard'ta MD2_1, MD2_2 ayrı kanal olarak işlense de
    # hibrit motor MD1 ve MD2 fiziksel hat seviyesinde çalışır
    md_lines_hybrid = ["MD1", "MD2"]

    # OTD tempoları: tempo[line][card] → tempo_otd[(card, line)]
    tempo_otd = {}
    for l in otd_lines:
        for c in sus_cards:
            v = tempo.get(l, {}).get(c, 0)
            if v and v > 0:
                tempo_otd[(c, l)] = float(v)

    # MD tempoları — dashboard.py'daki MD_TEMPO'dan al, yoksa default
    md_tempo_src = getattr(_dashboard_module(), "MD_TEMPO", None)
    tempo_md = {}
    if md_tempo_src:
        for m in md_lines_hybrid:
            for c in kartlar_md:
                v = md_tempo_src.get(m, {}).get(c, 0)
                if v and v > 0:
                    tempo_md[(c, m)] = float(v)
    else:
        _default_md_tempo = {
            ("GB","MD1"):800, ("GL","MD1"):780, ("MR","MD1"):600, ("V1","MD1"):1000,
            ("XGB","MD1"):950, ("XGS","MD1"):1100, ("Y3","MD1"):890, ("Y4","MD1"):1000,
            ("GB","MD2"):800, ("GL","MD2"):780, ("MR","MD2"):600, ("V1","MD2"):1000,
            ("XGB","MD2"):950, ("XGS","MD2"):1100, ("Y3","MD2"):890, ("Y4","MD2"):1000,
        }
        tempo_md = {k: float(v) for k, v in _default_md_tempo.items() if v > 0}

    # TA fikstur kapasitesi — dashboard.py'daki TA_FIKSTUR_DEFAULT × TA_ADET_DEFAULT
    dash_mod = _dashboard_module()
    ta_fix = getattr(dash_mod, "TA_FIKSTUR_DEFAULT", None)
    ta_adet = getattr(dash_mod, "TA_ADET_DEFAULT", None)
    if ta_fix and ta_adet:
        ta_cap = {(c, t): float(2 * ta_fix.get(c, 0) * ta_adet.get(c, 0))
                  for c in sus_cards for t in range(n_days)}
    else:
        _ta_max = {
            "F4":160, "GB":180, "GL":630, "GX":1040, "LG":1040,
            "MR":100, "V1":760, "XC":1160, "XD":600, "XGB":828,
            "XGS":1680, "XR":460, "Y3":640, "Y4":628,
        }
        ta_cap = {(c, t): float(_ta_max.get(c, 0))
                  for c in sus_cards for t in range(n_days)}

    # Montaj talebi
    demand = {}
    for c in sus_cards:
        asm = plan.get("assembly", {}).get(c, [0] * n_days)
        for t in range(n_days):
            val = asm[t] if t < len(asm) else 0
            if val and val > 0:
                demand[(c, t)] = float(val)

    # Başlangıç stokları
    init_kso = {c: float(plan.get("init", {}).get(c, {}).get("o", 0))
                for c in sus_cards}
    init_ksm = {c: float(plan.get("init", {}).get(c, {}).get("m", 0))
                for c in kartlar_md}
    init_kst = {c: float(plan.get("init", {}).get(c, {}).get("t", 0))
                for c in sus_cards}

    return {
        "kartlar":      sus_cards,
        "kartlar_md":   kartlar_md,
        "kartlar_skip": kartlar_skip,
        "otd_lines":    otd_lines,
        "md_lines":     md_lines_hybrid,
        "T":            n_days,
        "tempo_otd":    tempo_otd,
        "tempo_md":     tempo_md,
        "ta_cap":       ta_cap,
        "demand":       demand,
        "init_kso":     init_kso,
        "init_ksm":     init_ksm,
        "init_kst":     init_kst,
    }


# ===================================================================
# 2. RESULT → PROPOSALS + NEW_PLAN (hibrit çıktısı → dashboard şeması)
# ===================================================================

def _result_to_proposals(plan_before: dict,
                         result: dict,
                         sus_cards: list,
                         otd_lines: list,
                         n_days: int,
                         sus_dates: list,
                         process_map: dict) -> tuple[list, dict]:
    """
    Hibrit motor çıktısını dashboard'un beklediği `proposals` listesine ve
    `new_plan` dict'ine çevirir.
    """
    new_plan = copy.deepcopy(plan_before)
    proposals = []

    # --- OTD alokasyon ve üretim önerileri ---
    # Hibrit çıktısı plan_otd: {"OD0|0": "XGS", "OD0|1": "XGS", ...}
    # Hibrit çıktısı prod_otd: {"XGS|OD0|0": 1040, ...}

    # Önce mevcut allocation'ı sıfır gibi düşünüp hibritin önerdiğini koy
    new_otd_alloc = {l: [""] * n_days for l in otd_lines}
    new_otd_daily = {c: [0] * n_days for c in sus_cards}

    for key, card in result.get("plan_otd", {}).items():
        if not card:
            continue
        line, t_str = key.split("|")
        t = int(t_str)
        if line in new_otd_alloc and t < n_days:
            new_otd_alloc[line][t] = card

    for key, prod in result.get("prod_otd", {}).items():
        k, l, t_str = key.split("|")
        t = int(t_str)
        if k in new_otd_daily and t < n_days:
            new_otd_daily[k][t] += int(prod)

    # --- MD üretim ---
    new_md_daily = {c: [0] * n_days for c in sus_cards if process_map.get(c)}
    for key, prod in result.get("prod_md", {}).items():
        k, _m, t_str = key.split("|")
        t = int(t_str)
        if k in new_md_daily and t < n_days:
            new_md_daily[k][t] += int(prod)

    # --- TA üretim ---
    new_ta_daily = {c: [0] * n_days for c in sus_cards}
    for key, prod in result.get("prod_ta", {}).items():
        k, t_str = key.split("|")
        t = int(t_str)
        if k in new_ta_daily and t < n_days:
            new_ta_daily[k][t] = int(prod)

    # --- new_plan'a yaz ---
    new_plan["otd_alloc"] = new_otd_alloc
    new_plan["otd_daily"] = new_otd_daily
    new_plan["md_daily"]  = new_md_daily
    new_plan["ta_daily"]  = new_ta_daily

    # Slot2 boş bırakılır (hibrit motor günde tek slot çalışıyor)
    new_plan["otd_alloc2"] = {l: [""] * n_days for l in otd_lines}
    new_plan["otd_split"]  = {l: [(1.0, 0.0)] * n_days for l in otd_lines}

    # --- Değişiklikleri proposal olarak listele ---
    old_otd_alloc = plan_before.get("otd_alloc", {})
    old_otd_daily = plan_before.get("otd_daily", {})
    old_md_daily  = plan_before.get("md_daily", {})
    old_ta_daily  = plan_before.get("ta_daily", {})

    # OTD alokasyon değişiklikleri
    for line in otd_lines:
        old_a = old_otd_alloc.get(line, [""] * n_days)
        new_a = new_otd_alloc.get(line, [""] * n_days)
        for t in range(n_days):
            old_c = old_a[t] if t < len(old_a) else ""
            new_c = new_a[t] if t < len(new_a) else ""
            if old_c != new_c and new_c:  # sadece yeni atamaları rapor et
                old_prod = old_otd_daily.get(new_c, [0]*n_days)[t] if t < len(old_otd_daily.get(new_c, [])) else 0
                new_prod = new_otd_daily.get(new_c, [0]*n_days)[t]
                proposals.append({
                    "type": "OTD üretim ekle",
                    "card": new_c,
                    "day": t + 1,
                    "date": sus_dates[t] if t < len(sus_dates) else f"G{t+1}",
                    "line": line,
                    "old": int(old_prod),
                    "new": int(new_prod),
                    "reason": f"{line} hattına {new_c} atandı (hibrit motor önerisi)",
                    "impact": f"+{int(new_prod - old_prod):,} adet OTD",
                    "slot": 1,
                })

    # MD üretim değişiklikleri
    for c in new_md_daily:
        old_arr = old_md_daily.get(c, [0]*n_days)
        new_arr = new_md_daily.get(c, [0]*n_days)
        for t in range(n_days):
            old_v = old_arr[t] if t < len(old_arr) else 0
            new_v = new_arr[t]
            if new_v != old_v and new_v > 0:
                proposals.append({
                    "type": "MD üretim ekle",
                    "card": c,
                    "day": t + 1,
                    "date": sus_dates[t] if t < len(sus_dates) else f"G{t+1}",
                    "line": "MD",
                    "old": int(old_v),
                    "new": int(new_v),
                    "reason": f"{c} MD üretimi hibrit motor tarafından ayarlandı",
                    "impact": f"{int(new_v - old_v):+,} adet MD",
                })

    # TA üretim değişiklikleri
    for c in sus_cards:
        old_arr = old_ta_daily.get(c, [0]*n_days)
        new_arr = new_ta_daily.get(c, [0]*n_days)
        for t in range(n_days):
            old_v = old_arr[t] if t < len(old_arr) else 0
            new_v = new_arr[t]
            if new_v != old_v and new_v > 0:
                proposals.append({
                    "type": "TA üretim ekle",
                    "card": c,
                    "day": t + 1,
                    "date": sus_dates[t] if t < len(sus_dates) else f"G{t+1}",
                    "line": "TA",
                    "old": int(old_v),
                    "new": int(new_v),
                    "reason": f"{c} TA üretimi hibrit motor tarafından ayarlandı",
                    "impact": f"{int(new_v - old_v):+,} adet TA",
                })

    return proposals, new_plan


# ===================================================================
# 3. ANA ARAYÜZ — run_optimization(plan)
# ===================================================================

def run_optimization(current_plan: dict,
                     time_limit_sec: int = 120) -> dict:
    """
    dashboard.py için drop-in replacement.

    Arkada hibrit motoru (Faz 1 SCIP + Faz 2 CBC) çalıştırır,
    sonucu dashboard'un beklediği {status, proposals, new_plan, ...}
    şemasında döndürür.
    """
    # dashboard.py içindeki global sabitlere erişmek için import yapıyoruz
    # — dairesel import'tan kaçınmak için çağrı anında
    import dashboard as dash

    sus_cards   = dash.SUS_CARDS
    otd_lines   = dash.OTD_LINES
    md_lines    = ["MD1", "MD2"]
    tempo       = dash.TEMPO
    process_map = dash.PROCESS_MAP
    sus_dates   = dash.SUS_DATES
    n_days      = dash.N_DAYS

    # 1. Plan → Data dönüşümü
    data = _plan_to_data(current_plan, sus_cards, otd_lines, md_lines,
                          tempo, n_days, process_map)

    # 2. Hibrit motoru çağır
    try:
        result = hybrid_solve(data, time_limit_sec=time_limit_sec)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Hibrit motor hatası: {type(e).__name__}: {str(e)[:200]}",
            "proposals": [],
            "new_plan": current_plan,
            "remaining_violations": -1,
            "suggestions": ["• Veri tutarlılığını kontrol edin",
                            "• Zaman limitini arttırın",
                            "• OR-Tools ve PuLP'in kurulu olduğunu doğrulayın"],
        }

    if result.get("status") not in ("OPTIMAL", "FEASIBLE"):
        return {
            "status": "partial",
            "message": result.get("message", "Hibrit motor fizibil çözüm bulamadı."),
            "proposals": [],
            "new_plan": current_plan,
            "remaining_violations": -1,
            "suggestions": ["• Talep ile kapasite uyumsuz olabilir",
                            "• Başlangıç stoklarını gözden geçirin"],
        }

    # 3. Sonucu dashboard formatına çevir
    proposals, new_plan = _result_to_proposals(
        current_plan, result, sus_cards, otd_lines, n_days, sus_dates, process_map
    )

    # 4. Yeni planın stoklarını yeniden hesapla (dashboard.py'ın recalc'i)
    try:
        new_plan = dash.recalc_stocks(new_plan)
    except Exception:
        pass  # recalc başarısız olursa yine de proposal döndür

    # 5. Kalan ihlal sayısı
    remaining = 0
    for c in sus_cards:
        for rk in ["otd_rem", "md_rem", "ta_rem"]:
            if rk == "md_rem" and not process_map.get(c):
                continue
            arr = new_plan.get(rk, {}).get(c, [])
            remaining += sum(1 for v in arr if v < 0)

    # 6. Mesaj ve durum
    n_props = len(proposals)
    setup_count = result.get("total_setups", "—")
    buffer_total = result.get("total_buffer", "—")
    phase1_t = result.get("phase1_time", "—")
    phase2_t = result.get("phase2_time", "—")

    msg = (f"Hibrit motor çözdü — Setup: {setup_count}, "
           f"Tampon: {buffer_total:,} | "
           f"Faz1 (SCIP) {phase1_t}s + Faz2 (CBC) {phase2_t}s | "
           f"{n_props} değişiklik önerisi")

    status = "optimal" if (result["status"] == "OPTIMAL" and remaining == 0) else \
             "feasible" if remaining == 0 else "partial"

    suggestions = []
    if remaining > 0:
        suggestions.append(f"• {remaining} stok ihlali kaldı — manuel kontrol gerekli")
    else:
        suggestions.append("✅ Hibrit motor tüm kısıtları sağlayan plan üretti")
    suggestions.append(f"📈 OTD setup: {result.get('otd_setups', '—')} | "
                       f"MD setup: {result.get('md_setups', '—')}")
    suggestions.append(f"📈 Çözücü: Faz 1 OR-Tools/SCIP + Faz 2 PuLP/CBC (açık kaynak hibrit)")

    return {
        "status": status,
        "message": msg,
        "proposals": proposals,
        "new_plan": new_plan,
        "remaining_violations": remaining,
        "suggestions": suggestions,
        # Ekstra (UI'da göstermek isterse):
        "_hybrid_meta": {
            "total_setups":  result.get("total_setups"),
            "otd_setups":    result.get("otd_setups"),
            "md_setups":     result.get("md_setups"),
            "total_buffer":  result.get("total_buffer"),
            "phase1_time":   result.get("phase1_time"),
            "phase2_time":   result.get("phase2_time"),
            "solve_time":    result.get("solve_time_sec"),
        },
    }
