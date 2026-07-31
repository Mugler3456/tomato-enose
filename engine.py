# -*- coding: utf-8 -*-
"""
Консольное приложение для оценки состояния томатов по температурному профилю.
Пользователь может вводить любую температуру. Программа не отбрасывает ввод,
а строит оценочный прогноз, показывает химические показатели, e-nose и надежность.

Запуск:
    python tomato_app.py
    python tomato_app.py --self-test
    python tomato_app.py --variety Черри --greenhouse-temp 9 --dc-temp 8 --transport-temp 8 --store-temp 25 --day 14
"""

import argparse
import math
import sys


DC_DAYS = 4.0
TRANSPORT_DAYS = 3.0
BASE_STORE_TEMP = 25.0

VALIDATED_GREENHOUSE_POINTS = [9.0, 12.5, 17.0]  # 8-10, 10-15, >15 как условный центр
VALIDATED_DC_POINTS = [5.0, 8.0, 12.0]
VALIDATED_TRANSPORT_POINTS = [4.0, 8.0]
VALIDATED_STORE_POINTS = [25.0]

VARIETY_ALIASES = {
    "ч": "Черри", "черри": "Черри", "cherry": "Черри", "c": "Черри",
    "ф": "Фламенко", "фламенко": "Фламенко", "flamenco": "Фламенко", "f": "Фламенко",
}

CHEMICAL_NAMES = {
    "chlorophyll": ("Хлорофилл", "мг/г"),
    "carotenoids": ("Каротиноиды", "мг/г"),
    "lycopene": ("Ликопин", "мг/г"),
    "vitamin_c": ("Витамин C / аскорбиновая кислота", "условн. ед."),
    "phenolics": ("Фенольные соединения", "мг/100 г"),
    "flavonoids": ("Флавоноиды", "мг/100 г"),
    "respiration": ("Интенсивность дыхания", "условн. ед."),
    "sugars_brix": ("Растворимые сахара", "°Brix"),
    "acidity": ("Кислотность", "условн. ед."),
    "total_antioxidants": ("ОАОА / суммарная антиоксидантная активность", "условн. ед."),
}

SENSOR_ORDER = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "enose_index"]

BASE_CHEMISTRY = {
    "Черри": {
        "chlorophyll": {0: 0.160, 4: 0.040, 7: 0.019, 17: 0.009, 21: 0.006},
        "carotenoids": {0: 1.070, 4: 1.850, 7: 2.318, 17: 3.350, 21: 3.450},
        "lycopene": {0: 3.150, 4: 2.625, 7: 2.410, 17: 2.500, 21: 2.450},
        "vitamin_c": {0: 9.170, 4: 7.120, 7: 5.174, 17: 4.075, 21: 3.500},
        "phenolics": {0: 34.300, 4: 36.350, 7: 42.880, 17: 42.850, 21: 39.000},
        "flavonoids": {0: 6.600, 4: 7.050, 7: 7.860, 17: 9.750, 21: 10.000},
        "respiration": {0: 9.990, 4: 10.355, 7: 11.252, 17: 10.350, 21: 9.500},
        "sugars_brix": {0: 8.796, 4: 9.530, 7: 9.440, 17: 10.350, 21: 10.100},
        "acidity": {0: 0.274, 4: 0.025, 7: 9.760, 17: 8.650, 21: 8.100},
        "total_antioxidants": {0: 6.600, 4: 2.800, 7: 2.600, 17: 2.350, 21: 2.100},
    },
    "Фламенко": {
        "chlorophyll": {0: 0.140, 4: 0.090, 7: 0.075, 17: 0.024, 21: 0.016},
        "carotenoids": {0: 1.790, 4: 3.010, 7: 2.925, 17: 3.350, 21: 3.400},
        "lycopene": {0: 2.890, 4: 2.750, 7: 2.780, 17: 3.030, 21: 3.000},
        "vitamin_c": {0: 14.170, 4: 11.210, 7: 8.103, 17: 5.285, 21: 4.300},
        "phenolics": {0: 9.600, 4: 10.867, 7: 13.300, 17: 17.433, 21: 18.500},
        "flavonoids": {0: 3.600, 4: 6.167, 7: 6.427, 17: 7.247, 21: 7.500},
        "respiration": {0: 4.620, 4: 4.977, 7: 4.700, 17: 3.950, 21: 3.600},
        "sugars_brix": {0: 4.890, 4: 5.600, 7: 5.125, 17: 5.950, 21: 5.700},
        "acidity": {0: 0.144, 4: 0.010, 7: 6.400, 17: 5.650, 21: 5.200},
        "total_antioxidants": {0: 4.500, 4: 1.700, 7: 1.400, 17: 1.900, 21: 1.600},
    },
}

