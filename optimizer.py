"""
optimizer.py — Beko TV Anakart Üretim Planlama MILP Modeli (v4)
================================================================
Çözücü  : Google OR-Tools (pywraplp) + SCIP
Yapı    : CLSP-SI — Hibrit Üretim Miktarları

OTD AŞAMASI → DETERMİNİSTİK (tam tempo veya sıfır)
  pO = tempo × yO × (1 - S_OTD × setup)
  Çözücü 662, 199 gibi küsuratlı değer üretemez.

MD AŞAMASI  → KAPASİTE SINIRLI SÜREKLİ (MD tempo ≤ üst sınır)
  MD'de hat ataması ikili (yM), üretim ≤ tempo × yM × verim.
  Neden sürekli: MD temposu > OTD temposu olan kartlarda (GB, GL, MR)
  deterministik MD, KSO'yu negatife düşürür.

TA AŞAMASI  → SÜREKLİ (fikstur bazlı, ≤ ta_cap)

Yazar   : Mehmet Ensar & Ege — YTÜ Endüstri Müh. Bitirme Projesi
Danışman: Prof. Dr. Nihan Çetin Demirel
"""

from __future__ import annotations
from ortools.linear_solver import pywraplp
from typing import Any

# ─────────────────────────────────────────────────────────────────────
S_OTD      = 0.50        # OTD setup kaybı (%50)
S_MD       = 0.05        # MD  setup kaybı (%5)
W_SETUP    = 100_000     # Setup ağırlığı
W_IDLE     = 10          # Boş OTD hat cezası
SOLVER_ID  = "SCIP"


