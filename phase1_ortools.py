"""
phase1_ortools.py — Hibrit Çözücü FAZ 1 (OR-Tools / SCIP)
==========================================================
Görev   : Kombinatoryal atama ve setup minimizasyonu.
Çıktı   : yO, zO, yM, zM (ikili kararlar)
          → Faz 2 (PuLP+CBC) için SABİT parametre olarak aktarılır.

Bu faz, OR-Tools'un güçlü olduğu yere odaklanır:
  - Çok ikili değişken, BoolVar tabanlı atama
  - Setup tespiti (sequence-independent)
  - SCIP'in branch-and-cut hızı
Bu fazda üretim miktarları (xO, xM, xT) ve stoklar (KSO, KSM, KST)
de modelin içindedir, çünkü atamaların FİZİBİL olduğunu doğrulamak
gerekir; ama amaç fonksiyonunda yalnızca SETUP cezalandırılır.
Buffer ağırlığı 0 → Faz 1 buffer'a kayıtsız, sadece setup düşürür.

Yazar   : Mehmet Ensar & Ege — YTÜ Endüstri Müh. Bitirme Projesi
"""

from __future__ import annotations
from ortools.linear_solver import pywraplp
from typing import Any

S_OTD = 0.50   # OTD setup kapasite kaybı (%50)
S_MD  = 0.05   # MD  setup kapasite kaybı (%5)


