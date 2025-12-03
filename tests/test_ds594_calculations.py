# tests/test_ds594_calculations.py
import pytest
import sys
import os
import numpy as np
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.consumers.stream_processor import DS594Calculator

# Helper para generar mediciones realistas con timestamps continuos
def create_measurement(laeq: float, seconds_offset: int):
    """Genera una medición con timestamp ISO válido (compatible con fromisoformat)"""
    base_time = datetime(2025, 1, 1, 8, 0, 0)  # Jornada comienza a las 08:00
    real_time = base_time + timedelta(seconds=seconds_offset)
    return {
        "timestamp": real_time.isoformat() + "Z",
        "metrics": {"LAeq": laeq, "LPeak": laeq + 15}
    }


class TestDS594Compliance:
    """Suite completa de validación contra Decreto Supremo N°594/1999 (Chile)"""

    def test_01_permitted_time_official_table(self):
        """
        Valida la tabla oficial del DS 594 (factor de intercambio 3 dB)
        Fuente: Artículo 75 y Anexo 3
        """
        cases = [
            (85.0, 8.0),      # Límite base
            (88.0, 4.0),      # +3 dB → tiempo se reduce a la mitad
            (91.0, 2.0),      # +6 dB → 1/4 del tiempo
            (94.0, 1.0),      # +9 dB → 1/8
            (97.0, 0.5),      # +12 dB → 1/16
            (100.0, 0.25),    # +15 dB → 1/32
            (82.0, 16.0),     # Nivel de acción preventivo
        ]
        for level, expected in cases:
            result = DS594Calculator.get_permitted_time(level)
            assert abs(result - expected) < 0.3, f"Falló {level} dB → {result}h (esperado {expected}h)"

    def test_02_dose_full_day_at_limit(self):
        """
        8 horas continuas a 85 dB(A) → Dosis debe ser exactamente 100%
        Caso base del DS 594
        """
        measurements = [create_measurement(85.0, i*5) for i in range(int(8 * 3600 / 5))]
        dose = DS594Calculator.calculate_dose_from_measurements(measurements)
        assert abs(dose - 100.0) < 3.0, f"Dosis = {dose}% (debe ser ~100%)"

    def test_03_dose_half_day_at_88db(self):
        """
        4 horas a 88 dB + 4 horas silencio → Dosis = 100%
        Valida que el factor de intercambio funcione correctamente
        """
        measurements = []
        t = 0
        # 4 horas a 88 dB
        for _ in range(int(4 * 3600 / 5)):
            measurements.append(create_measurement(88.0, t))
            t += 5
        # 4 horas silencio
        for _ in range(int(4 * 3600 / 5)):
            measurements.append(create_measurement(0.0, t))
            t += 5
        
        dose = DS594Calculator.calculate_dose_from_measurements(measurements)
        assert abs(dose - 100.0) < 5.0, f"Dosis = {dose}% (debe ser ~100%)"

    def test_04_dose_mixed_exposure_classic_case(self):
        """
        Caso clásico del ejemplo en documentación oficial:
        6 horas a 86 dB + 2 horas a 90 dB → Dosis ≈ 173.9%
        """
        measurements = []
        t = 0
        # 6 horas a 86 dB
        for _ in range(int(6 * 3600 / 5)):
            measurements.append(create_measurement(86.0, t))
            t += 5
        # 2 horas a 90 dB
        for _ in range(int(2 * 3600 / 5)):
            measurements.append(create_measurement(90.0, t))
            t += 5

        dose = DS594Calculator.calculate_dose_from_measurements(measurements)
        assert 170 <= dose <= 177, f"Dosis mixta = {dose}% (esperado ~173.9%)"

    def test_05_lex8h_4h_at_91db_famous_case(self):
        """
        Caso emblemático usado en capacitaciones:
        4 horas a 91 dB(A) → Lex,8h = 88.0 dB(A)
        Equivale energéticamente a 8 horas a 88 dB
        """
        measurements = [create_measurement(91.0, i*5) for i in range(int(4 * 3600 / 5))]
        lex8h = DS594Calculator.calculate_lex8h(measurements)
        assert abs(lex8h - 88.0) < 0.5, f"Lex,8h = {lex8h} dB (esperado 88.0 dB)"

    def test_06_lex8h_full_day_85db(self):
        """8 horas a 85 dB → Lex,8h debe ser exactamente 85 dB"""
        measurements = [create_measurement(85.0, i*5) for i in range(int(8 * 3600 / 5))]
        lex8h = DS594Calculator.calculate_lex8h(measurements)
        assert abs(lex8h - 85.0) < 0.3

    def test_07_lex8h_mixed_exposure(self):
        """6h a 86 dB + 2h a 90 dB → Lex,8h ≈ 87.4 dB"""
        measurements = []
        t = 0
        for _ in range(int(6 * 3600 / 5)):
            measurements.append(create_measurement(86.0, t)); t += 5
        for _ in range(int(2 * 3600 / 5)):
            measurements.append(create_measurement(90.0, t)); t += 5
        
        lex8h = DS594Calculator.calculate_lex8h(measurements)
        assert 87.0 <= lex8h <= 88.0

    def test_08_peak_limit_constant(self):
        """Constante del límite de presión sonora peak"""
        assert DS594Calculator.PEAK_MAXIMO == 140.0