BASE_SENSORS = {
    "Черри": {
        "S1": {0: 10, 4: 14, 7: 19, 11: 25, 17: 11, 21: 11},
        "S2": {0: 8, 4: 12, 7: 15, 11: 15, 17: 10, 21: 9},
        "S3": {0: 31, 4: 55, 7: 59, 11: 47, 17: 35, 21: 38},
        "S4": {0: 3, 4: 4, 7: 6, 11: 7, 17: 3, 21: 3},
        "S5": {0: 7, 4: 11, 7: 13, 11: 15, 17: 8, 21: 8},
        "S6": {0: 10, 4: 18, 7: 19, 11: 14, 17: 13, 21: 12},
        "S7": {0: 21, 4: 33, 7: 46, 11: 37, 17: 26, 21: 33},
        "S8": {0: 1, 4: 3, 7: 3, 11: 2, 17: 1, 21: 1},
    },
    "Фламенко": {
        "S1": {0: 10, 4: 11, 7: 15, 11: 14, 17: 12, 21: 11},
        "S2": {0: 7, 4: 9, 7: 11, 11: 13, 17: 12, 21: 10},
        "S3": {0: 32, 4: 42, 7: 51, 11: 51, 17: 48, 21: 24},
        "S4": {0: 2, 4: 3, 7: 4, 11: 7, 17: 4, 21: 2},
        "S5": {0: 7, 4: 7, 7: 9, 11: 16, 17: 10, 21: 7},
        "S6": {0: 12, 4: 12, 7: 15, 11: 23, 17: 17, 21: 11},
        "S7": {0: 26, 4: 28, 7: 40, 11: 48, 17: 31, 21: 26},
        "S8": {0: 1, 4: 2, 7: 4, 11: 2, 17: 3, 21: 3},
    },
}

CORR_WEIGHTS = {
    "S1": {"chlorophyll_loss": 0.38, "vitamin_c_loss": 0.45, "phenolics_growth": 0.12},
    "S2": {"chlorophyll_loss": 0.40, "vitamin_c_loss": 0.55, "flavonoids_growth": 0.30},
    "S3": {"carotenoids_growth": 0.22, "respiration_shift": 0.25, "sugars_growth": 0.10},
    "S4": {"vitamin_c_loss": 0.70, "chlorophyll_loss": 0.45, "flavonoids_growth": 0.25},
    "S5": {"chlorophyll_loss": 0.72, "vitamin_c_loss": 0.60, "carotenoids_growth": 0.38},
    "S6": {"chlorophyll_loss": 0.70, "carotenoids_growth": 0.50, "phenolics_growth": 0.25},
    "S7": {"chlorophyll_loss": 0.58, "respiration_shift": 0.35, "phenolics_growth": 0.20},
    "S8": {"chlorophyll_loss": 0.40, "vitamin_c_loss": 0.30, "flavonoids_growth": 0.20},
}


class AppError(Exception):
    pass


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def parse_float(x, name):
    try:
        value = float(str(x).strip().replace(",", "."))
    except ValueError:
        raise AppError(f"{name}: нужно число, получено {x!r}")
    if not math.isfinite(value):
        raise AppError(f"{name}: число должно быть конечным")
    return value


