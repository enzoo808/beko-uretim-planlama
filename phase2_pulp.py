"""
phase2_pulp.py — Hibrit Çözücü FAZ 2 (PuLP + CBC)
==================================================
Görev   : Faz 1'in sabitlediği atamalar altında, sürekli üretim ve
          tampon stok değişkenlerini optimize etmek.
Girdi   : Faz 1'den gelen yO_fixed, zO_fixed, yM_fixed, zM_fixed
Çıktı   : xO, xM, xT, KSO, KSM, KST (sürekli) + buffer optimize sonuç

Bu faz, PuLP+CBC'nin güçlü olduğu yere odaklanır:
  - Saf LP (atamalar sabit, yalnızca sürekli karar değişkenleri kaldı)
  - Lineer hedef (Σ KSO + Σ KSM + Σ KST minimize)
  - CBC'nin simplex tabanlı hızı

Akademik gerekçe (tezde geçecek):
  Atamalar binary ve combinatorial → SCIP (Faz 1) güçlü.
  Atamalar sabitlenince problem saf LP'ye iner → CBC (Faz 2) güçlü.
  İki açık-kaynak çözücüyü problem yapısına göre bölüştürmek
  leksikografik kaliteyi korurken çözüm süresini düşürür.

Yazar   : Mehmet Ensar & Ege — YTÜ Endüstri Müh. Bitirme Projesi
"""

from __future__ import annotations
import pulp
from typing import Any

S_OTD = 0.50   # OTD setup kapasite kaybı (Faz 1 ile aynı sabit)
S_MD  = 0.05   # MD  setup kapasite kaybı


def solve_phase2(data: dict[str, Any],
                 phase1_result: dict[str, Any],
                 time_limit_sec: int = 60) -> dict[str, Any]:
    """
    Faz 2: Atamalar sabit, üretim ve buffer'lar değişken.
    Tek amaç: toplam tampon stoku (KSO + KSM + KST) minimize et.
    Faz 1'in setup sayısı (z_star) doğal olarak korunur, çünkü
    yO_fixed ve zO_fixed parametre olarak gelir — değişmez.
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

    yO_fix = phase1_result["yO_fixed"]    # {(k,l,t): 1}
    zO_fix = phase1_result["zO_fixed"]    # {(l,t): 1}
    yM_fix = phase1_result["yM_fixed"]    # {(k,m,t): 1}
    zM_fix = phase1_result["zM_fixed"]    # {(m,t): 1}

    prob = pulp.LpProblem("Beko_Hybrid_Phase2", pulp.LpMinimize)

    # --- Sürekli karar değişkenleri ---
    # xO[k,l,t]: OTD üretimi (yO=1 olan hücrelerde tempo·(1-S·zO) ile sınırlı)
    xO = {}
    for (k, l, t), _ in yO_fix.items():
        cap = tempo_otd[(k, l)]
        is_setup = (l, t) in zO_fix
        ub = cap * (1 - S_OTD) if is_setup else cap
        xO[k, l, t] = pulp.LpVariable(f"xO_{k}_{l}_{t}",
                                       lowBound=0, upBound=ub)

    # xM[k,m,t]: MD üretimi (yM=1 olan hücrelerde tempo ile sınırlı)
    xM = {}
    for (k, m, t), _ in yM_fix.items():
        cap = tempo_md[(k, m)]
        xM[k, m, t] = pulp.LpVariable(f"xM_{k}_{m}_{t}",
                                       lowBound=0, upBound=cap)

    # xT[k,t]: TA üretimi
    xT = {(k, t): pulp.LpVariable(f"xT_{k}_{t}",
                                   lowBound=0,
                                   upBound=ta_cap.get((k, t), 0))
          for k in K for t in days}

    # Tampon stoklar — sert non-negatif kısıt (lowBound=0)
    KSO = {(k, t): pulp.LpVariable(f"KSO_{k}_{t}", lowBound=0)
           for k in K for t in days}
    KSM = {(k, t): pulp.LpVariable(f"KSM_{k}_{t}", lowBound=0)
           for k in K_MD for t in days}
    KST = {(k, t): pulp.LpVariable(f"KST_{k}_{t}", lowBound=0)
           for k in K for t in days}

    # --- Yardımcı toplamlar ---
    def otd_prod(k, t):
        return pulp.lpSum(xO[k, l, t] for l in L_OTD if (k, l, t) in xO)

    def md_prod(k, t):
        return pulp.lpSum(xM[k, m, t] for m in L_MD if (k, m, t) in xM)

    # --- (P2.1)–(P2.3) MD paylasimli kapasite (aynı hatta çakışma yok) ---
    # Faz 1 zaten "bir kart/hat/gün" garantisi vermiş; ek kısıt gerekmez.

    # --- (P2.4) KSO denge ---
    for k in K:
        for t in days:
            prev = KSO[k, t-1] if t > 0 else init_kso.get(k, 0)
            if k in K_MD:
                prob += (KSO[k, t] == prev + otd_prod(k, t) - md_prod(k, t),
                         f"denge_KSO_md_{k}_{t}")
            else:
                prob += (KSO[k, t] == prev + otd_prod(k, t) - xT[k, t],
                         f"denge_KSO_skip_{k}_{t}")

    # --- (P2.5) KSM denge ---
    for k in K_MD:
        for t in days:
            prev = KSM[k, t-1] if t > 0 else init_ksm.get(k, 0)
            prob += (KSM[k, t] == prev + md_prod(k, t) - xT[k, t],
                     f"denge_KSM_{k}_{t}")

    # --- (P2.6) KST denge ---
    for k in K:
        for t in days:
            prev = KST[k, t-1] if t > 0 else init_kst.get(k, 0)
            prob += (KST[k, t] == prev + xT[k, t] - demand.get((k, t), 0),
                     f"denge_KST_{k}_{t}")

    # --- (P2.OBJ) Amaç: toplam tampon stok minimize ---
    total_buf = (pulp.lpSum(KSO[k, t] for k in K for t in days)
                 + pulp.lpSum(KSM[k, t] for k in K_MD for t in days)
                 + pulp.lpSum(KST[k, t] for k in K for t in days))
    prob += total_buf

    cbc = pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit_sec)
    prob.solve(cbc)

    if prob.status != pulp.constants.LpStatusOptimal:
        # CBC zaman aşımıyla durabilir ama feasible bulmuş olabilir
        if pulp.value(prob.objective) is None:
            return {"status": "INFEASIBLE",
                    "message": "Faz 2: LP fizibil çözüm üretemedi."}

    # --- Sonuç çıkarımı ---
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

    return {
        "status": "OPTIMAL" if prob.status == pulp.LpStatusOptimal else "FEASIBLE",
        "phase2_buffer": int(sum(sk_kso.values()) + sum(sk_ksm.values()) + sum(sk_kst.values())),
        "phase2_solve_time": round(prob.solutionTime, 2),
        "phase2_num_vars": len(prob.variables()),
        "phase2_num_cons": len(prob.constraints),
        # Üretim sonuçları
        "prod_otd": r_prod_otd,
        "prod_md":  r_prod_md,
        "prod_ta":  r_prod_ta,
        # Stoklar
        "stocks_kso": sk_kso,
        "stocks_ksm": sk_ksm,
        "stocks_kst": sk_kst,
    }
