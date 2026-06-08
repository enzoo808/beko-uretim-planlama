"""
hybrid_solver.py — Hibrit Cozucu Orkestrasyon
Yazar: Mehmet Ensar & Ege -- YTU Endustri Muh. Bitirme Projesi
"""
from __future__ import annotations
from typing import Any
from phase1_ortools import solve_phase1
from phase2_pulp     import solve_phase2


def solve(data: dict[str, Any],
          time_limit_sec: int = 120,
          daily_total_min: float = 2600.0,
          daily_total_max: float = 9999.0,
          stock_band_low_ratio: float = 0.80,
          stock_band_high_ratio: float = 1.20) -> dict[str, Any]:
    """
    Hibrit cozum. Toplam time_limit'i iki faza bolusturu:
      Faz 1 (atama, setup minimize): %80
      Faz 2 (buffer + bant min):     %20

    daily_total_max varsayilan 9999 -- Faz 1'de ust sinir YOK.
    Gercek Beko verisi 5000-6000/gun gerektiriyor; 3100 tavani her
    senaryoyu infeasible yapiyordu. Ust bant yalnizca Faz 2 soft
    amac fonksiyonuyla yaklasik olarak kontrol edilir.
    """
    t1 = max(30, int(time_limit_sec * 0.80))
    t2 = max(20, time_limit_sec - t1)

    r1 = solve_phase1(data, time_limit_sec=t1,
                      daily_total_min=daily_total_min,
                      daily_total_max=daily_total_max)
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
                    "Faz 1 basarili ama Faz 2 LP fizibil degil -- "
                    "Negatif KSO sifir olamadi."),
                "phase1": r1}

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
        "status":            r2["status"],
        "total_setups":      r1["phase1_setups"],
        "otd_setups":        r1["phase1_otd_setups"],
        "md_setups":         r1["phase1_md_setups"],
        "total_buffer":      r2["phase2_buffer"],
        "band_violation":    r2.get("phase2_band_violation", 0),
        "daily_under":       r2.get("phase2_daily_under", 0),
        "phase1_band_under": r1.get("phase1_band_total_under", 0),
        "solve_time_sec":    round(r1["phase1_solve_time"] + r2["phase2_solve_time"], 2),
        "phase1_solver":     "OR-Tools pywraplp / CBC",
        "phase1_setups":     r1["phase1_setups"],
        "phase1_time":       r1["phase1_solve_time"],
        "phase2_solver":     "PuLP / CBC",
        "phase2_buffer":     r2["phase2_buffer"],
        "phase2_time":       r2["phase2_solve_time"],
        "num_variables":     r1["phase1_num_vars"] + r2["phase2_num_vars"],
        "num_constraints":   r1["phase1_num_cons"] + r2["phase2_num_cons"],
        "plan_otd":  {f"{l}|{t}":   v for (l, t),    v in plan_otd.items()},
        "plan_md":   {f"{m}|{t}":   v for (m, t),    v in plan_md.items()},
        "prod_otd":  {f"{k}|{l}|{t}": v for (k, l, t), v in r2["prod_otd"].items()},
        "prod_md":   {f"{k}|{m}|{t}": v for (k, m, t), v in r2["prod_md"].items()},
        "prod_ta":   {f"{k}|{t}":   v for (k, t),    v in r2["prod_ta"].items()},
        "setups":    {f"{l}|{t}": True for (l, t) in r1["zO_fixed"]},
        "setups_md": {f"{m}|{t}": True for (m, t) in r1["zM_fixed"]},
        "stocks_kso": {f"{k}|{t}": v for (k, t), v in r2["stocks_kso"].items()},
        "stocks_ksm": {f"{k}|{t}": v for (k, t), v in r2["stocks_ksm"].items()},
        "stocks_kst": {f"{k}|{t}": v for (k, t), v in r2["stocks_kst"].items()},
    }
