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
def tarea_backfill(year, week_from=1, week_to=None):
    return backfill(year, week_from=week_from, week_to=week_to)
