from datetime import date

from django.test import SimpleTestCase

from apps.bustrax import gps, ns
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

    def _row(self, **overrides):
        row = {
            "id": "1",
            "id_servicio": "E-X-T1-N0010",
            "ID Ruta": "0010",
            "group": "SCN-SCHNEIDER",
            "des": "RUTA X",
            "start_date": "2026-08-17",
            "end_date": "2026-08-17",
            "start_time": "10:00:00",
            "start_eta": "10:04:00",
            "end_time": "11:00:00",
            "end_eta": "11:04:00",
            "Tipo de Viaje": "N",
            "shift": "IN",
            "status": "6",
            "record_quality": "1",
            "Estado de Viaje": "Finalizado ETA",
            "car": "123",
        }
        row.update(overrides)
        return row

    def test_4_minutos_es_retraso(self):
        s = ns.normalize_service(self._row(start_eta="10:04:00", end_eta="11:04:00"))
        self.assertEqual(s["dif_ini"], 4)
        self.assertEqual(s["dif_fin"], 4)
        self.assertEqual(s["diagnostico_inicio"], "Retrasado")
        self.assertTrue(s["es_retraso"])

    def test_3_minutos_no_es_retraso(self):
        s = ns.normalize_service(self._row(start_eta="10:03:00", end_eta="11:03:00"))
        self.assertEqual(s["diagnostico_inicio"], "A tiempo")
        self.assertFalse(s["es_retraso"])

    def test_dif_llegada_cruce_medianoche(self):
        self.assertEqual(
            ns.dif_llegada({"end_eta": "00:10:00", "end_time": "23:50:00"}), 20
        )

    def test_retraso_cruce_medianoche_coincide_con_detalle(self):
        row = self._row(
            start_time="22:00:00",
            start_eta="22:00:00",
            end_time="23:50:00",
            end_eta="00:10:00",
        )
        _, _, retraso = ns.trip_flags(row)
        self.assertEqual(retraso, 1)
        self.assertEqual(ns.normalize_service(row)["dif_fin"], 20)


class GpsEvaluateServiceTests(SimpleTestCase):
    STOP = {"index": 0, "id": "S1", "des": "PARADA 1", "lat": 32.0, "lng": -117.0,
            "sched_min": None}

    def _service(self):
        return {"stops": [self.STOP], "stime": "10:00:00", "etime": "11:00:00"}

    def test_idle_marca_detenida_y_velocidad_minima(self):
        points = [
            (605, 32.0001, -117.0001, 25.0, False),
            (610, 32.0000, -117.0000, 0.0, True),
            (615, 32.0000, -117.0000, 0.0, True),
        ]
        ev = gps.evaluate_service(self._service(), points, tol_m=200, window_min=None)[0]
        self.assertEqual(ev["found"], 1)
        self.assertTrue(ev["idle"])
        self.assertEqual(ev["vel_min"], 0.0)
        self.assertEqual(ev["idle_seg"], 300.0)

    def test_paso_sin_detenerse_no_es_idle(self):
        points = [
            (610, 32.0000, -117.0000, 45.0, False),
            (611, 32.0001, -117.0001, 30.0, False),
        ]
        ev = gps.evaluate_service(self._service(), points, tol_m=200, window_min=None)[0]
        self.assertEqual(ev["found"], 1)
        self.assertFalse(ev["idle"])
        self.assertEqual(ev["vel_min"], 30.0)

    def test_fuera_de_radio_no_detecta(self):
        points = [(610, 32.01, -117.0, 45.0, False)]
        ev = gps.evaluate_service(self._service(), points, tol_m=200, window_min=None)[0]
        self.assertEqual(ev["found"], 0)
        self.assertFalse(ev["idle"])
        self.assertIsNone(ev["vel_min"])

    def test_sin_puntos_devuelve_defaults(self):
        ev = gps.evaluate_service(self._service(), [], tol_m=200, window_min=None)[0]
        self.assertEqual(ev["found"], 0)
        self.assertFalse(ev["idle"])
        self.assertIsNone(ev["vel_min"])
        self.assertEqual(ev["idle_seg"], 0.0)
