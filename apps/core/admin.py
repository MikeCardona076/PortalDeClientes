from django.contrib import admin

from .models import (
    BusinessUnit,
    Cliente,
    CRClienteSemana,
    CRRutaSemana,
    GpsPunto,
    GrupoCliente,
    MaeRuta,
    PerfilUsuario,
    RefinamientoRuta,
    RutaIndicadoresSemana,
    Semana,
    ServicioRutaSemana,
    SyncLog,
    ViajeSemana,
)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("user", "es_admin")
    search_fields = ("user__username", "user__email")
    filter_horizontal = ("clientes",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    search_fields = ("nombre",)


@admin.register(GrupoCliente)
class GrupoClienteAdmin(admin.ModelAdmin):
    list_display = ("group", "cliente", "business_unit", "gcode")
    list_filter = ("business_unit", "cliente")
    search_fields = ("group", "gcode")


@admin.register(BusinessUnit)
class BusinessUnitAdmin(admin.ModelAdmin):
    list_display = ("code", "nombre", "activa")


@admin.register(Semana)
class SemanaAdmin(admin.ModelAdmin):
    list_display = ("year", "week", "inicio", "fin")
    list_filter = ("year",)


@admin.register(ViajeSemana)
class ViajeSemanaAdmin(admin.ModelAdmin):
    list_display = ("cliente", "semana", "total", "entradas", "retrasos", "ns")
    list_filter = ("semana__year",)


@admin.register(CRClienteSemana)
class CRClienteSemanaAdmin(admin.ModelAdmin):
    list_display = ("cliente", "semana", "window_mode", "calidad", "rutas", "source")
    list_filter = ("window_mode", "semana__year", "source")


@admin.register(CRRutaSemana)
class CRRutaSemanaAdmin(admin.ModelAdmin):
    list_display = ("grupo", "semana", "ruta_seq", "window_mode", "calidad", "source")
    list_filter = ("window_mode", "semana__year", "source")
    search_fields = ("ruta_seq", "descripcion", "grupo__group")


@admin.register(MaeRuta)
class MaeRutaAdmin(admin.ModelAdmin):
    list_display = ("grupo", "ruta_seq", "descripcion", "quality", "history_size")
    search_fields = ("ruta_seq", "descripcion")


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ("proceso", "year", "week", "estado", "creado")
    list_filter = ("estado", "proceso")


@admin.register(GpsPunto)
class GpsPuntoAdmin(admin.ModelAdmin):
    list_display = ("car", "dia_utc")


@admin.register(RefinamientoRuta)
class RefinamientoRutaAdmin(admin.ModelAdmin):
    list_display = ("grupo", "ruta_seq", "activo", "tol_m", "ventana_min")
    list_filter = ("activo", "grupo")
    search_fields = ("ruta_seq", "grupo__group")


@admin.register(ServicioRutaSemana)
class ServicioRutaSemanaAdmin(admin.ModelAdmin):
    list_display = (
        "business_unit", "grupo", "semana", "ruta_seq", "fecha_inicio",
        "car", "operador", "dif_ini", "dif_fin", "es_retraso",
    )
    list_filter = ("business_unit", "semana__year", "es_retraso", "source")
    search_fields = ("external_id", "service_id", "ruta_seq", "car", "operador", "nomina")


@admin.register(RutaIndicadoresSemana)
class RutaIndicadoresSemanaAdmin(admin.ModelAdmin):
    list_display = (
        "business_unit", "grupo", "semana", "ruta_seq",
        "servicios", "entradas", "retrasos", "ns",
    )
    list_filter = ("business_unit", "semana__year", "source")
    search_fields = ("ruta_seq", "grupo__group")
