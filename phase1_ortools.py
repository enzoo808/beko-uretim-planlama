"""
phase1_ortools.py — Hibrit Çözücü FAZ 1 (OR-Tools pywraplp / CBC)
=================================================================
Görev   : Kombinatoryal atama + setup minimizasyonu.
Çıktı   : yO, zO, yM, zM (ikili kararlar) → Faz 2 için SABİT parametre.

Amaç    : min Σ zO  +  M × Σ dU_t
            M = 1000 (band uyumu setup'a güçlü biçimde öncelikli)
            dU_t  = günlük toplam OTD üretiminin alt band altı açığı (slack)

Kısıtlar:
  (P1.1)  Σ_k yO[k,l,t] ≤ 1          — hat başına en fazla 1 kart / gün
  (P1.2)  zO[l,t] ≥ yO[k,l,t] - yO[k,l,t-1]  — OTD setup tespiti
  (P1.3)  wO = yO ∧ zO                — linearize produktif zaman
  (P1.4)  Σ_k yM[k,m,t] ≤ 1          — MD hat başına en fazla 1 kart
  (P1.5)  zM[m,t] ≥ yM[k,m,t] - yM[k,m,t-1]  — MD setup (yalnız raporlama)
  (P1.6)  pM ≤ tempo_md × yM
  (P1.7)  MD kapasite tavanı (S_MD = 0)
  (P1.8)  KSO denge (≥ 0 hard)
  (P1.9)  KSM denge (≥ 0 hard)
  (P1.10) KST denge (≥ 0 hard)
  (P1.11) Σ_k Σ_l prod(k,l,t) + dU_t ≥ daily_total_min  — SOFT alt band
  (P1.12) Σ_k Σ_l prod(k,l,t) ≤ daily_total_max          — HARD üst band

2026-06 Düzeltmeleri:
  • S_MD = 0.0 — tez Kısıt (16): MD geçişinde kurulum kaybı yok
  • Amaç: YALNIZCA OTD setup + band cezası (MD cezalandırılmaz)
  • P1.11–P1.12 EKLENDİ: Faz 1'i kart atamaya zorlayan band kısıtları
    Neden: P1.11/12 olmadan, init_kso yeterli büyüklükte ise Faz 1'in
    trivial optimal çözümü "yO=0 her yerde" olur → Faz 2'ye sıfır atama gelir
    → kullanıcı hiç kart görmez, stoklar bozulur.

Yazar   : Mehmet Ensar & Ege — YTÜ Endüstri Müh. Bitirme Projesi
"""

from __future__ import annotations
from ortools.linear_solver import pywraplp
from typing import Any

S_OTD = 0.50   # OTD setup kapasite kaybı (%50) — Tez Bölüm 3.6.1
S_MD  = 0.0    # MD setup kaybı YOK — Tez Kısıt (16)

M_BAND = 1000.0   # Band ihlali ceza katsayısı (M >> max_setups ≈ 98)


