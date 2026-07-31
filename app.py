# -*- coding: utf-8 -*-
"""
Веб-приложение для оценки состояния томатов.
Запуск: python app.py
Откроется на http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
import os

from engine import predict, CHEMICAL_NAMES, SENSOR_ORDER, DC_DAYS, TRANSPORT_DAYS

app = Flask(__name__, static_folder='static')

DAYS = [0, 4, 7, 11, 14, 17, 21]

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data = request.json
        variety   = data.get('variety', 'Черри')
        g         = float(data.get('greenhouse_temp', 9))
        dc        = float(data.get('dc_temp', 8))
        tr        = float(data.get('transport_temp', 8))
        st        = float(data.get('store_temp', 25))
        # selected_day — день, который пользователь выбрал для статус-карточки
        sel_day   = float(data.get('selected_day', 7))

        # Полная траектория по всем точкам
        trajectory = []
        for day in DAYS:
            r = predict(variety, g, dc, tr, st, day)
            row = {
                'day': day,
                'stage': _stage_label(day),
                'chemistry': {k: round(v, 4) for k, v in r['chemistry'].items()},
                'enose':     {k: round(v, 2)  for k, v in r['enose'].items()},
                'features':  {k: round(v * 100, 1) for k, v in r['features'].items()},
                'quality':   r['quality'],
                'shelf_life': round(r['shelf_life'], 1),
                'reliability': r['reliability'],
                'metrics': {
                    'effective_day':  round(r['metrics']['effective_day'], 2),
                    'weighted_rate':  round(r['metrics']['weighted_rate'], 3),
                    'heat':           round(r['metrics']['heat'], 3),
                    'cold':           round(r['metrics']['cold'], 3),
                    'jump':           round(r['metrics']['jump'], 3),
                },
                'warnings': r['warnings'],
            }
            trajectory.append(row)

        # Найти точку ближайшую к выбранному дню
        closest = min(trajectory, key=lambda t: abs(t['day'] - sel_day))

        # Прогноз точно для selected_day (может быть между точками — интерполяция движком)
        r_sel = predict(variety, g, dc, tr, st, sel_day)
        selected = {
            'day': sel_day,
            'stage': _stage_label(sel_day),
            'chemistry':  {k: round(v, 4) for k, v in r_sel['chemistry'].items()},
            'enose':      {k: round(v, 2)  for k, v in r_sel['enose'].items()},
            'features':   {k: round(v * 100, 1) for k, v in r_sel['features'].items()},
            'quality':    r_sel['quality'],
            'shelf_life': round(r_sel['shelf_life'], 1),
            'reliability': r_sel['reliability'],
            'metrics': {
                'effective_day':  round(r_sel['metrics']['effective_day'], 2),
                'weighted_rate':  round(r_sel['metrics']['weighted_rate'], 3),
                'heat':           round(r_sel['metrics']['heat'], 3),
                'cold':           round(r_sel['metrics']['cold'], 3),
                'jump':           round(r_sel['metrics']['jump'], 3),
            },
            'warnings': r_sel['warnings'],
        }

        return jsonify({
            'ok': True,
            'input': {'variety': variety, 'g': g, 'dc': dc, 'tr': tr,
                      'st': st, 'selected_day': sel_day},
            'trajectory':  trajectory,
            'selected':    selected,   # данные для статус-карточки
            'shelf_life':  selected['shelf_life'],
            'chem_names':  {k: {'name': v[0], 'unit': v[1]}
                            for k, v in CHEMICAL_NAMES.items()},
            'days': DAYS,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


def _stage_label(day):
    if day == 0:     return 'Приёмка / РЦ'
    if day <= 4:     return 'Хранение на РЦ'
    if day <= 7:     return 'Транспортировка'
    if day <= 14:    return 'Магазин (ранний)'
    return 'Магазин (поздний)'


if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    print("=" * 50)
    print("  Томаты — Оценка состояния")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
