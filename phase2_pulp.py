"""
phase2_pulp.py — Hibrit Çözücü FAZ 2 (PuLP + CBC) v2 (2026-06)
================================================================
v2 değişiklikleri (Ensar talebi):
  • Hard kısıt: KSO/KSM/KST ≥ 0 (mevcut)
  • Hard kısıt: Günlük toplam OTD üretimi ≤ DAILY_TOTAL_MAX
  • Yumuşak hedef: Günlük toplam OTD üretimi ≥ DAILY_TOTAL_MIN (slack ile)
  • Yumuşak hedef: KSO ∈ [max_tempo(c)×LOW, max_tempo(c)×HIGH] (slack ile)
  • Ağırlıklı tek amaç: 100×bant_ihlali + 50×alt_bant_açığı + 1×buffer

Yazar : Mehmet Ensar & Ege — YTÜ Endüstri Müh. Bitirme Projesi
"""

from __future__ import annotations
import pulp
from typing import Any

S_OTD = 0.50

# Ağırlıklar (yumuşak hedefler için)
W_BAND_OVER  = 100.0   # KSO üst bandı aşma cezası (kart bazlı)
W_BAND_UNDER = 100.0   # KSO alt bandı altında kalma cezası
W_DAILY_LOW  = 50.0    # Günlük üretim alt bandı altı cezası
W_BUFFER     = 1.0     # Toplam buffer minimize


