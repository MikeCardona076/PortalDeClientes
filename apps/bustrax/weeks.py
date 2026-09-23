"""Calendario operativo SETTEPI.

Semana ISO: lunes-domingo. El número de semana es la semana ISO de la fecha.
"""

from datetime import date, datetime, timedelta


def week_window(year, week):
    """Devuelve (lunes, domingo) de la semana ISO (year, week)."""
    try:
        monday = date.fromisocalendar(year, week, 1)
    except ValueError:
        return None, None
    return monday, monday + timedelta(days=6)


def weeks_of_year(year):
    """Número de semanas ISO del año (1..52 o 1..53)."""
    # El 28 de diciembre siempre cae en la última semana ISO del año.
    last = date(year, 12, 28).isocalendar()[1]
    return list(range(1, last + 1))


def current_week():
    """Semana ISO en curso de la fecha actual."""
    iso = datetime.now().date().isocalendar()
    return iso[0], iso[1]


def prev_week(year, week):
    """Semana operativa inmediatamente anterior a (year, week)."""
    if week > 1:
        return year, week - 1
    wl = weeks_of_year(year - 1)
    return year - 1, (max(wl) if wl else 52)
