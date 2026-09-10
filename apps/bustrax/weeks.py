"""Calendario operativo SETTEPI.

Semana domingo-sábado; el número de semana es la semana ISO del domingo inicial
(validado en vivo contra el campo "Sem Via" del reporte).
"""

from datetime import date, datetime, timedelta


def start_sunday(d):
    return d - timedelta(days=(d.weekday() + 1) % 7)


def semvia(d):
    s = start_sunday(d)
    iso = s.isocalendar()
    return s.year, iso[1]


def sunday_of_week(year, week):
    d = date(year, 1, 1)
    s = start_sunday(d)
    if s.year < year:
        s += timedelta(days=7)
    while s.year == year:
        if s.isocalendar()[1] == week:
            return s
        s += timedelta(days=7)
    return None


def week_window(year, week):
    s = sunday_of_week(year, week)
    if s is None:
        return None, None
    return s, s + timedelta(days=6)


def weeks_of_year(year):
    d = date(year, 1, 1)
    s = start_sunday(d)
    if s.year < year:
        s += timedelta(days=7)
    weeks = []
    while s.year == year:
        weeks.append(s.isocalendar()[1])
        s += timedelta(days=7)
    if not weeks:
        return []
    return list(range(1, max(weeks) + 1))


def current_week():
    return semvia(datetime.now().date())