def norm_variety(x):
    key = str(x).strip().lower()
    if key not in VARIETY_ALIASES:
        raise AppError("Сорт должен быть: Черри или Фламенко")
    return VARIETY_ALIASES[key]


def fmt(x, digits=3):
    if abs(x) >= 100:
        s = f"{x:.1f}"
    elif abs(x) >= 10:
        s = f"{x:.2f}"
    else:
        s = f"{x:.{digits}f}"
    return s.rstrip("0").rstrip(".")


def interpolate(curve, day):
    pts = sorted((float(k), float(v)) for k, v in curve.items())
    if day <= pts[0][0]:
        return pts[0][1]
    if day >= pts[-1][0]:
        d1, v1 = pts[-2]
        d2, v2 = pts[-1]
        return max(0.0, v2 + (v2 - v1) / (d2 - d1) * (day - d2))
    for (d1, v1), (d2, v2) in zip(pts, pts[1:]):
        if d1 <= day <= d2:
            return v1 + (v2 - v1) * ((day - d1) / (d2 - d1))
    return pts[-1][1]


def q10_rate(temp, reference):
    return clamp(2.0 ** ((temp - reference) / 10.0), 0.20, 4.50)


def durations(day):
    if day <= 0:
        return {"greenhouse": 0.0, "dc": 0.0, "transport": 0.0, "store": 0.0}
    return {
        "greenhouse": min(0.5, day),
        "dc": min(day, DC_DAYS),
        "transport": min(max(day - DC_DAYS, 0.0), TRANSPORT_DAYS),
        "store": max(day - DC_DAYS - TRANSPORT_DAYS, 0.0),
    }


def temp_metrics(g, dc, tr, st, day):
    d = durations(day)
    total = sum(d.values())
    rates = {
        "greenhouse": q10_rate(g, 9.0),
        "dc": q10_rate(dc, 8.0),
        "transport": q10_rate(tr, 8.0),
        "store": q10_rate(st, 25.0),
    }
    weighted_rate = 1.0 if total <= 0 else sum(d[k] * rates[k] for k in d) / total

    if total <= 0:
        heat = cold = 0.0
    else:
        heat = (
            d["greenhouse"] * max(0.0, g - 10.0) / 10.0 +
            d["dc"] * max(0.0, dc - 8.0) / 10.0 +
            d["transport"] * max(0.0, tr - 8.0) / 10.0 +
            d["store"] * max(0.0, st - 25.0) / 10.0
        ) / total
        cold = (
            d["greenhouse"] * max(0.0, 8.0 - g) / 10.0 +
            d["dc"] * max(0.0, 5.0 - dc) / 10.0 +
            d["transport"] * max(0.0, 4.0 - tr) / 10.0 +
            d["store"] * max(0.0, 18.0 - st) / 10.0
        ) / total

    jump = (
        0.30 * max(0.0, abs(g - dc) - 4.0) / 10.0 +
        0.45 * max(0.0, abs(dc - tr) - 4.0) / 10.0 +
        0.60 * max(0.0, abs(tr - st) - 17.0) / 10.0
    )

    extreme = 0.0
    for t in [g, dc, tr, st]:
        if t < 0:
            extreme += abs(t) / 10.0 + 1.0
        if t > 40:
            extreme += (t - 40.0) / 10.0 + 1.0

    effective_day = day * clamp((weighted_rate ** 0.55) * (1.0 + 0.12 * jump), 0.35, 2.60)
    return {
        "durations": d,
        "weighted_rate": weighted_rate,
        "effective_day": effective_day,
        "heat": heat,
        "cold": cold,
        "jump": jump,
        "extreme": extreme,
    }


