from datetime import date

from django.test import SimpleTestCase

from apps.bustrax import ns
from apps.bustrax.weeks import prev_week, week_window, weeks_of_year


class WeeksTests(SimpleTestCase):
    def test_cruce_iso_52_1(self):
        self.assertEqual(
            week_window(2025, 52), (date(2025, 12, 22), date(2025, 12, 28))
        )
        self.assertEqual(
            week_window(2026, 1), (date(2025, 12, 29), date(2026, 1, 4))
        )
        self.assertEqual(prev_week(2026, 1), (2025, 52))

    def test_weeks_of_year_incluye_53(self):
        self.assertIn(53, weeks_of_year(2020))


class NsTests(SimpleTestCase):
    def test_minutos_diferencia_positivo_es_tarde(self):
        self.assertEqual(ns.minutes_diff("10:10:00", "10:00:00"), 10)
        self.assertEqual(ns.minutes_diff("09:50:00", "10:00:00"), -10)

    def test_minutos_diferencia_cruce_medianoche(self):
        self.assertEqual(ns.minutes_diff("00:10:00", "23:50:00"), 20)

    def test_normalize_service(self):
        row = {
            "id": "1",
            "id_servicio": "E-X-T1-N0010",
            "ID Ruta": "0010",
            "group": "SCN-SCHNEIDER",
            "des": "RUTA X",
            "start_date": "2026-08-17",
            "end_date": "2026-08-17",
            "start_time": "10:00:00",
            "start_eta": "10:10:00",
            "end_time": "11:00:00",
            "end_eta": "11:20:00",
            "Tipo de Viaje": "N",
            "shift": "IN",
            "status": "6",
            "record_quality": "1",
            "Estado de Viaje": "Finalizado ETA",
            "Diagnostico Viaje": "Retrasado",
            "car": "123",
            "operador": "OPERADOR",
            "no. de nomina": "99",
        }
        s = ns.normalize_service(row)
        self.assertEqual(s["ruta_seq"], "0010")
        self.assertEqual(s["dif_ini"], 10)
        self.assertEqual(s["dif_fin"], 20)
        self.assertEqual(s["diagnostico_inicio"], "Retrasado")
        self.assertTrue(s["es_entrada"])
        self.assertTrue(s["es_retraso"])