def solve_phase1(data: dict[str, Any],
                 time_limit_sec: int = 60) -> dict[str, Any]:
    """
    Faz 1: yalnızca toplam setup'ı (OTD + MD) minimize eder.
    Atamaları (yO, zO, yM, zM) ve bunlardan türeyen OTD üretim ifadesini
    Faz 2'ye iletir. Tampon stoklar bu fazda da hesaplanır ama amaca girmez.
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
        return {"status": "ERROR", "message": "SCIP yüklenemedi."}
    solver.SetTimeLimit(time_limit_sec * 1000)
                           solver.SetRelativeMipGap(0.01)
    inf = solver.infinity()

    # --- OTD ikili değişkenleri ---
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

    # --- MD ikili değişkenleri + sürekli üretim ---
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

    # --- TA üretim + stoklar (fizibilite için gerekli) ---
    pT  = {(k, t): solver.NumVar(0, ta_cap.get((k, t), 0), f"pT_{k}_{t}")
           for k in K for t in days}
    KSO = {(k, t): solver.NumVar(0, inf, f"KSO_{k}_{t}")
           for k in K for t in days}
    KSM = {(k, t): solver.NumVar(0, inf, f"KSM_{k}_{t}")
           for k in K_MD for t in days}
    KST = {(k, t): solver.NumVar(0, inf, f"KST_{k}_{t}")
           for k in K for t in days}

    # --- OTD kısıtları ---
    for l in L_OTD:
        for t in days:
            c = [yO[k, l, t] for k in K if (k, l, t) in yO]
            if c:
                solver.Add(sum(c) <= 1)   # (P1.1) tek kart/hat/gün

    for l in L_OTD:
        for t in days:
            if t == 0:
                for k in K:
                    if (k, l, 0) in yO:
                        solver.Add(zO[l, 0] >= yO[k, l, 0])   # (P1.2) setup tespiti
            else:
                for k in K:
                    if (k, l, t) in yO:
                        prev = yO.get((k, l, t - 1))
                        if prev is not None:
                            solver.Add(zO[l, t] >= yO[k, l, t] - prev)
                        else:
                            solver.Add(zO[l, t] >= yO[k, l, t])

    for (k, l, t) in wO:                                       # (P1.3) wO = yO ∧ zO
        solver.Add(wO[k, l, t] <= yO[k, l, t])
        solver.Add(wO[k, l, t] <= zO[l, t])
        solver.Add(wO[k, l, t] >= yO[k, l, t] + zO[l, t] - 1)

    # --- MD kısıtları ---
    for m in L_MD:
        for t in days:
            c = [yM[k, m, t] for k in K_MD if (k, m, t) in yM]
            if c:
                solver.Add(sum(c) <= 1)                        # (P1.4) tek kart/MD hat/gün

    for m in L_MD:
        for t in days:
            if t == 0:
                for k in K_MD:
                    if (k, m, 0) in yM:
                        solver.Add(zM[m, 0] >= yM[k, m, 0])    # (P1.5) MD setup tespiti
            else:
                for k in K_MD:
                    if (k, m, t) in yM:
                        prev = yM.get((k, m, t - 1))
                        if prev is not None:
                            solver.Add(zM[m, t] >= yM[k, m, t] - prev)
                        else:
                            solver.Add(zM[m, t] >= yM[k, m, t])

    for (k, m, t), var in pM.items():
        solver.Add(var <= tempo_md[(k, m)] * yM[k, m, t])      # (P1.6) MD üretim ≤ tempo·yM

    for m in L_MD:
        for t in days:
            prods = [pM[k, m, t] for k in K_MD if (k, m, t) in pM]
            if prods:
                max_md = max(tempo_md.get((kk, m), 0) for kk in K_MD)
                solver.Add(sum(prods) <= max_md * (1 - S_MD * zM[m, t]))   # (P1.7) MD setup kaybı

    # --- OTD deterministik üretim ifadesi ---
    def otd_prod(k, t):
        terms = []
        for l in L_OTD:
            if (k, l, t) in yO:
                tp = tempo_otd[(k, l)]
                terms.append(tp * yO[k, l, t] - tp * S_OTD * wO[k, l, t])
        return sum(terms) if terms else 0

    def md_prod(k, t):
        return sum(pM[k, m, t] for m in L_MD if (k, m, t) in pM)

    # --- Stok denge denklemleri (fizibilite ZORUNLU) ---
    for k in K:
        for t in days:
            prev = KSO[k, t-1] if t > 0 else init_kso.get(k, 0)
            otd = otd_prod(k, t)
            if k in K_MD:
                solver.Add(KSO[k, t] == prev + otd - md_prod(k, t))       # (P1.8) KSO MD'li
            else:
                solver.Add(KSO[k, t] == prev + otd - pT[k, t])            # (P1.8) KSO MD-skip

    for k in K_MD:
        for t in days:
            prev = KSM[k, t-1] if t > 0 else init_ksm.get(k, 0)
            solver.Add(KSM[k, t] == prev + md_prod(k, t) - pT[k, t])      # (P1.9) KSM denge

    for k in K:
        for t in days:
            prev = KST[k, t-1] if t > 0 else init_kst.get(k, 0)
            solver.Add(KST[k, t] == prev + pT[k, t] - demand.get((k, t), 0))   # (P1.10) KST denge

    # --- AMAÇ FONKSİYONU (FAZ 1): yalnızca setup ---
    total_otd_z = sum(zO[l, t] for l in L_OTD for t in days)
    total_md_z  = sum(zM[m, t] for m in L_MD  for t in days)
    solver.Minimize(total_otd_z + total_md_z)                             # (P1.OBJ) min Σ setup

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return {"status": "INFEASIBLE",
                "message": "Faz 1: Fizibil atama bulunamadı."}

    smap = {pywraplp.Solver.OPTIMAL: "OPTIMAL",
            pywraplp.Solver.FEASIBLE: "FEASIBLE"}

    # --- Faz 2'ye aktarılacak SABİT atama kararları ---
    yO_fixed = {key: int(round(v.solution_value()))
                for key, v in yO.items() if v.solution_value() > 0.5}
    zO_fixed = {key: int(round(v.solution_value()))
                for key, v in zO.items() if v.solution_value() > 0.5}
    yM_fixed = {key: int(round(v.solution_value()))
                for key, v in yM.items() if v.solution_value() > 0.5}
    zM_fixed = {key: int(round(v.solution_value()))
                for key, v in zM.items() if v.solution_value() > 0.5}

    return {
        "status": smap.get(status, "UNKNOWN"),
        "phase1_setups": int(round(solver.Objective().Value())),
        "phase1_otd_setups": len(zO_fixed),
        "phase1_md_setups":  len(zM_fixed),
        "phase1_solve_time": round(solver.wall_time() / 1000, 2),
        "phase1_num_vars":   solver.NumVariables(),
        "phase1_num_cons":   solver.NumConstraints(),
        # Faz 2'ye geçecek sabit kararlar:
        "yO_fixed": yO_fixed,
        "zO_fixed": zO_fixed,
        "yM_fixed": yM_fixed,
        "zM_fixed": zM_fixed,
    }
