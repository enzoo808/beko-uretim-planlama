"""
optimizer.py — Beko TV Anakart Üretim Planlama MILP Modeli
===========================================================
Çözücü  : Google OR-Tools (pywraplp) + SCIP
Yapı    : CLSP-SI (Capacitated Lot Sizing Problem – Setup & Inventory)
Amaç    : Leksikografik iki fazlı optimizasyon
            Faz 1 → Setup sayısını minimize et  (Σ zO)
            Faz 2 → Toplam tampon stoğu minimize et  (Σ KSO + KSM + KST)
                     s.t.  Σ zO ≤ z*

Mimari  : Streamlit veya herhangi bir UI bağımlılığı YOKTUR.
          Parametreleri dışarıdan dict olarak alır, sonucu dict olarak döner.

Yazar   : Mehmet Ensar & Ege — YTÜ Endüstri Mühendisliği Bitirme Projesi
Danışman: Prof. Dr. Nihan Çetin Demirel
"""

from __future__ import annotations
from ortools.linear_solver import pywraplp
from typing import Any


# ─────────────────────────────────────────────────────────────────────
#  SABİTLER
# ─────────────────────────────────────────────────────────────────────
SETUP_LOSS = 0.50          # Kart değişimi → günlük kapasitenin %50'si kayıp
BIG_M      = 1_000_000     # Büyük-M sabiti (lineerleştirme)
SOLVER_ID  = "SCIP"        # OR-Tools MIP back-end


