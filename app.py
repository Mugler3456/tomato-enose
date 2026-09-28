# -*- coding: utf-8 -*-
"""
Агрегатор опытов РЭУ им. Плеханова — томаты, авокадо, яблоки.
Плоская структура: все файлы в одной папке, index.html в корне.
Запуск: python app.py → http://localhost:5000
"""
from flask import Flask, request, jsonify, send_from_directory
import os

import engine                      # томаты (e-nose модель)
import avocado_engine as avo       # авокадо (справочник НИР)
import apple_engine as apl         # яблоки (индексы зрелости)

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

TOMATO_DAYS = [0, 4, 7, 11, 14, 17, 21]


@app.route("/")
def index():
    return send_from_directory(BASE, "index.html")


# ─────────────── ТОМАТЫ ───────────────
@app.route("/api/tomato/predict", methods=["POST"])
def tomato_predict():
    try:
        d = request.json
        variety = d.get("variety", "Черри")
        g = float(d.get("greenhouse_temp", 9))
        dc = float(d.get("dc_temp", 8))
        tr = float(d.get("transport_temp", 8))
        st = float(d.get("store_temp", 25))
        sel_day = float(d.get("selected_day", 7))

        traj = []
        for day in TOMATO_DAYS:
            r = engine.predict(variety, g, dc, tr, st, day)
            traj.append(_tomato_row(r, day))

        r_sel = engine.predict(variety, g, dc, tr, st, sel_day)
        selected = _tomato_row(r_sel, sel_day)

        return jsonify({"ok": True, "trajectory": traj, "selected": selected,
                        "days": TOMATO_DAYS})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


def _tomato_row(r, day):
    return {
        "day": day,
        "chemistry": {k: round(v, 4) for k, v in r["chemistry"].items()},
        "enose": {k: round(v, 2) for k, v in r["enose"].items()},
        "quality": r["quality"],
        "shelf_life": round(r["shelf_life"], 1),
        "reliability": r["reliability"],
        "color": r["color"],
        "organoleptic": r["organoleptic"],
        "passport": r["passport"],
        "metrics": {"effective_day": round(r["metrics"]["effective_day"], 2),
                    "heat": round(r["metrics"]["heat"], 3),
                    "cold": round(r["metrics"]["cold"], 3),
                    "jump": round(r["metrics"]["jump"], 3)},
        "warnings": r["warnings"],
    }


# ─────────────── АВОКАДО ───────────────
@app.route("/api/avocado/lookup", methods=["POST"])
def avocado_lookup():
    try:
        d = request.json
        temp = float(d.get("temp", 12))
        firmness = d.get("firmness")
        firmness = float(firmness) if firmness not in (None, "", "null") else None
        r = avo.avocado_lookup(temp, firmness=firmness)
        markers = [{"name": k, "rc": v[0], "shop": v[1], "crit": v[2]}
                   for k, v in r["markers"].items()]
        return jsonify({"ok": True, "temp": r["temp"], "opt_days": r["opt_days"],
                        "exp_days": r["exp_days"], "markers": markers,
                        "voc": r["voc"], "scale": r["scale"],
                        "current_stage": r.get("current_stage")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ─────────────── ЯБЛОКИ ───────────────
@app.route("/api/apple/indices", methods=["POST"])
def apple_indices():
    try:
        d = request.json
        T = d.get("T"); brix = d.get("brix"); isi = d.get("isi")
        acidity = d.get("acidity")
        r = apl.apple_indices(T, brix, isi, acidity)
        r["ok"] = True
        r["streif_stages"] = apl.STREIF_STAGES
        return jsonify(r)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 52)
    print("  Агрегатор опытов: томаты · авокадо · яблоки")
    print(f"  http://localhost:{port}")
    print("=" * 52)
    app.run(host="0.0.0.0", port=port, debug=False)