def estimate_chemistry(variety, effective_day, m):
    chem = {k: interpolate(v, effective_day) for k, v in BASE_CHEMISTRY[variety].items()}
    heat, cold, jump, extreme = m["heat"], m["cold"], m["jump"], m["extreme"]
    stress = heat + 0.8 * cold + 0.6 * jump + 0.8 * extreme

    multipliers = {
        "chlorophyll": clamp(1.0 - 0.12 * heat - 0.06 * jump - 0.08 * extreme + 0.03 * cold, 0.20, 1.20),
        "vitamin_c": clamp(1.0 - 0.22 * heat - 0.08 * cold - 0.10 * jump - 0.15 * extreme, 0.10, 1.05),
        "carotenoids": clamp(1.0 + 0.10 * heat - 0.06 * cold + 0.04 * jump, 0.55, 1.45),
        "lycopene": clamp(1.0 + 0.06 * heat - 0.04 * cold, 0.70, 1.30),
        "phenolics": clamp(1.0 + 0.14 * stress, 0.70, 1.80),
        "flavonoids": clamp(1.0 + 0.12 * stress, 0.70, 1.70),
        "respiration": clamp(1.0 + 0.35 * heat + 0.18 * jump + 0.25 * extreme - 0.12 * cold, 0.45, 2.20),
        "sugars_brix": clamp(1.0 - 0.12 * heat - 0.04 * extreme + 0.03 * cold, 0.65, 1.20),
        "acidity": clamp(1.0 + 0.08 * heat + 0.10 * jump, 0.70, 1.45),
        "total_antioxidants": clamp(1.0 - 0.10 * heat - 0.05 * jump + 0.06 * cold, 0.45, 1.30),
    }
    return {k: max(0.0, chem[k] * multipliers[k]) for k in chem}


def chemistry_features(variety, chem):
    c0 = {k: interpolate(BASE_CHEMISTRY[variety][k], 0.0) for k in BASE_CHEMISTRY[variety]}
    c7 = {k: interpolate(BASE_CHEMISTRY[variety][k], 7.0) for k in BASE_CHEMISTRY[variety]}

    def ratio(a, b):
        return a / b if abs(b) > 1e-12 else 0.0

    return {
        "chlorophyll_loss": clamp(ratio(c0["chlorophyll"] - chem["chlorophyll"], c0["chlorophyll"]), 0.0, 1.5),
        "vitamin_c_loss": clamp(ratio(c0["vitamin_c"] - chem["vitamin_c"], c0["vitamin_c"]), 0.0, 1.5),
        "carotenoids_growth": clamp(ratio(chem["carotenoids"] - c0["carotenoids"], c7["carotenoids"] - c0["carotenoids"]), -1.0, 2.0),
        "phenolics_growth": clamp(ratio(chem["phenolics"] - c0["phenolics"], c7["phenolics"] - c0["phenolics"]), -1.0, 2.0),
        "flavonoids_growth": clamp(ratio(chem["flavonoids"] - c0["flavonoids"], c7["flavonoids"] - c0["flavonoids"]), -1.0, 2.0),
        "respiration_shift": clamp(abs(ratio(chem["respiration"] - c0["respiration"], c0["respiration"])), 0.0, 2.0),
        "sugars_growth": clamp(ratio(chem["sugars_brix"] - c0["sugars_brix"], c7["sugars_brix"] - c0["sugars_brix"]), -1.0, 2.0),
    }


def estimate_enose(variety, effective_day, chem, m):
    features = chemistry_features(variety, chem)
    sensors = {}
    for sensor in SENSOR_ORDER[:-1]:
        base = interpolate(BASE_SENSORS[variety][sensor], effective_day)
        weights = CORR_WEIGHTS[sensor]
        denom = sum(abs(w) for w in weights.values()) or 1.0
        corr_signal = sum(weights[k] * features[k] for k in weights) / denom
        factor = 1.0 + 0.28 * corr_signal + 0.10 * m["heat"] + 0.06 * m["jump"] + 0.10 * m["extreme"] - 0.05 * m["cold"]
        sensors[sensor] = max(0.0, base * clamp(factor, 0.40, 2.20))
    sensors["enose_index"] = sum(sensors[s] for s in SENSOR_ORDER[:-1])
    return sensors, features