def solve_phase2(data: dict[str, Any],
                 phase1_result: dict[str, Any],
                 time_limit_sec: int = 60,
                 daily_total_min: float = 2600.0,
                 daily_total_max: float = 3100.0,
                 stock_band_low_ratio: float = 0.80,
                 stock_band_high_ratio: float = 1.20) -> dict[str, Any]:
    """Faz 2: Atamalar sabit, üretim ve buffer değişken.
    Çok hedef ağırlıklı: bant ihlali + alt bant açığı + buffer."""
    K       = data["kartlar"]
    K_MD    = data["kartlar_md"]
    K_SKIP  = data["kartlar_skip"]
    L_OTD   = data["otd_lines"]
    L_MD    = data["md_lines"]
    T       = data["T"]
    days    = list(range(T))

    tempo_otd = data["tempo_otd"]
    tempo_md  = data["tempo_md"]
    ta_cap    = data["ta_cap"]
    demand    = data["demand"]
    init_kso  = data["init_kso"]
    init_ksm  = data["init_ksm"]
    init_kst  = data["init_kst"]

    yO_fix = phase1_result["yO_fixed"]
    zO_fix = phase1_result["zO_fixed"]
    yM_fix = phase1_result["yM_fixed"]
    zM_fix = phase1_result["zM_fixed"]

    # --- Kart başına max tempo (stok bandı için) ---
    max_tempo_k = {}
    for k in K:
        vals = [tempo_otd[(k, l)] for l in L_OTD if (k, l) in tempo_otd]
        max_tempo_k[k] = max(vals) if vals else 0.0

    band_low  = {k: max_tempo_k[k] * stock_band_low_ratio  for k in K}
    band_high = {k: max_tempo_k[k] * stock_band_high_ratio for k in K}

    prob = pulp.LpProblem("Beko_Hybrid_Phase2_v2", pulp.LpMinimize)

    # --- Üretim değişkenleri ---
    xO = {}
    for (k, l, t), _ in yO_fix.items():
        cap = tempo_otd[(k, l)]
        is_setup = (l, t) in zO_fix
        ub = cap * (1 - S_OTD) if is_setup else cap
        xO[k, l, t] = pulp.LpVariable(f"xO_{k}_{l}_{t}", lowBound=0, upBound=ub)

    xM = {}
    for (k, m, t), _ in yM_fix.items():
        cap = tempo_md[(k, m)]
        xM[k, m, t] = pulp.LpVariable(f"xM_{k}_{m}_{t}", lowBound=0, upBound=cap)

    xT = {(k, t): pulp.LpVariable(f"xT_{k}_{t}", lowBound=0,
                                   upBound=ta_cap.get((k, t), 0))
          for k in K for t in days}

    # --- Tampon stoklar (≥0 hard) ---
    KSO = {(k, t): pulp.LpVariable(f"KSO_{k}_{t}", lowBound=0) for k in K for t in days}
    KSM = {(k, t): pulp.LpVariable(f"KSM_{k}_{t}", lowBound=0) for k in K_MD for t in days}
    KST = {(k, t): pulp.LpVariable(f"KST_{k}_{t}", lowBound=0) for k in K for t in days}

    # --- Slack değişkenleri (yumuşak hedefler için) ---
    # KSO bant açığı: alt bant (s_under) ve üst bant aşımı (s_over)
    s_under = {(k, t): pulp.LpVariable(f"sU_{k}_{t}", lowBound=0) for k in K for t in days}
    s_over  = {(k, t): pulp.LpVariable(f"sO_{k}_{t}", lowBound=0) for k in K for t in days}
    # Günlük toplam üretim alt bandı açığı
    d_under = {t: pulp.LpVariable(f"dU_{t}", lowBound=0) for t in days}

    def otd_prod(k, t):
        return pulp.lpSum(xO[k, l, t] for l in L_OTD if (k, l, t) in xO)

    def md_prod(k, t):
        return pulp.lpSum(xM[k, m, t] for m in L_MD if (k, m, t) in xM)

    # --- (P2.1) KSO denge ---
    for k in K:
        for t in days:
            prev = KSO[k, t-1] if t > 0 else init_kso.get(k, 0)
            if k in K_MD:
                prob += (KSO[k, t] == prev + otd_prod(k, t) - md_prod(k, t),
                         f"denge_KSO_md_{k}_{t}")
            else:
                prob += (KSO[k, t] == prev + otd_prod(k, t) - xT[k, t],
                         f"denge_KSO_skip_{k}_{t}")

    # --- (P2.2) KSM denge ---
    for k in K_MD:
        for t in days:
            prev = KSM[k, t-1] if t > 0 else init_ksm.get(k, 0)
            prob += (KSM[k, t] == prev + md_prod(k, t) - xT[k, t],
                     f"denge_KSM_{k}_{t}")

    # --- (P2.3) KST denge ---
    for k in K:
        for t in days:
            prev = KST[k, t-1] if t > 0 else init_kst.get(k, 0)
            prob += (KST[k, t] == prev + xT[k, t] - demand.get((k, t), 0),
                     f"denge_KST_{k}_{t}")

    # --- (P2.4) Günlük toplam OTD üretimi HARD üst sınır ---
    # Σ_k Σ_l xO[k,l,t] ≤ daily_total_max
    for t in days:
        daily_sum = pulp.lpSum(xO[k, l, t]
                               for (k, l, tt) in xO if tt == t)
        prob += (daily_sum <= daily_total_max,
                 f"daily_max_{t}")

    # --- (P2.5) Günlük toplam OTD üretimi SOFT alt sınır ---
    # Σ_k Σ_l xO[k,l,t] + d_under[t] ≥ daily_total_min
    for t in days:
        daily_sum = pulp.lpSum(xO[k, l, t]
                               for (k, l, tt) in xO if tt == t)
        prob += (daily_sum + d_under[t] >= daily_total_min,
                 f"daily_min_{t}")

    # --- (P2.6) KSO bant kısıtları (yumuşak) ---
    # KSO[k,t] + s_under[k,t] ≥ band_low[k]   → alt bandın altında kalırsa s_under > 0
    # KSO[k,t] - s_over[k,t]  ≤ band_high[k]  → üst bandı aşarsa s_over > 0
    for k in K:
        if max_tempo_k[k] <= 0:
            continue  # bu kartın OTD üretimi yok, bant tanımlanamaz
        for t in days:
            prob += (KSO[k, t] + s_under[k, t] >= band_low[k],
                     f"band_low_{k}_{t}")
            prob += (KSO[k, t] - s_over[k, t] <= band_high[k],
                     f"band_high_{k}_{t}")

    # --- (P2.OBJ) Ağırlıklı amaç ---
    obj_buffer = (pulp.lpSum(KSO[k, t] for k in K for t in days)
                  + pulp.lpSum(KSM[k, t] for k in K_MD for t in days)
                  + pulp.lpSum(KST[k, t] for k in K for t in days))
    obj_band = (pulp.lpSum(s_under[k, t] for k in K for t in days if max_tempo_k[k] > 0)
                + pulp.lpSum(s_over[k, t]  for k in K for t in days if max_tempo_k[k] > 0))
    obj_daily = pulp.lpSum(d_under[t] for t in days)

    prob += (W_BAND_OVER * obj_band
             + W_DAILY_LOW * obj_daily
             + W_BUFFER * obj_buffer)

    cbc = pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit_sec, gapRel=0.01)
    prob.solve(cbc)

    if prob.status != pulp.constants.LpStatusOptimal:
        if pulp.value(prob.objective) is None:
            return {"status": "INFEASIBLE",
                    "message": "Faz 2: Negatif KSO/KSM/KST sıfır olamadı. "
                               "Talep > kapasite. Hatlara kart ekleme veya "
                               "talep azaltma gerekli."}

    # Sonuç çıkar
    r_prod_otd = {(k, l, t): round(v.varValue)
                  for (k, l, t), v in xO.items()
                  if v.varValue is not None and v.varValue > 0.5}
    r_prod_md  = {(k, m, t): round(v.varValue)
                  for (k, m, t), v in xM.items()
                  if v.varValue is not None and v.varValue > 0.5}
    r_prod_ta  = {(k, t): round(v.varValue)
                  for (k, t), v in xT.items()
                  if v.varValue is not None and v.varValue > 0.5}

    sk_kso = {(k, t): round(KSO[k, t].varValue or 0) for k in K for t in days}
    sk_ksm = {(k, t): round(KSM[k, t].varValue or 0) for k in K_MD for t in days}
    sk_kst = {(k, t): round(KST[k, t].varValue or 0) for k in K for t in days}

    # Kısıt ihlalleri (raporlama)
    band_total_violation = sum(
        (s_under[k, t].varValue or 0) + (s_over[k, t].varValue or 0)
        for k in K for t in days if max_tempo_k[k] > 0
    )
    daily_under_total = sum(d_under[t].varValue or 0 for t in days)

    return {
        "status": "OPTIMAL" if prob.status == pulp.LpStatusOptimal else "FEASIBLE",
        "phase2_buffer": int(sum(sk_kso.values()) + sum(sk_ksm.values()) + sum(sk_kst.values())),
        "phase2_solve_time": round(prob.solutionTime, 2),
        "phase2_num_vars": len(prob.variables()),
        "phase2_num_cons": len(prob.constraints),
        "phase2_band_violation": round(band_total_violation),
        "phase2_daily_under":    round(daily_under_total),
        "prod_otd": r_prod_otd,
        "prod_md":  r_prod_md,
        "prod_ta":  r_prod_ta,
        "stocks_kso": sk_kso,
        "stocks_ksm": sk_ksm,
        "stocks_kst": sk_kst,
    }