# ─────────────────────────────────────────────────────────────────────
#  ANA ÇÖZÜM FONKSİYONU
# ─────────────────────────────────────────────────────────────────────
def solve(data: dict[str, Any],
          time_limit_sec: int = 120) -> dict[str, Any]:
    """
    Parametreler
    ------------
    data : dict  — Aşağıdaki anahtarları içermeli:
        kartlar         : list[str]          — 14 kart tipi kodu
        kartlar_md      : list[str]          — MD'den geçen 9 kart
        kartlar_skip    : list[str]          — MD'yi atlayan 5 kart
        otd_lines       : list[str]          — OTD hat isimleri  (7 hat)
        md_lines        : list[str]          — MD hat isimleri   (2 hat)
        T               : int                — Planlama ufku (gün sayısı, ör: 14)
        tempo_otd       : dict[(k,l), float] — OTD tempoları
        tempo_md        : dict[(k,m), float] — MD tempoları
        ta_cap          : dict[(k,t), float] — TA günlük kapasite (fikstur bazlı)
        demand          : dict[(k,t), float] — Montaj talebi
        init_kso        : dict[k, float]     — OTD sonrası başlangıç stoku
        init_ksm        : dict[k, float]     — MD sonrası başlangıç stoku
        init_kst        : dict[k, float]     — TA sonrası başlangıç stoku
        ref_otd_alloc   : dict[(l,t), str|None] — Referans OTD alokasyonu (opsiyonel)

    time_limit_sec : int  — Her faz için çözücü zaman limiti (saniye)

    Dönüş
    ------
    dict  — status, phase1_setups, phase2_buffer, plan_otd, plan_md,
            plan_ta, stocks_kso, stocks_ksm, stocks_kst, ...
    """

    # ── Veri çözümleme ──────────────────────────────────────────────
    K       = data["kartlar"]
    K_MD    = data["kartlar_md"]
    K_SKIP  = data["kartlar_skip"]
    L_OTD   = data["otd_lines"]
    L_MD    = data["md_lines"]
    T       = data["T"]
    days    = list(range(T))

    tempo_otd = data["tempo_otd"]    # (k, l) → float
    tempo_md  = data["tempo_md"]     # (k, m) → float
    ta_cap    = data["ta_cap"]       # (k, t) → float
    demand    = data["demand"]       # (k, t) → float
    init_kso  = data["init_kso"]     # k → float
    init_ksm  = data["init_ksm"]     # k → float
    init_kst  = data["init_kst"]     # k → float

    # Her OTD hattının günlük maksimum kapasitesi (en yüksek tempo)
    max_cap = {}
    for l in L_OTD:
        caps = [tempo_otd.get((k, l), 0) for k in K]
        max_cap[l] = max(caps) if caps else 0

    # ═════════════════════════════════════════════════════════════════
    #  FAZ 1 — SETUP SAYISINI MİNİMİZE ET
    # ═════════════════════════════════════════════════════════════════
    s1 = pywraplp.Solver.CreateSolver(SOLVER_ID)
    if not s1:
        return {"status": "ERROR", "message": "SCIP çözücüsü bulunamadı."}

    s1.SetTimeLimit(time_limit_sec * 1000)
    infinity = s1.infinity()

    # ── Karar Değişkenleri ──────────────────────────────────────────

    # yO[k,l,t] ∈ {0,1} — Kart k, OTD hattı l, gün t'de üretiliyor mu?
    yO = {}
    for k in K:
        for l in L_OTD:
            for t in days:
                if tempo_otd.get((k, l), 0) > 0:
                    yO[k, l, t] = s1.BoolVar(f"yO_{k}_{l}_{t}")

    # zO[l,t] ∈ {0,1} — OTD hattı l'de gün t'de setup var mı?
    zO = {}
    for l in L_OTD:
        for t in days:
            zO[l, t] = s1.BoolVar(f"zO_{l}_{t}")

    # pO[k,l,t] ≥ 0 — OTD üretim miktarı
    pO = {}
    for k in K:
        for l in L_OTD:
            for t in days:
                if tempo_otd.get((k, l), 0) > 0:
                    pO[k, l, t] = s1.NumVar(
                        0, tempo_otd[(k, l)], f"pO_{k}_{l}_{t}")

    # pM[k,m,t] ≥ 0 — MD üretim miktarı (sadece K_MD kartları)
    pM = {}
    for k in K_MD:
        for m in L_MD:
            for t in days:
                cap = tempo_md.get((k, m), 0)
                if cap > 0:
                    pM[k, m, t] = s1.NumVar(0, cap, f"pM_{k}_{m}_{t}")

    # pT[k,t] ≥ 0 — TA üretim miktarı
    pT = {}
    for k in K:
        for t in days:
            cap = ta_cap.get((k, t), 0)
            pT[k, t] = s1.NumVar(0, cap, f"pT_{k}_{t}")

    # KSO[k,t] ≥ 0 — OTD → (MD veya TA) tampon stoku
    KSO = {}
    for k in K:
        for t in days:
            KSO[k, t] = s1.NumVar(0, infinity, f"KSO_{k}_{t}")

    # KSM[k,t] ≥ 0 — MD → TA tampon stoku (sadece K_MD)
    KSM = {}
    for k in K_MD:
        for t in days:
            KSM[k, t] = s1.NumVar(0, infinity, f"KSM_{k}_{t}")

    # KST[k,t] ≥ 0 — TA → Montaj tampon stoku
    KST = {}
    for k in K:
        for t in days:
            KST[k, t] = s1.NumVar(0, infinity, f"KST_{k}_{t}")

    # ── KISITLAR ────────────────────────────────────────────────────

    # (1) Bir OTD hattında günde en fazla bir kart tipi üretilebilir.
    #     Σ_k yO[k,l,t] ≤ 1    ∀ l ∈ L_OTD, t ∈ T
    for l in L_OTD:
        for t in days:
            cards_on_line = [yO[k, l, t] for k in K
                            if (k, l, t) in yO]
            if cards_on_line:
                s1.Add(sum(cards_on_line) <= 1,
                       f"C1_one_card_per_line_{l}_{t}")

    # (2) OTD üretim, alokasyona bağlıdır (big-M lineerleştirme).
    #     pO[k,l,t] ≤ tempo[k,l] × yO[k,l,t]    ∀ k,l,t
    for (k, l, t), var in pO.items():
        s1.Add(var <= tempo_otd[(k, l)] * yO[k, l, t],
               f"C2_otd_cap_{k}_{l}_{t}")

    # (3) Setup tespiti — gün t'de hat l'ye farklı bir kart atandıysa
    #     setup tetiklenir.
    #     zO[l,t] ≥ yO[k,l,t] - yO[k,l,t-1]    ∀ k,l,  t > 0
    for l in L_OTD:
        for t in days:
            if t == 0:
                # İlk gün: referans plan yoksa her atama setup sayılır
                for k in K:
                    if (k, l, t) in yO:
                        s1.Add(zO[l, t] >= yO[k, l, t],
                               f"C3_setup_day0_{k}_{l}")
            else:
                for k in K:
                    if (k, l, t) in yO:
                        prev = yO.get((k, l, t - 1))
                        if prev is not None:
                            s1.Add(zO[l, t] >= yO[k, l, t] - prev,
                                   f"C3_setup_{k}_{l}_{t}")
                        else:
                            # Kart bu hatta dün atanamaz → bugün atanırsa setup
                            s1.Add(zO[l, t] >= yO[k, l, t],
                                   f"C3_setup_new_{k}_{l}_{t}")

    # (4) Setup kaybı — setup olan günde hat kapasitesi %50 azalır.
    #     Σ_k pO[k,l,t] ≤ max_cap[l] × (1 - S × zO[l,t])
    for l in L_OTD:
        for t in days:
            prod_on_line = [pO[k, l, t] for k in K
                           if (k, l, t) in pO]
            if prod_on_line:
                s1.Add(
                    sum(prod_on_line)
                    <= max_cap[l] * (1 - SETUP_LOSS * zO[l, t]),
                    f"C4_setup_loss_{l}_{t}")

    # (5) MD hattında günde en fazla bir kart (basitleştirme: ayrı yM
    #     binary kullanılabilir, burada kapasite ile kontrol ediyoruz).
    #     Σ_k pM[k,m,t] ≤ max_md_cap[m]    ∀ m,t
    for m in L_MD:
        for t in days:
            prod_md = [pM[k, m, t] for k in K_MD
                       if (k, m, t) in pM]
            if prod_md:
                max_md = max(tempo_md.get((k, m), 0) for k in K_MD)
                s1.Add(sum(prod_md) <= max_md,
                       f"C5_md_cap_{m}_{t}")

    # (6) TA günlük kapasite kısıtı (fikstur bazlı).
    #     pT[k,t] ≤ ta_cap[k,t]    ∀ k,t
    #     (Zaten değişken üst sınırı olarak tanımlandı, ek kısıt gerekmez.)

    # (7) Tampon stok denge denklemleri — OTD sonrası (KSO)
    for k in K:
        for t in days:
            # Toplam OTD üretimi
            otd_prod = sum(pO[k, l, t] for l in L_OTD
                          if (k, l, t) in pO)
            # Önceki stok
            prev_kso = KSO[k, t - 1] if t > 0 else init_kso.get(k, 0)

            if k in K_MD:
                # MD kartları: KSO çıkışı = MD girişi
                md_consumption = sum(pM[k, m, t] for m in L_MD
                                     if (k, m, t) in pM)
                s1.Add(KSO[k, t] == prev_kso + otd_prod - md_consumption,
                       f"C7a_kso_md_{k}_{t}")
            else:
                # Skip kartlar: KSO çıkışı = TA girişi
                s1.Add(KSO[k, t] == prev_kso + otd_prod - pT[k, t],
                       f"C7b_kso_skip_{k}_{t}")

    # (8) Tampon stok denge — MD sonrası (KSM), sadece K_MD
    for k in K_MD:
        for t in days:
            md_prod = sum(pM[k, m, t] for m in L_MD
                         if (k, m, t) in pM)
            prev_ksm = KSM[k, t - 1] if t > 0 else init_ksm.get(k, 0)
            s1.Add(KSM[k, t] == prev_ksm + md_prod - pT[k, t],
                   f"C8_ksm_{k}_{t}")

    # (9) Tampon stok denge — TA sonrası (KST)
    for k in K:
        for t in days:
            prev_kst = KST[k, t - 1] if t > 0 else init_kst.get(k, 0)
            s1.Add(KST[k, t] == prev_kst + pT[k, t]
                   - demand.get((k, t), 0),
                   f"C9_kst_{k}_{t}")

    # ── Faz 1 Amaç Fonksiyonu ──────────────────────────────────────
    #     min  Σ_{l,t} zO[l,t]
    obj1 = sum(zO[l, t] for l in L_OTD for t in days)
    s1.Minimize(obj1)

    # ── Çöz ─────────────────────────────────────────────────────────
    status1 = s1.Solve()

    if status1 not in (pywraplp.Solver.OPTIMAL,
                       pywraplp.Solver.FEASIBLE):
        return {
            "status": "INFEASIBLE",
            "phase": 1,
            "message": (
                "Faz 1 (setup minimizasyonu) fizibil çözüm bulamadı. "
                "Olası nedenler: yetersiz OTD kapasitesi, negatife düşen "
                "tampon stok veya tutarsız TA fikstur verisi."
            ),
        }

    z_star = int(round(s1.Objective().Value()))

    # ═════════════════════════════════════════════════════════════════
    #  FAZ 2 — TOPLAM TAMPON STOĞU MİNİMİZE ET  (setup ≤ z*)
    # ═════════════════════════════════════════════════════════════════
    s2 = pywraplp.Solver.CreateSolver(SOLVER_ID)
    if not s2:
        return {"status": "ERROR", "message": "Faz 2 için SCIP başlatılamadı."}

    s2.SetTimeLimit(time_limit_sec * 1000)
    inf2 = s2.infinity()

    # ── Değişkenler (aynı yapı, yeni solver instance) ───────────────
    yO2, zO2, pO2, pM2, pT2 = {}, {}, {}, {}, {}
    KSO2, KSM2, KST2 = {}, {}, {}

    for k in K:
        for l in L_OTD:
            for t in days:
                if tempo_otd.get((k, l), 0) > 0:
                    yO2[k, l, t] = s2.BoolVar(f"yO_{k}_{l}_{t}")
                    pO2[k, l, t] = s2.NumVar(
                        0, tempo_otd[(k, l)], f"pO_{k}_{l}_{t}")

    for l in L_OTD:
        for t in days:
            zO2[l, t] = s2.BoolVar(f"zO_{l}_{t}")

    for k in K_MD:
        for m in L_MD:
            for t in days:
                cap = tempo_md.get((k, m), 0)
                if cap > 0:
                    pM2[k, m, t] = s2.NumVar(0, cap, f"pM_{k}_{m}_{t}")

    for k in K:
        for t in days:
            cap = ta_cap.get((k, t), 0)
            pT2[k, t] = s2.NumVar(0, cap, f"pT_{k}_{t}")
            KSO2[k, t] = s2.NumVar(0, inf2, f"KSO_{k}_{t}")
            KST2[k, t] = s2.NumVar(0, inf2, f"KST_{k}_{t}")

    for k in K_MD:
        for t in days:
            KSM2[k, t] = s2.NumVar(0, inf2, f"KSM_{k}_{t}")

    # ── Kısıtlar (birebir aynı — C1-C9) ────────────────────────────
    _add_constraints(s2, K, K_MD, K_SKIP, L_OTD, L_MD, days,
                     yO2, zO2, pO2, pM2, pT2,
                     KSO2, KSM2, KST2,
                     tempo_otd, tempo_md, ta_cap, demand,
                     init_kso, init_ksm, init_kst, max_cap)

    # (10) Epsilon kısıtı — toplam setup ≤ z*
    s2.Add(sum(zO2[l, t] for l in L_OTD for t in days) <= z_star,
           "C10_epsilon_setup")

    # ── Faz 2 Amaç Fonksiyonu ──────────────────────────────────────
    #     min  Σ_{k,t} ( KSO[k,t] + KST[k,t] ) + Σ_{k∈K_MD,t} KSM[k,t]
    obj2 = (sum(KSO2[k, t] for k in K for t in days)
            + sum(KSM2[k, t] for k in K_MD for t in days)
            + sum(KST2[k, t] for k in K for t in days))
    s2.Minimize(obj2)

    # ── Çöz ─────────────────────────────────────────────────────────
    status2 = s2.Solve()

    if status2 not in (pywraplp.Solver.OPTIMAL,
                       pywraplp.Solver.FEASIBLE):
        return {
            "status": "INFEASIBLE",
            "phase": 2,
            "message": (
                f"Faz 2 (tampon minimizasyonu) fizibil değil. "
                f"Faz 1 z*={z_star} ile devam edilemedi."
            ),
        }

    # ═════════════════════════════════════════════════════════════════
    #  SONUÇLARI TOPLA
    # ═════════════════════════════════════════════════════════════════
    result = _extract_results(
        s2, K, K_MD, K_SKIP, L_OTD, L_MD, days,
        yO2, zO2, pO2, pM2, pT2,
        KSO2, KSM2, KST2,
        z_star, status2)

    return result