def reliability(g, dc, tr, st, day):
    def nearest(value, points):
        return min(abs(value - p) for p in points)

    penalty = 100.0 * (
        0.22 * nearest(g, VALIDATED_GREENHOUSE_POINTS) / 8.0 +
        0.26 * nearest(dc, VALIDATED_DC_POINTS) / 6.0 +
        0.22 * nearest(tr, VALIDATED_TRANSPORT_POINTS) / 5.0 +
        0.20 * nearest(st, VALIDATED_STORE_POINTS) / 12.0 +
        0.10 * max(0.0, day - 21.0) / 10.0
    )
    score = clamp(100.0 - penalty, 5.0, 100.0)
    if any(t < 0 or t > 40 for t in [g, dc, tr, st]):
        score *= 0.55
    return round(clamp(score, 1.0, 100.0), 1)


def estimate_shelf_life(variety, m):
    base = 21.0
    sensitivity = 1.12 if variety == "Фламенко" else 0.95
    reduction = 1.0 + sensitivity * (0.45 * m["heat"] + 0.35 * m["cold"] + 0.28 * m["jump"] + 0.80 * m["extreme"])
    return clamp(base / reduction, 2.0, 28.0)


def quality_state(variety, day, shelf_life, chem):
    ratio = day / shelf_life
    vit0 = interpolate(BASE_CHEMISTRY[variety]["vitamin_c"], 0.0)
    chl0 = interpolate(BASE_CHEMISTRY[variety]["chlorophyll"], 0.0)
    vit_left = chem["vitamin_c"] / vit0 if vit0 else 0.0
    chl_left = chem["chlorophyll"] / chl0 if chl0 else 0.0

    if ratio <= 0.22:
        state = "свежий"
        rec = "партия свежая, можно хранить и реализовывать планово"
    elif ratio <= 0.55:
        state = "дозревание / оптимальная реализация"
        rec = "лучшее окно продажи: качество стабильное, вкус и аромат оптимальны"
    elif ratio <= 0.80:
        state = "зрелый / реализация"
        rec = "товар пригоден для продажи, желательно не затягивать"
    elif ratio <= 0.95:
        state = "поздняя реализация / зона риска"
        rec = "нужна быстрая реализация или уценка"
    else:
        state = "перезревание / вероятная потеря качества"
        rec = "для обычной продажи партия рискованна, нужна органолептическая проверка"

    if vit_left < 0.30 and chl_left < 0.20 and ratio > 0.60:
        state = "старение / высокий риск потери товарности"
        rec = "не направлять в длительную реализацию"

    return {
        "state": state,
        "recommendation": rec,
        "used_shelf_pct": ratio * 100.0,
        "vitamin_c_left_pct": clamp(vit_left * 100.0, 0.0, 200.0),
        "chlorophyll_left_pct": clamp(chl_left * 100.0, 0.0, 200.0),
    }


def warnings_for(g, dc, tr, st, day, rel, m):
    w = []
    if rel < 65:
        w.append("Низкая надежность: температура далеко от экспериментальных режимов, это экстраполяция.")
    elif rel < 85:
        w.append("Средняя надежность: часть температур интерполируется/экстраполируется.")
    if any(t < 0 for t in [g, dc, tr, st]):
        w.append("Есть температура ниже 0°C: возможны холодовые повреждения.")
    if any(t > 40 for t in [g, dc, tr, st]):
        w.append("Есть температура выше 40°C: высокий риск теплового повреждения.")
    if m["jump"] > 0.4:
        w.append("Сильные перепады температур между этапами.")
    if m["heat"] > 0.5:
        w.append("Высокий тепловой стресс: ускоренное старение и потеря витамина C.")
    if m["cold"] > 0.5:
        w.append("Высокий холодовой стресс: возможны нарушение дозревания и потеря аромата.")
    if day > 21:
        w.append("День хранения больше 21: дальняя экстраполяция.")
    return w


