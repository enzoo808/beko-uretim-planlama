"""
optimizer.py — Beko TV Anakart Üretim Planlama MILP Modeli
===========================================================
Çözücü  : Google OR-Tools (pywraplp) + SCIP
Yapı    : CLSP-SI (Capacitated Lot Sizing Problem – Setup & Inventory)
Amaç    : Ağırlıklı tek-fazlı optimizasyon (hierarchical weights)
            min  W_SETUP × Σ zO  +  1 × Σ (KSO + KSM + KST)
          W_SETUP yeterince büyük seçilerek leksikografik etki sağlanır:
          model önce setup'ı minimize eder, sonra eşit setup içinde
          tampon stoğu minimize eder.

Mimari  : Hiçbir Streamlit (st) bağımlılığı YOKTUR.
          Parametreleri dict olarak alır, sonucu dict olarak döner.

Yazar   : Mehmet Ensar & Ege — YTÜ Endüstri Mühendisliği Bitirme Projesi
Danışman: Prof. Dr. Nihan Çetin Demirel
"""

from __future__ import annotations
from ortools.linear_solver import pywraplp
from typing import Any


# ─────────────────────────────────────────────────────────────────────
#  SABİTLER
# ─────────────────────────────────────────────────────────────────────
SETUP_LOSS    = 0.50       # Kart değişimi → günlük kapasitenin %50'si kayıp
W_SETUP       = 100_000    # Setup ağırlığı — buffer toplamından >> büyük
SOLVER_ID     = "SCIP"     # OR-Tools MIP back-end