# ─────────────────────────────────────────────────────────────────────
#  YARDIMCI: Kısıt ekleme (Faz 2'de tekrar kullanım için)
# ─────────────────────────────────────────────────────────────────────
def _add_constraints(solver, K, K_MD, K_SKIP, L_OTD, L_MD, days,
                     yO, zO, pO, pM, pT,
                     KSO, KSM, KST,
                     tempo_otd, tempo_md, ta_cap, demand,
                     init_kso, init_ksm, init_kst, max_cap):
    """Faz 1 ile birebir aynı kısıtları (C1–C9) verilen solver'a ekler."""

    # (C1) Bir OTD hattında günde en fazla bir kart
    for l in L_OTD:
        for t in days:
            cards = [yO[k, l, t] for k in K if (k, l, t) in yO]
            if cards:
                solver.Add(sum(cards) <= 1)

    # (C2) OTD üretim ≤ tempo × alokasyon
    for (k, l, t), var in pO.items():
        solver.Add(var <= tempo_otd[(k, l)] * yO[k, l, t])

    # (C3) Setup tespiti
    for l in L_OTD:
        for t in days:
            if t == 0:
                for k in K:
                    if (k, l, t) in yO:
                        solver.Add(zO[l, t] >= yO[k, l, t])
            else:
                for k in K:
                    if (k, l, t) in yO:
                        prev = yO.get((k, l, t - 1))
                        if prev is not None:
                            solver.Add(zO[l, t] >= yO[k, l, t] - prev)
                        else:
                            solver.Add(zO[l, t] >= yO[k, l, t])

    # (C4) Setup kaybı — kapasite %50 azalır
    for l in L_OTD:
        for t in days:
            prod = [pO[k, l, t] for k in K if (k, l, t) in pO]
            if prod:
                solver.Add(
                    sum(prod) <= max_cap[l] * (1 - SETUP_LOSS * zO[l, t]))

    # (C5) MD hat kapasitesi
    for m in L_MD:
        for t in days:
            prod_md = [pM[k, m, t] for k in K_MD if (k, m, t) in pM]
            if prod_md:
                max_md = max(tempo_md.get((k, m), 0) for k in K_MD)
                solver.Add(sum(prod_md) <= max_md)

    # (C7) KSO denge
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

    # (C8) KSM denge (sadece K_MD)
    for k in K_MD:
        for t in days:
            md_prod = sum(pM[k, m, t] for m in L_MD
                         if (k, m, t) in pM)
            prev_ksm = KSM[k, t - 1] if t > 0 else init_ksm.get(k, 0)
            solver.Add(KSM[k, t] == prev_ksm + md_prod - pT[k, t])

    # (C9) KST denge
    for k in K:
        for t in days:
            prev_kst = KST[k, t - 1] if t > 0 else init_kst.get(k, 0)
            solver.Add(KST[k, t] == prev_kst + pT[k, t]
                       - demand.get((k, t), 0))


