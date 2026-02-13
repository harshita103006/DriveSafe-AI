from typing import List

def predict_next_risk(recent_final_risks: List[float], minutes_since_start: int, hour: int) -> dict:
    # simple features
    avg10 = sum(recent_final_risks[-10:]) / max(1, min(10, len(recent_final_risks)))
    trend = 0.0
    if len(recent_final_risks) >= 6:
        trend = (sum(recent_final_risks[-3:]) / 3) - (sum(recent_final_risks[-6:-3]) / 3)

    night = 1.0 if (hour >= 22 or hour <= 5) else 0.0
    long_drive = min(minutes_since_start / 120.0, 1.0)  # 2 hours -> 1

    # probability 0..1
    p = 0.35*(avg10/100) + 0.25*max(trend/50, 0) + 0.25*long_drive + 0.15*night
    p = max(0.0, min(1.0, p))

    level = "LOW"
    if p > 0.75: level = "HIGH"
    elif p > 0.45: level = "MEDIUM"

    return {"probability": round(p, 3), "level": level, "signals": {"avg10": round(avg10,1), "trend": round(trend,1), "night": night, "long_drive": round(long_drive,2)}}