# ─────────────────────────────────────────────────────────────────────
#  ANA ÇÖZÜM FONKSİYONU
# ─────────────────────────────────────────────────────────────────────
def solve(data: dict[str, Any],
          time_limit_sec: int = 120) -> dict[str, Any]:
    """
    Parametreler
    ------------
    data : dict — Aşağıdaki anahtarları içermeli:
        kartlar, kartlar_md, kartlar_skip : list[str]
        otd_lines, md_lines              : list[str]
        T                                : int
        tempo_otd  : dict[(k,l), float]
        tempo_md   : dict[(k,m), float]
        ta_cap     : dict[(k,t), float]
        demand     : dict[(k,t), float]
        init_kso, init_ksm, init_kst : dict[k, float]

    time_limit_sec : int — Çözücü zaman limiti (saniye)

    Dönüş
    ------
    dict — status, total_setups, total_buffer, plan_otd, prod_otd,
           prod_md, prod_ta, setups, stocks_kso, stocks_ksm, stocks_kst,
           solve_time_sec, num_variables, num_constraints
    """

    # ── Veri çözümleme ──────────────────────────────────────────────
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

    # Her OTD hattının günlük maksimum kapasitesi (en yüksek tempo)
    max_cap = {}
    for l in L_OTD:
        caps = [tempo_otd.get((k, l), 0) for k in K]
        max_cap[l] = max(caps) if caps else 0

    # ═════════════════════════════════════════════════════════════════
    #  MODEL OLUŞTUR
    # ═════════════════════════════════════════════════════════════════
    solver = pywraplp.Solver.CreateSolver(SOLVER_ID)
    if not solver:
        return {"status": "ERROR",
                "message": f"{SOLVER_ID} çözücüsü bulunamadı. "
                           f"'pip install ortools' komutunu çalıştırın."}

    solver.SetTimeLimit(time_limit_sec * 1000)
    infinity = solver.infinity()

    # ── KARAR DEĞİŞKENLERİ ─────────────────────────────────────────

    # yO[k,l,t] ∈ {0,1} — Kart k, OTD hattı l, gün t'de üretiliyor mu?
    yO = {}
    for k in K:
        for l in L_OTD:
            for t in days:
                if tempo_otd.get((k, l), 0) > 0:
                    yO[k, l, t] = solver.BoolVar(f"yO_{k}_{l}_{t}")

    # zO[l,t] ∈ {0,1} — OTD hattı l'de gün t'de setup var mı?
    zO = {}
    for l in L_OTD:
        for t in days:
            zO[l, t] = solver.BoolVar(f"zO_{l}_{t}")

    # pO[k,l,t] ≥ 0 — OTD üretim miktarı (adet)
    pO = {}
    for k in K:
        for l in L_OTD:
            for t in days:
                cap = tempo_otd.get((k, l), 0)
                if cap > 0:
                    pO[k, l, t] = solver.NumVar(0, cap, f"pO_{k}_{l}_{t}")

    # pM[k,m,t] ≥ 0 — MD üretim miktarı (sadece K_MD kartları)
    pM = {}
    for k in K_MD:
        for m in L_MD:
            for t in days:
                cap = tempo_md.get((k, m), 0)
                if cap > 0:
                    pM[k, m, t] = solver.NumVar(0, cap, f"pM_{k}_{m}_{t}")

    # pT[k,t] ≥ 0 — TA üretim miktarı
    pT = {}
    for k in K:
        for t in days:
            cap = ta_cap.get((k, t), 0)
            pT[k, t] = solver.NumVar(0, cap, f"pT_{k}_{t}")

    # KSO[k,t] ≥ 0 — OTD → sonraki aşama tampon stoku
    KSO = {}
    for k in K:
        for t in days:
            KSO[k, t] = solver.NumVar(0, infinity, f"KSO_{k}_{t}")

    # KSM[k,t] ≥ 0 — MD → TA tampon stoku (sadece K_MD kartları)
    KSM = {}
    for k in K_MD:
        for t in days:
            KSM[k, t] = solver.NumVar(0, infinity, f"KSM_{k}_{t}")

    # KST[k,t] ≥ 0 — TA → Montaj tampon stoku
    KST = {}
    for k in K:
        for t in days:
            KST[k, t] = solver.NumVar(0, infinity, f"KST_{k}_{t}")

    # ── KISITLAR ────────────────────────────────────────────────────

    # (1) Bir OTD hattında günde en fazla bir kart tipi üretilebilir.
    #     Σ_k yO[k,l,t] ≤ 1    ∀ l ∈ L_OTD, t ∈ T
    for l in L_OTD:
        for t in days:
            cards_on_line = [yO[k, l, t] for k in K
                            if (k, l, t) in yO]
            if cards_on_line:
                solver.Add(sum(cards_on_line) <= 1)

    # (2) OTD üretim kapasitesi — alokasyona bağlı.
    #     pO[k,l,t] ≤ tempo[k,l] × yO[k,l,t]    ∀ k,l,t
    for (k, l, t), var in pO.items():
        solver.Add(var <= tempo_otd[(k, l)] * yO[k, l, t])

    # (3) Setup tespiti — kart değişimi zO'yu tetikler.
    #     t=0: zO[l,0] ≥ yO[k,l,0]            (ilk gün, her atama = setup)
    #     t>0: zO[l,t] ≥ yO[k,l,t] - yO[k,l,t-1]
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
                            # Kart dün bu hatta atanamaz → bugün atanırsa setup
                            solver.Add(zO[l, t] >= yO[k, l, t])

    # (4) Setup kaybı — setup olan günde hat kapasitesi %50 azalır.
    #     Σ_k pO[k,l,t] ≤ max_cap[l] × (1 - S × zO[l,t])    ∀ l,t
    for l in L_OTD:
        for t in days:
            prod_on_line = [pO[k, l, t] for k in K
                           if (k, l, t) in pO]
            if prod_on_line:
                solver.Add(
                    sum(prod_on_line)
                    <= max_cap[l] * (1 - SETUP_LOSS * zO[l, t]))

    # (5) MD hat kapasitesi — her hatta günlük üst sınır.
    #     Σ_k pM[k,m,t] ≤ max_tempo_md[m]    ∀ m,t
    for m in L_MD:
        for t in days:
            prod_md = [pM[k, m, t] for k in K_MD if (k, m, t) in pM]
            if prod_md:
                max_md = max(tempo_md.get((kk, m), 0) for kk in K_MD)
                solver.Add(sum(prod_md) <= max_md)

    # (6) TA kapasite → değişken üst sınırında (pT tanımında)

    # (7) Tampon stok denge — KSO
    #     K_MD kartları : KSO[k,t] = KSO[k,t-1] + Σ_l pO[k,l,t] - Σ_m pM[k,m,t]
    #     K_SKIP kartları: KSO[k,t] = KSO[k,t-1] + Σ_l pO[k,l,t] - pT[k,t]
    for k in K:
        for t in days:
            otd_prod = sum(pO[k, l, t] for l in L_OTD
                          if (k, l, t) in pO)
            prev_kso = KSO[k, t - 1] if t > 0 else init_kso.get(k, 0)

            if k in K_MD:
                md_cons = sum(pM[k, m, t] for m in L_MD
                              if (k, m, t) in pM)
                solver.Add(KSO[k, t] == prev_kso + otd_prod - md_cons)
            else:
                solver.Add(KSO[k, t] == prev_kso + otd_prod - pT[k, t])

    # (8) Tampon stok denge — KSM (sadece K_MD)
    #     KSM[k,t] = KSM[k,t-1] + Σ_m pM[k,m,t] - pT[k,t]
    for k in K_MD:
        for t in days:
            md_prod = sum(pM[k, m, t] for m in L_MD
                         if (k, m, t) in pM)
            prev_ksm = KSM[k, t - 1] if t > 0 else init_ksm.get(k, 0)
            solver.Add(KSM[k, t] == prev_ksm + md_prod - pT[k, t])

    # (9) Tampon stok denge — KST
    #     KST[k,t] = KST[k,t-1] + pT[k,t] - demand[k,t]
    for k in K:
        for t in days:
            prev_kst = KST[k, t - 1] if t > 0 else init_kst.get(k, 0)
            solver.Add(KST[k, t] == prev_kst + pT[k, t]
                       - demand.get((k, t), 0))

    # ── AMAÇ FONKSİYONU ────────────────────────────────────────────
    # Ağırlıklı tek-fazlı: W_SETUP × Σ zO  +  Σ (KSO + KSM + KST)
    # W_SETUP >> buffer toplamı olduğundan leksikografik etki sağlanır.
    total_setups_expr = sum(zO[l, t] for l in L_OTD for t in days)
    total_buffer_expr = (
        sum(KSO[k, t] for k in K for t in days)
        + sum(KSM[k, t] for k in K_MD for t in days)
        + sum(KST[k, t] for k in K for t in days)
    )

    solver.Minimize(W_SETUP * total_setups_expr + total_buffer_expr)

    # ── ÇÖZ ────────────────────────────────────────────────────────
    status = solver.Solve()

    if status not in (pywraplp.Solver.OPTIMAL,
                      pywraplp.Solver.FEASIBLE):
        return {
            "status": "INFEASIBLE",
            "message": (
                "Fizibil çözüm bulunamadı. Olası nedenler:\n"
                "• Yetersiz OTD kapasitesi (tempo → hat uyumsuzluğu)\n"
                "• TA fikstur darboğazı (MR: 100/gün dikkat)\n"
                "• Toplam montaj talebi mevcut kapasiteyi aşıyor\n"
                "• Başlangıç stokları yetersiz (KST < ilk günlerin talebi)"
            ),
        }

    # ═════════════════════════════════════════════════════════════════
    #  SONUÇLARI TOPLA
    # ═════════════════════════════════════════════════════════════════
    status_map = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
    }

    # OTD Alokasyon planı
    plan_otd = {}
    for l in L_OTD:
        for t in days:
            assigned = None
            for k in K:
                if (k, l, t) in yO and yO[k, l, t].solution_value() > 0.5:
                    assigned = k
                    break
            plan_otd[(l, t)] = assigned

    # OTD Üretim
    prod_otd = {}
    for (k, l, t), var in pO.items():
        val = var.solution_value()
        if val > 0.5:
            prod_otd[(k, l, t)] = round(val)

    # MD Üretim
    prod_md = {}
    for (k, m, t), var in pM.items():
        val = var.solution_value()
        if val > 0.5:
            prod_md[(k, m, t)] = round(val)

    # TA Üretim
    prod_ta = {}
    for (k, t), var in pT.items():
        val = var.solution_value()
        if val > 0.5:
            prod_ta[(k, t)] = round(val)

    # Setup günleri
    setups = {}
    for (l, t), var in zO.items():
        if var.solution_value() > 0.5:
            setups[(l, t)] = True

    # Tampon stoklar
    stocks_kso = {(k, t): round(KSO[k, t].solution_value())
                  for k in K for t in days}
    stocks_ksm = {(k, t): round(KSM[k, t].solution_value())
                  for k in K_MD for t in days}
    stocks_kst = {(k, t): round(KST[k, t].solution_value())
                  for k in K for t in days}

    # Özet metrikler
    total_setups = sum(1 for v in zO.values()
                       if v.solution_value() > 0.5)
    total_buffer = round(total_buffer_expr.solution_value()
                         if hasattr(total_buffer_expr, 'solution_value')
                         else sum(stocks_kso.values())
                              + sum(stocks_ksm.values())
                              + sum(stocks_kst.values()))

    return {
        "status": status_map.get(status, "UNKNOWN"),
        "total_setups": total_setups,
        "total_buffer": total_buffer,
        "plan_otd": {f"{l}|{t}": v for (l, t), v in plan_otd.items()},
        "prod_otd": {f"{k}|{l}|{t}": v
                     for (k, l, t), v in prod_otd.items()},
        "prod_md":  {f"{k}|{m}|{t}": v
                     for (k, m, t), v in prod_md.items()},
        "prod_ta":  {f"{k}|{t}": v for (k, t), v in prod_ta.items()},
        "setups":   {f"{l}|{t}": True for (l, t) in setups},
        "stocks_kso": {f"{k}|{t}": v
                       for (k, t), v in stocks_kso.items()},
        "stocks_ksm": {f"{k}|{t}": v
                       for (k, t), v in stocks_ksm.items()},
        "stocks_kst": {f"{k}|{t}": v
                       for (k, t), v in stocks_kst.items()},
        "solve_time_sec": round(solver.wall_time() / 1000, 2),
        "num_variables": solver.NumVariables(),
        "num_constraints": solver.NumConstraints(),
        "objective_value": round(solver.Objective().Value()),
        "w_setup": W_SETUP,
    }


