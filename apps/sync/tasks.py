"""Tareas Celery (producción). En dev se usan los management commands."""

from .services import backfill, sync_semana

try:
    from celery import shared_task
except ImportError:  # Celery no instalado en dev
    def shared_task(func=None, **kwargs):
        def wrapper(f):
            return f

        return wrapper(func) if func else wrapper


@shared_task
def tarea_sync_semana(year, week, bunits=None):
    return sync_semana(year, week, bunits=bunits)


@shared_task
def tarea_sync_semana_actual(bunits=None):
    """Sincroniza la semana en curso y la anterior (para Celery beat).

    La semana anterior se re-sincroniza porque, al cerrarse el sábado,
    su último día aún no estaba completo en la corrida previa.
    """
    from apps.bustrax.weeks import current_week, prev_week

    year, week = current_week()
    actual = sync_semana(year, week, bunits=bunits)
    pyear, pweek = prev_week(year, week)
    anterior = sync_semana(pyear, pweek, bunits=bunits)
    return {"actual": {"year": year, "week": week}, "anterior": {"year": pyear, "week": pweek}}


@shared_task
def tarea_backfill(year, week_from=1, week_to=None):
    return backfill(year, week_from=week_from, week_to=week_to)