def solve_phase1(data: dict[str, Any],
                 time_limit_sec: int = 60,
                 daily_total_min: float = 2600.0,
                 daily_total_max: float = 3100.0) -> dict[str, Any]:
    """
    Faz 1: Günlük üretim band kısıtları altında OTD setup minimizasyonu.

    Amaç: min Σ zO + M × Σ dU_t
      M=1000 >> max_setups (~98) → band uyumu setup azaltmaya öncelidir.
      dU_t = günlük üretimin daily_total_min altında kalan miktarı (slack ≥ 0).
    """
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

    solver = pywraplp.Solver.CreateSolver("CBC")
    if not solver:
        return {"status": "ERROR", "message": "CBC çözücü yüklenemedi."}
    solver.SetTimeLimit(time_limit_sec * 1000)
    solver.SetRelativeMipGap(0.01)
    inf = solver.infinity()

    # ─── OTD ikili değişkenleri ───────────────────────────────────────────────
    yO, zO, wO = {}, {}, {}
    for k in K:
        for l in L_OTD:
            for t in days:
                if tempo_otd.get((k, l), 0) > 0:
                    yO[k, l, t] = solver.BoolVar(f"yO_{k}_{l}_{t}")
    for l in L_OTD:
        for t in days:
            zO[l, t] = solver.BoolVar(f"zO_{l}_{t}")
    for (k, l, t) in yO:
        wO[k, l, t] = solver.BoolVar(f"wO_{k}_{l}_{t}")

    # ─── MD ikili değişkenleri + sürekli üretim ───────────────────────────────
    yM, zM, pM = {}, {}, {}
    for k in K_MD:
        for m in L_MD:
            for t in days:
                if tempo_md.get((k, m), 0) > 0:
                    yM[k, m, t] = solver.BoolVar(f"yM_{k}_{m}_{t}")
    for m in L_MD:
        for t in days:
            zM[m, t] = solver.BoolVar(f"zM_{m}_{t}")
    for k in K_MD:
        for m in L_MD:
            for t in days:
                cap = tempo_md.get((k, m), 0)
                if cap > 0:
                    pM[k, m, t] = solver.NumVar(0, cap, f"pM_{k}_{m}_{t}")

    # ─── TA üretim + stoklar ──────────────────────────────────────────────────
    pT  = {(k, t): solver.NumVar(0, ta_cap.get((k, t), 0), f"pT_{k}_{t}")
           for k in K for t in days}
    KSO = {(k, t): solver.NumVar(0, inf, f"KSO_{k}_{t}") for k in K for t in days}
    KSM = {(k, t): solver.NumVar(0, inf, f"KSM_{k}_{t}") for k in K_MD for t in days}
    KST = {(k, t): solver.NumVar(0, inf, f"KST_{k}_{t}") for k in K for t in days}

    # ─── Band slack değişkeni ─────────────────────────────────────────────────
    dU_p1 = {t: solver.NumVar(0, inf, f"dU_p1_{t}") for t in days}

    # ─── (P1.1) Tek kart / OTD hat / gün ────────────────────────────────────
    for l in L_OTD:
        for t in days:
            c = [yO[k, l, t] for k in K if (k, l, t) in yO]
            if c:
                solver.Add(sum(c) <= 1)

    # ─── (P1.2) OTD setup tespiti ────────────────────────────────────────────
    for l in L_OTD:
        for t in days:
            if t == 0:
                for k in K:
                    if (k, l, 0) in yO:
                        solver.Add(zO[l, 0] >= yO[k, l, 0])
            else:
                for k in K:
                    if (k, l, t) in yO:
                        prev = yO.get((k, l, t - 1))
                        if prev is not None:
                            solver.Add(zO[l, t] >= yO[k, l, t] - prev)
                        else:
                            solver.Add(zO[l, t] >= yO[k, l, t])

    # ─── (P1.3) wO = yO ∧ zO ────────────────────────────────────────────────
    for (k, l, t) in wO:
        solver.Add(wO[k, l, t] <= yO[k, l, t])
        solver.Add(wO[k, l, t] <= zO[l, t])
        solver.Add(wO[k, l, t] >= yO[k, l, t] + zO[l, t] - 1)

    # ─── (P1.4) Tek kart / MD hat / gün ────────────────────────────────────
    for m in L_MD:
        for t in days:
            c = [yM[k, m, t] for k in K_MD if (k, m, t) in yM]
            if c:
                solver.Add(sum(c) <= 1)

    # ─── (P1.5) MD setup tespiti (yalnız raporlama; amaca DAHİL DEĞİL) ───────
    for m in L_MD:
        for t in days:
            if t == 0:
                for k in K_MD:
                    if (k, m, 0) in yM:
                        solver.Add(zM[m, 0] >= yM[k, m, 0])
            else:
                for k in K_MD:
                    if (k, m, t) in yM:
                        prev = yM.get((k, m, t - 1))
                        if prev is not None:
                            solver.Add(zM[m, t] >= yM[k, m, t] - prev)
                        else:
                            solver.Add(zM[m, t] >= yM[k, m, t])

    # ─── (P1.6) MD üretim ≤ tempo × yM ─────────────────────────────────────
    for (k, m, t), var in pM.items():
        solver.Add(var <= tempo_md[(k, m)] * yM[k, m, t])

    # ─── (P1.7) MD hat kapasite tavanı (S_MD = 0) ───────────────────────────
    for m in L_MD:
        for t in days:
            prods = [pM[k, m, t] for k in K_MD if (k, m, t) in pM]
            if prods:
                max_md = max(tempo_md.get((kk, m), 0) for kk in K_MD)
                solver.Add(sum(prods) <= max_md)

    # ─── OTD üretim ifadesi ──────────────────────────────────────────────────
    def otd_prod(k, t):
        terms = []
        for l in L_OTD:
            if (k, l, t) in yO:
                tp = tempo_otd[(k, l)]
                terms.append(tp * yO[k, l, t] - tp * S_OTD * wO[k, l, t])
        return sum(terms) if terms else 0

    def md_prod(k, t):
        return sum(pM[k, m, t] for m in L_MD if (k, m, t) in pM)

    # ─── (P1.8) KSO denge ────────────────────────────────────────────────────
    for k in K:
        for t in days:
            prev = KSO[k, t-1] if t > 0 else init_kso.get(k, 0)
            otd = otd_prod(k, t)
            if k in K_MD:
                solver.Add(KSO[k, t] == prev + otd - md_prod(k, t))
            else:
                solver.Add(KSO[k, t] == prev + otd - pT[k, t])

    # ─── (P1.9) KSM denge ────────────────────────────────────────────────────
    for k in K_MD:
        for t in days:
            prev = KSM[k, t-1] if t > 0 else init_ksm.get(k, 0)
            solver.Add(KSM[k, t] == prev + md_prod(k, t) - pT[k, t])

    # ─── (P1.10) KST denge ───────────────────────────────────────────────────
    for k in K:
        for t in days:
            prev = KST[k, t-1] if t > 0 else init_kst.get(k, 0)
            solver.Add(KST[k, t] == prev + pT[k, t] - demand.get((k, t), 0))

    # ─── (P1.11) Günlük OTD üretim SOFT alt band ─────────────────────────────
    # Σ_k Σ_l prod(k,l,t) + dU_p1[t] ≥ daily_total_min
    # dU_p1 ≥ 0; ceza = M × dU_p1 >> max_setups → band uyumu öncelikli.
    for t in days:
        terms_t = [
            tempo_otd[(k, l)] * yO[k, l, t] - tempo_otd[(k, l)] * S_OTD * wO[k, l, t]
            for k in K for l in L_OTD if (k, l, t) in yO
        ]
        if terms_t:
            solver.Add(sum(terms_t) + dU_p1[t] >= daily_total_min)
        else:
            # Hiç uyumlu kart/hat yoksa sadece slack ile kısıtı sağla
            solver.Add(dU_p1[t] >= daily_total_min)

    # ─── (P1.12) Günlük OTD üretim HARD üst band ─────────────────────────────
    # Σ_k Σ_l prod(k,l,t) ≤ daily_total_max
    for t in days:
        terms_t = [
            tempo_otd[(k, l)] * yO[k, l, t] - tempo_otd[(k, l)] * S_OTD * wO[k, l, t]
            for k in K for l in L_OTD if (k, l, t) in yO
        ]
        if terms_t:
            solver.Add(sum(terms_t) <= daily_total_max)

    # ─── AMAÇ FONKSİYONU ─────────────────────────────────────────────────────
    # min Σ zO  +  M × Σ dU_p1[t]
    # M=1000 >> max_setups (~6×14=84) → band uyumu her zaman önce sağlanır.
    # zM: raporlama amaçlı saklanır, amaca dahil edilmez (MD setup serbest).
    total_otd_z  = sum(zO[l, t] for l in L_OTD for t in days)
    total_dU     = sum(dU_p1[t] for t in days)
    solver.Minimize(total_otd_z + M_BAND * total_dU)

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return {"status": "INFEASIBLE",
                "message": "Faz 1: Fizibil atama bulunamadı. "
                           "Kapasite < talep veya band çok dar."}

    smap = {pywraplp.Solver.OPTIMAL: "OPTIMAL", pywraplp.Solver.FEASIBLE: "FEASIBLE"}

    yO_fixed = {key: 1 for key, v in yO.items() if v.solution_value() > 0.5}
    zO_fixed = {key: 1 for key, v in zO.items() if v.solution_value() > 0.5}
    yM_fixed = {key: 1 for key, v in yM.items() if v.solution_value() > 0.5}
    zM_fixed = {key: 1 for key, v in zM.items() if v.solution_value() > 0.5}

    # Günlük üretim band açığı (raporlama)
    daily_under_vals = {t: round(dU_p1[t].solution_value(), 1) for t in days}
    total_dU_val = sum(daily_under_vals.values())

    return {
        "status": smap.get(status, "UNKNOWN"),
        "phase1_setups":     int(round(solver.Objective().Value() - M_BAND * total_dU_val)),
        "phase1_otd_setups": len(zO_fixed),
        "phase1_md_setups":  len(zM_fixed),
        "phase1_solve_time": round(solver.wall_time() / 1000, 2),
        "phase1_num_vars":   solver.NumVariables(),
        "phase1_num_cons":   solver.NumConstraints(),
        "phase1_daily_under": daily_under_vals,
        "phase1_band_total_under": round(total_dU_val, 1),
        # Faz 2'ye aktarılan sabit kararlar:
        "yO_fixed": yO_fixed,
        "zO_fixed": zO_fixed,
        "yM_fixed": yM_fixed,
        "zM_fixed": zM_fixed,
    }