# ─────────────────────────────────────────────────────────────────────
#  MODÜL TESTİ
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Minimal test verisi (2 kart, 2 hat, 3 gün)
    test_data = {
        "kartlar":      ["XC", "XR"],
        "kartlar_md":   [],
        "kartlar_skip": ["XC", "XR"],
        "otd_lines":    ["OD0", "OD2"],
        "md_lines":     ["MD1", "MD2"],
        "T": 3,
        "tempo_otd": {
            ("XC", "OD0"): 1000, ("XR", "OD0"): 900,
            ("XC", "OD2"): 1000, ("XR", "OD2"): 900,
        },
        "tempo_md": {},
        "ta_cap": {
            ("XC", 0): 800, ("XC", 1): 800, ("XC", 2): 800,
            ("XR", 0): 700, ("XR", 1): 700, ("XR", 2): 700,
        },
        "demand": {
            ("XC", 0): 400, ("XC", 1): 400, ("XC", 2): 400,
            ("XR", 0): 300, ("XR", 1): 300, ("XR", 2): 300,
        },
        "init_kso": {"XC": 500, "XR": 400},
        "init_ksm": {},
        "init_kst": {"XC": 200, "XR": 150},
    }

    result = solve(test_data, time_limit_sec=30)
    print(f"Durum    : {result['status']}")
    print(f"Setup    : {result.get('total_setups', '—')}")
    print(f"Buffer   : {result.get('total_buffer', '—')}")
    print(f"Süre     : {result.get('solve_time_sec', '—')}s")