# ─────────────────────────────────────────────────────────────────────
#  YARDIMCI: Sonuç çıkarma
# ─────────────────────────────────────────────────────────────────────
def _extract_results(solver, K, K_MD, K_SKIP, L_OTD, L_MD, days,
                     yO, zO, pO, pM, pT,
                     KSO, KSM, KST,
                     z_star, solve_status):
    """Faz 2 çözümünden sonuç sözlüğünü üretir."""

    status_map = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
    }

    # ── OTD Alokasyon planı: {(l, t): kart_kodu veya None} ─────────
    plan_otd = {}
    for l in L_OTD:
        for t in days:
            assigned = None
            for k in K:
                if (k, l, t) in yO and yO[k, l, t].solution_value() > 0.5:
                    assigned = k
                    break
            plan_otd[(l, t)] = assigned

    # ── OTD Üretim miktarları ───────────────────────────────────────
    prod_otd = {}
    for (k, l, t), var in pO.items():
        val = var.solution_value()
        if val > 0.5:
            prod_otd[(k, l, t)] = round(val)

    # ── MD Üretim miktarları ────────────────────────────────────────
    prod_md = {}
    for (k, m, t), var in pM.items():
        val = var.solution_value()
        if val > 0.5:
            prod_md[(k, m, t)] = round(val)

    # ── TA Üretim miktarları ────────────────────────────────────────
    prod_ta = {}
    for (k, t), var in pT.items():
        val = var.solution_value()
        if val > 0.5:
            prod_ta[(k, t)] = round(val)

    # ── Setup günleri ───────────────────────────────────────────────
    setups = {}
    for (l, t), var in zO.items():
        if var.solution_value() > 0.5:
            setups[(l, t)] = True

    # ── Tampon stoklar ──────────────────────────────────────────────
    stocks_kso = {(k, t): round(KSO[k, t].solution_value())
                  for k in K for t in days}
    stocks_ksm = {(k, t): round(KSM[k, t].solution_value())
                  for k in K_MD for t in days}
    stocks_kst = {(k, t): round(KST[k, t].solution_value())
                  for k in K for t in days}

    # ── Özet metrikler ──────────────────────────────────────────────
    total_buffer = solver.Objective().Value()
    total_setups = sum(1 for v in zO.values()
                       if v.solution_value() > 0.5)

    return {
        "status": status_map.get(solve_status, "UNKNOWN"),
        "phase1_setups": z_star,
        "phase2_setups": total_setups,
        "phase2_total_buffer": round(total_buffer),
        "plan_otd": {f"{l}|{t}": v for (l, t), v in plan_otd.items()},
        "prod_otd": {f"{k}|{l}|{t}": v for (k, l, t), v in prod_otd.items()},
        "prod_md":  {f"{k}|{m}|{t}": v for (k, m, t), v in prod_md.items()},
        "prod_ta":  {f"{k}|{t}": v for (k, t), v in prod_ta.items()},
        "setups":   {f"{l}|{t}": True for (l, t) in setups},
        "stocks_kso": {f"{k}|{t}": v for (k, t), v in stocks_kso.items()},
        "stocks_ksm": {f"{k}|{t}": v for (k, t), v in stocks_ksm.items()},
        "stocks_kst": {f"{k}|{t}": v for (k, t), v in stocks_kst.items()},
        "solve_time_sec": round(solver.wall_time() / 1000, 2),
        "num_variables": solver.NumVariables(),
        "num_constraints": solver.NumConstraints(),
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
    print(f"\nDurum     : {result['status']}")
    print(f"Faz 1 z*  : {result.get('phase1_setups', '—')}")
    print(f"Faz 2 buf : {result.get('phase2_total_buffer', '—')}")
    print(f"Süre      : {result.get('solve_time_sec', '—')}s")
    print(f"Değişken  : {result.get('num_variables', '—')}")
    print(f"Kısıt     : {result.get('num_constraints', '—')}")
