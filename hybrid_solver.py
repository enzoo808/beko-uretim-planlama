"""
hybrid_solver.py — Hibrit Çözücü Orkestrasyon
==============================================
İki açık-kaynak çözücüyü problem yapısına göre bölüştürür:

  FAZ 1 (OR-Tools pywraplp / CBC, phase1_ortools.py)
     → İkili atama kararları: yO, zO, yM, zM
     → Hedef: min Σ zO (yalnız OTD setup — Tez Bölüm 3.5)
     → Güçlü yan: combinatorial branch-and-cut
     → NOT: SCIP Streamlit Cloud'da yok; CBC kullanılır.

  FAZ 2 (PuLP / CBC, phase2_pulp.py)
     → Sürekli karar değişkenleri: xO, xM, xT, KSO, KSM, KST
     → Atamalar Faz 1'den SABİT parametre olarak gelir
     → Hedef: min (100·bant + 50·alt_band + 1·buffer) — yumuşak hedefler
     → Hard: KSO/KSM/KST ≥ 0 ve günlük OTD ≤ daily_total_max
     → Güçlü yan: saf LP simplex hızı

Bu modül, app.py'ın eskiden optimizer.solve(data, time_limit) ile
çağırdığı arayüzü AYNEN korur — drop-in replacement.

Yazar   : Mehmet Ensar & Ege — YTÜ Endüstri Müh. Bitirme Projesi
"""

from __future__ import annotations
from typing import Any
from phase1_ortools import solve_phase1
from phase2_pulp     import solve_phase2


def solve(data: dict[str, Any],
          time_limit_sec: int = 120,
          daily_total_min: float = 2600.0,
          daily_total_max: float = 3100.0,
          stock_band_low_ratio: float = 0.80,
          stock_band_high_ratio: float = 1.20) -> dict[str, Any]:
    """
    Hibrit çözüm. Toplam time_limit'i iki faza bölüştürür:
      Faz 1 (atama, setup minimize)  : %85
      Faz 2 (buffer + bant + günlük min): %15
    """
    t1 = max(30, int(time_limit_sec * 0.85))
    t2 = max(30, time_limit_sec - t1)

    r1 = solve_phase1(data, time_limit_sec=t1)
    if r1["status"] in ("INFEASIBLE", "ERROR"):
        return r1

    r2 = solve_phase2(data, phase1_result=r1, time_limit_sec=t2,
                      daily_total_min=daily_total_min,
                      daily_total_max=daily_total_max,
                      stock_band_low_ratio=stock_band_low_ratio,
                      stock_band_high_ratio=stock_band_high_ratio)
    if r2["status"] in ("INFEASIBLE", "ERROR"):
        return {"status": "INFEASIBLE",
                "message": r2.get("message",
                    "Faz 1 başarılı ama Faz 2 LP fizibil değil — "
                    "Talep > kapasite. Negatif KSO sıfır olamadı."),
                "phase1": r1}

    # 4. Birleştirilmiş çıktı (app.py'nin beklediği şema)
    yO_fix = r1["yO_fixed"]
    yM_fix = r1["yM_fixed"]
    days   = list(range(data["T"]))

    plan_otd = {(l, t): None for l in data["otd_lines"] for t in days}
    for (k, l, t) in yO_fix:
        plan_otd[(l, t)] = k

    plan_md  = {(m, t): None for m in data["md_lines"] for t in days}
    for (k, m, t) in yM_fix:
        plan_md[(m, t)] = k

    return {
        "status":         r2["status"],
        # KPI
        "total_setups":   r1["phase1_setups"],
        "otd_setups":     r1["phase1_otd_setups"],
        "md_setups":      r1["phase1_md_setups"],
        "total_buffer":   r2["phase2_buffer"],
        "band_violation": r2.get("phase2_band_violation", 0),
        "daily_under":    r2.get("phase2_daily_under", 0),
        "solve_time_sec": round(r1["phase1_solve_time"] + r2["phase2_solve_time"], 2),
        # Faz-bazlı detay (dashboard'da gösterilebilir)
        "phase1_solver":  "OR-Tools pywraplp / CBC",
        "phase1_setups":  r1["phase1_setups"],
        "phase1_time":    r1["phase1_solve_time"],
        "phase2_solver":  "PuLP / CBC",
        "phase2_buffer":  r2["phase2_buffer"],
        "phase2_time":    r2["phase2_solve_time"],
        # Modellerin boyutu
        "num_variables":   r1["phase1_num_vars"] + r2["phase2_num_vars"],
        "num_constraints": r1["phase1_num_cons"] + r2["phase2_num_cons"],
        # Planlar
        "plan_otd": {f"{l}|{t}": v for (l, t), v in plan_otd.items()},
        "plan_md":  {f"{m}|{t}": v for (m, t), v in plan_md.items()},
        # Üretim
        "prod_otd": {f"{k}|{l}|{t}": v for (k, l, t), v in r2["prod_otd"].items()},
        "prod_md":  {f"{k}|{m}|{t}": v for (k, m, t), v in r2["prod_md"].items()},
        "prod_ta":  {f"{k}|{t}": v    for (k, t),    v in r2["prod_ta"].items()},
        # Setuplar
        "setups":    {f"{l}|{t}": True for (l, t) in r1["zO_fixed"]},
        "setups_md": {f"{m}|{t}": True for (m, t) in r1["zM_fixed"]},
        # Stoklar
        "stocks_kso": {f"{k}|{t}": v for (k, t), v in r2["stocks_kso"].items()},
        "stocks_ksm": {f"{k}|{t}": v for (k, t), v in r2["stocks_ksm"].items()},
        "stocks_kst": {f"{k}|{t}": v for (k, t), v in r2["stocks_kst"].items()},
    }