def predict(variety, greenhouse_temp, dc_temp, transport_temp, store_temp, day):
    variety = norm_variety(variety)
    g = parse_float(greenhouse_temp, "Температура отгрузки")
    dc = parse_float(dc_temp, "Температура РЦ")
    tr = parse_float(transport_temp, "Температура транспортировки")
    st = parse_float(store_temp, "Температура магазина")
    day = parse_float(day, "Сутки хранения")
    if day < 0:
        raise AppError("Сутки хранения не могут быть отрицательными")

    m = temp_metrics(g, dc, tr, st, day)
    chem = estimate_chemistry(variety, m["effective_day"], m)
    enose, features = estimate_enose(variety, m["effective_day"], chem, m)
    shelf = estimate_shelf_life(variety, m)
    qual = quality_state(variety, day, shelf, chem)
    rel = reliability(g, dc, tr, st, day)

    return {
        "input": {"variety": variety, "g": g, "dc": dc, "tr": tr, "st": st, "day": day},
        "metrics": m,
        "chemistry": chem,
        "enose": enose,
        "features": features,
        "shelf_life": shelf,
        "quality": qual,
        "reliability": rel,
        "warnings": warnings_for(g, dc, tr, st, day, rel, m),
    }


def table(rows, headers):
    data = [headers] + [[str(x) for x in r] for r in rows]
    widths = [max(len(r[i]) for r in data) for i in range(len(headers))]
    print(" | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("-+-".join("-" * widths[i] for i in range(len(headers))))
    for r in data[1:]:
        print(" | ".join(r[i].ljust(widths[i]) for i in range(len(headers))))


def print_result(r):
    inp, m, q = r["input"], r["metrics"], r["quality"]
    print("\n" + "=" * 78)
    print("ПРОГНОЗ СОСТОЯНИЯ ТОМАТОВ")
    print("=" * 78)

    print("\nВходные данные")
    table([
        ["Сорт", inp["variety"]],
        ["Температура отгрузки с теплицы", f"{fmt(inp['g'])} °C"],
        ["Температура на РЦ", f"{fmt(inp['dc'])} °C"],
        ["Температура транспортировки", f"{fmt(inp['tr'])} °C"],
        ["Температура в магазине", f"{fmt(inp['st'])} °C"],
        ["Сутки хранения", fmt(inp["day"], 1)],
    ], ["Параметр", "Значение"])

    print("\nФиксированные этапы")
    table([
        ["РЦ", f"{fmt(DC_DAYS, 1)} суток"],
        ["Транспортировка", f"{fmt(TRANSPORT_DAYS, 1)} суток"],
        ["Магазин", f"{fmt(max(0.0, inp['day'] - DC_DAYS - TRANSPORT_DAYS), 1)} суток к выбранному дню"],
        ["Эффективный возраст", f"{fmt(m['effective_day'], 2)} суток"],
    ], ["Этап", "Расчет"])

    print("\nХимические показатели")
    table([[name, fmt(r["chemistry"][key]), unit] for key, (name, unit) in CHEMICAL_NAMES.items()],
          ["Показатель", "Значение", "Ед."])

    print("\nПоказания электронного носа")
    table([[key, fmt(r["enose"][key]), "условн. сигнал"] for key in SENSOR_ORDER],
          ["Сенсор", "Значение", "Ед."])

    feature_names = {
        "chlorophyll_loss": "Потеря хлорофилла",
        "vitamin_c_loss": "Потеря витамина C",
        "carotenoids_growth": "Рост каротиноидов",
        "phenolics_growth": "Рост фенольных",
        "flavonoids_growth": "Рост флавоноидов",
        "respiration_shift": "Сдвиг дыхания",
        "sugars_growth": "Рост сахаров",
    }
    print("\nКорреляционные признаки e-nose")
    table([[feature_names[k], fmt(v * 100, 1), "% / индекс"] for k, v in r["features"].items()],
          ["Признак", "Значение", "Ед."])

    print("\nОценочное состояние")
    table([
        ["Состояние", q["state"]],
        ["Рекомендация", q["recommendation"]],
        ["Оценочный срок партии", f"{fmt(r['shelf_life'], 1)} суток"],
        ["Использовано срока", f"{fmt(q['used_shelf_pct'], 1)} %"],
        ["Остаток витамина C", f"{fmt(q['vitamin_c_left_pct'], 1)} % от исходного"],
        ["Остаток хлорофилла", f"{fmt(q['chlorophyll_left_pct'], 1)} % от исходного"],
        ["Надежность прогноза", f"{fmt(r['reliability'], 1)} / 100"],
    ], ["Параметр", "Значение"])

    print("\nТехническая валидация")
    table([
        ["Средняя скорость старения Q10", fmt(m["weighted_rate"], 3)],
        ["Тепловой стресс", fmt(m["heat"], 3)],
        ["Холодовой стресс", fmt(m["cold"], 3)],
        ["Стресс перепадов", fmt(m["jump"], 3)],
        ["Экстремальный стресс", fmt(m["extreme"], 3)],
    ], ["Коэффициент", "Значение"])

    print("\nПредупреждения")
    if r["warnings"]:
        for w in r["warnings"]:
            print("- " + w)
    else:
        print("- Температуры близки к экспериментальным опорным режимам.")


def show_model():
    print("\nМодель принимает любые температуры, но надежность зависит от близости к опорным режимам.")
    print(f"Отгрузка: {VALIDATED_GREENHOUSE_POINTS}")
    print(f"РЦ: {VALIDATED_DC_POINTS}")
    print(f"Транспортировка: {VALIDATED_TRANSPORT_POINTS}")
    print(f"Магазин: {VALIDATED_STORE_POINTS}")
    print("\nКорреляционные веса e-nose:")
    table([[s, ", ".join(f"{k}={v}" for k, v in w.items())] for s, w in CORR_WEIGHTS.items()],
          ["Сенсор", "Признаки"])


def interactive():
    print("Прогноз томатов. Температуры можно вводить любые числовые.")
    variety = input("Сорт [Черри/Фламенко]: ")
    g = input("Температура отгрузки с теплицы, °C: ")
    dc = input("Температура на РЦ, °C: ")
    tr = input("Температура транспортировки, °C: ")
    st = input("Температура в магазине, °C: ")
    day = input("Сутки хранения: ")
    print_result(predict(variety, g, dc, tr, st, day))


def self_test():
    tests = [
        ("Черри", 9, 8, 8, 25, 14),
        ("Фламенко", 9, 8, 4, 25, 17),
        ("Черри", 16, 12, 4, 25, 17),
        ("Фламенко", 22, 6, 2, 28, 10),
        ("Черри", -2, 8, 8, 25, 5),
    ]
    for t in tests:
        r = predict(*t)
        print(f"OK: {r['input']['variety']}, день={r['input']['day']}, состояние={r['quality']['state']}, надежность={r['reliability']}")
    print("Self-test завершен без ошибок.")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--variety")
    parser.add_argument("--greenhouse-temp", type=float)
    parser.add_argument("--dc-temp", type=float)
    parser.add_argument("--transport-temp", type=float)
    parser.add_argument("--store-temp", type=float)
    parser.add_argument("--day", type=float)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--show-model", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return 0
    if args.show_model:
        show_model()
        return 0

    values = [args.variety, args.greenhouse_temp, args.dc_temp, args.transport_temp, args.store_temp, args.day]
    if all(v is not None for v in values):
        print_result(predict(args.variety, args.greenhouse_temp, args.dc_temp, args.transport_temp, args.store_temp, args.day))
    else:
        interactive()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nВыход.")
        raise SystemExit(130)
    except AppError as e:
        print(f"\nОшибка: {e}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as e:
        print(f"\nНепредвиденная ошибка: {e}", file=sys.stderr)
        raise SystemExit(2)