def solve(data: dict[str, Any],
          time_limit_sec: int = 120) -> dict[str, Any]:

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

    solver = pywraplp.Solver.CreateSolver(SOLVER_ID)
    if not solver:
        return {"status": "ERROR", "message": "SCIP yüklenemedi."}
    solver.SetTimeLimit(time_limit_sec * 1000)
    solver.SetRelativeMipGap(0.01)
    inf = solver.infinity()

    # =================================================================
    #  OTD DEĞİŞKENLERİ — DETERMİNİSTİK
    # =================================================================
    yO = {}   # yO[k,l,t] ∈ {0,1}
    for k in K:
        for l in L_OTD:
            for t in days:
                if tempo_otd.get((k, l), 0) > 0:
                    yO[k, l, t] = solver.BoolVar(f"yO_{k}_{l}_{t}")

    zO = {}   # zO[l,t] ∈ {0,1} — OTD setup
    for l in L_OTD:
        for t in days:
            zO[l, t] = solver.BoolVar(f"zO_{l}_{t}")

    wO = {}   # wO[k,l,t] = yO ∧ zO  (McCormick lineerleştirme)
    for (k, l, t) in yO:
        wO[k, l, t] = solver.BoolVar(f"wO_{k}_{l}_{t}")

    # =================================================================
    #  MD DEĞİŞKENLERİ — ATAMA İKİLİ, ÜRETİM SÜREKLİ
    # =================================================================
    yM = {}   # yM[k,m,t] ∈ {0,1}
    for k in K_MD:
        for m in L_MD:
            for t in days:
                if tempo_md.get((k, m), 0) > 0:
                    yM[k, m, t] = solver.BoolVar(f"yM_{k}_{m}_{t}")

    zM = {}   # zM[m,t] ∈ {0,1} — MD setup
    for m in L_MD:
        for t in days:
            zM[m, t] = solver.BoolVar(f"zM_{m}_{t}")

    pM = {}   # pM[k,m,t] ≥ 0 — MD üretim (sürekli, ≤ tempo × yM)
    for k in K_MD:
        for m in L_MD:
            for t in days:
                cap = tempo_md.get((k, m), 0)
                if cap > 0:
                    pM[k, m, t] = solver.NumVar(0, cap, f"pM_{k}_{m}_{t}")

    # =================================================================
    #  TA ve STOK DEĞİŞKENLERİ
    # =================================================================
    pT  = {(k, t): solver.NumVar(0, ta_cap.get((k, t), 0), f"pT_{k}_{t}")
           for k in K for t in days}
    KSO = {(k, t): solver.NumVar(0, inf, f"KSO_{k}_{t}")
           for k in K for t in days}
    KSM = {(k, t): solver.NumVar(0, inf, f"KSM_{k}_{t}")
           for k in K_MD for t in days}
    KST = {(k, t): solver.NumVar(0, inf, f"KST_{k}_{t}")
           for k in K for t in days}

    # =================================================================
    #  OTD KISITLARI
    # =================================================================

    # (C1) Bir hatta günde ≤ 1 kart
    for l in L_OTD:
        for t in days:
            c = [yO[k, l, t] for k in K if (k, l, t) in yO]
            if c:
                solver.Add(sum(c) <= 1)

    # (C2) OTD setup tespiti
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

    # (C3) wO = yO ∧ zO  (McCormick)
    for (k, l, t) in wO:
        solver.Add(wO[k, l, t] <= yO[k, l, t])
        solver.Add(wO[k, l, t] <= zO[l, t])
        solver.Add(wO[k, l, t] >= yO[k, l, t] + zO[l, t] - 1)

    # =================================================================
    #  MD KISITLARI
    # =================================================================

    # (C4) Bir MD hattında günde ≤ 1 kart
    for m in L_MD:
        for t in days:
            c = [yM[k, m, t] for k in K_MD if (k, m, t) in yM]
            if c:
                solver.Add(sum(c) <= 1)

    # (C5) MD setup tespiti
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

    # (C6) MD üretim ≤ tempo × yM  (atanmadıysa üretim = 0)
    for (k, m, t), var in pM.items():
        solver.Add(var <= tempo_md[(k, m)] * yM[k, m, t])

    # (C7) MD setup kaybı — Σ pM ≤ max_md × (1 - S_MD × zM)
    for m in L_MD:
        for t in days:
            prods = [pM[k, m, t] for k in K_MD if (k, m, t) in pM]
            if prods:
                max_md = max(tempo_md.get((kk, m), 0) for kk in K_MD)
                solver.Add(sum(prods) <= max_md * (1 - S_MD * zM[m, t]))

    # =================================================================
    #  DETERMİNİSTİK OTD ÜRETİM İFADESİ
    # =================================================================
    # pO[k,l,t] = tempo × yO - tempo × S_OTD × wO
    # Bu bir karar değişkeni DEĞİL, bir ifadedir (expression).
    # yO=1, zO=0 → tam tempo.  yO=1, zO=1 → yarım tempo.

    def otd_prod(k, t):
        """Kart k'nın gün t'deki toplam OTD üretimi."""
        terms = []
        for l in L_OTD:
            if (k, l, t) in yO:
                tp = tempo_otd[(k, l)]
                terms.append(tp * yO[k, l, t] - tp * S_OTD * wO[k, l, t])
        return sum(terms) if terms else 0

    def md_prod(k, t):
        """Kart k'nın gün t'deki toplam MD üretimi (sürekli)."""
        return sum(pM[k, m, t] for m in L_MD if (k, m, t) in pM)

    # =================================================================
    #  STOK DENGE DENKLEMLERİ
    # =================================================================

    # (C8) KSO: K_MD → OTD çıkış - MD giriş.  K_SKIP → OTD çıkış - TA giriş.
    for k in K:
        for t in days:
            prev = KSO[k, t-1] if t > 0 else init_kso.get(k, 0)
            otd = otd_prod(k, t)
            if k in K_MD:
                solver.Add(KSO[k, t] == prev + otd - md_prod(k, t))
            else:
                solver.Add(KSO[k, t] == prev + otd - pT[k, t])

    # (C9) KSM: MD çıkış - TA giriş (sadece K_MD)
    for k in K_MD:
        for t in days:
            prev = KSM[k, t-1] if t > 0 else init_ksm.get(k, 0)
            solver.Add(KSM[k, t] == prev + md_prod(k, t) - pT[k, t])

    # (C10) KST: TA çıkış - Montaj talebi
    for k in K:
        for t in days:
            prev = KST[k, t-1] if t > 0 else init_kst.get(k, 0)
            solver.Add(KST[k, t] == prev + pT[k, t]
                       - demand.get((k, t), 0))

    # =================================================================
    #  AMAÇ FONKSİYONU
    # =================================================================
    total_otd_z = sum(zO[l, t] for l in L_OTD for t in days)
    total_md_z  = sum(zM[m, t] for m in L_MD  for t in days)

    idle = 0
    for l in L_OTD:
        for t in days:
            c = [yO[k, l, t] for k in K if (k, l, t) in yO]
            if c:
                idle += (1 - sum(c))

    buf = (sum(KSO[k, t] for k in K for t in days)
           + sum(KSM[k, t] for k in K_MD for t in days)
           + sum(KST[k, t] for k in K for t in days))

    solver.Minimize(
        W_SETUP * (total_otd_z + total_md_z)
        + W_IDLE * idle
        + buf
    )

    # =================================================================
    #  ÇÖZ
    # =================================================================
    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return {"status": "INFEASIBLE",
                "message": "Fizibil çözüm bulunamadı."}

    smap = {pywraplp.Solver.OPTIMAL: "OPTIMAL",
            pywraplp.Solver.FEASIBLE: "FEASIBLE"}

    # ── Sonuç çıkarma ───────────────────────────────────────────────
    plan_otd = {}
    for l in L_OTD:
        for t in days:
            a = None
            for k in K:
                if (k, l, t) in yO and yO[k, l, t].solution_value() > 0.5:
                    a = k; break
            plan_otd[(l, t)] = a

    # OTD üretim: deterministik
    r_prod_otd = {}
    for k in K:
        for l in L_OTD:
            for t in days:
                if (k, l, t) in yO and yO[k, l, t].solution_value() > 0.5:
                    tp = tempo_otd[(k, l)]
                    setup = wO[k, l, t].solution_value() > 0.5
                    prod = round(tp * (1 - S_OTD) if setup else tp)
                    if prod > 0:
                        r_prod_otd[(k, l, t)] = prod

    # MD
    plan_md = {}
    for m in L_MD:
        for t in days:
            a = None
            for k in K_MD:
                if (k, m, t) in yM and yM[k, m, t].solution_value() > 0.5:
                    a = k; break
            plan_md[(m, t)] = a

    r_prod_md = {}
    for (k, m, t), var in pM.items():
        v = var.solution_value()
        if v > 0.5:
            r_prod_md[(k, m, t)] = round(v)

    # TA
    r_prod_ta = {}
    for (k, t), var in pT.items():
        v = var.solution_value()
        if v > 0.5:
            r_prod_ta[(k, t)] = round(v)

    s_otd = {(l,t) for (l,t),v in zO.items() if v.solution_value() > 0.5}
    s_md  = {(m,t) for (m,t),v in zM.items() if v.solution_value() > 0.5}

    sk_kso = {(k,t): round(KSO[k,t].solution_value()) for k in K for t in days}
    sk_ksm = {(k,t): round(KSM[k,t].solution_value()) for k in K_MD for t in days}
    sk_kst = {(k,t): round(KST[k,t].solution_value()) for k in K for t in days}

    return {
        "status": smap.get(status, "UNKNOWN"),
        "total_setups": len(s_otd) + len(s_md),
        "otd_setups": len(s_otd), "md_setups": len(s_md),
        "total_buffer": sum(sk_kso.values())+sum(sk_ksm.values())+sum(sk_kst.values()),
        "plan_otd":   {f"{l}|{t}": v for (l,t),v in plan_otd.items()},
        "plan_md":    {f"{m}|{t}": v for (m,t),v in plan_md.items()},
        "prod_otd":   {f"{k}|{l}|{t}": v for (k,l,t),v in r_prod_otd.items()},
        "prod_md":    {f"{k}|{m}|{t}": v for (k,m,t),v in r_prod_md.items()},
        "prod_ta":    {f"{k}|{t}": v for (k,t),v in r_prod_ta.items()},
        "setups":     {f"{l}|{t}": True for l,t in s_otd},
        "setups_md":  {f"{m}|{t}": True for m,t in s_md},
        "stocks_kso": {f"{k}|{t}": v for (k,t),v in sk_kso.items()},
        "stocks_ksm": {f"{k}|{t}": v for (k,t),v in sk_ksm.items()},
        "stocks_kst": {f"{k}|{t}": v for (k,t),v in sk_kst.items()},
        "solve_time_sec": round(solver.wall_time()/1000, 2),
        "num_variables": solver.NumVariables(),
        "num_constraints": solver.NumConstraints(),
        "objective_value": round(solver.Objective().Value()),
    }

if __name__ == "__main__":
    td = {
        "kartlar": ["XC","XR"], "kartlar_md": [], "kartlar_skip": ["XC","XR"],
        "otd_lines": ["OD0","OD2"], "md_lines": ["MD1","MD2"], "T": 3,
        "tempo_otd": {("XC","OD0"):1000, ("XR","OD0"):900,
                      ("XC","OD2"):1000, ("XR","OD2"):900},
        "tempo_md": {},
        "ta_cap": {("XC",t):800 for t in range(3)} | {("XR",t):700 for t in range(3)},
        "demand": {("XC",t):400 for t in range(3)} | {("XR",t):300 for t in range(3)},
        "init_kso": {"XC":500,"XR":400}, "init_ksm": {},
        "init_kst": {"XC":200,"XR":150},
    }
    r = solve(td, 30)
    print(f"Durum: {r['status']}, Setup: {r['total_setups']}, Buffer: {r['total_buffer']}")
