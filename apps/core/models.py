from django.contrib.auth.models import User
from django.db import models


class BusinessUnit(models.Model):
    """Unidad de negocio (plaza): set_tj2, set_mxl, ..."""

    code = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Unidad de negocio"
        verbose_name_plural = "Unidades de negocio"

    def __str__(self):
        return f"{self.nombre} ({self.code})"


class Cliente(models.Model):
    """Cliente lógico (nombre base agrupado), p.ej. STRYKER, SCHNEIDER."""

    nombre = models.CharField(max_length=120, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class GrupoCliente(models.Model):
    """Grupo exacto tal como viene en las APIs (p.ej. SCN-SCHNEIDER)."""

    group = models.CharField(max_length=180, unique=True)
    gcode = models.CharField(max_length=60, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="grupos")
    business_unit = models.ForeignKey(
        BusinessUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name="grupos"
    )
    plant_key = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Grupo de cliente"
        verbose_name_plural = "Grupos de cliente"

    def __str__(self):
        return self.group


class Semana(models.Model):
    """Semana operativa ISO lunes-domingo (year + week ISO)."""

    year = models.PositiveIntegerField()
    week = models.PositiveIntegerField()
    inicio = models.DateField()
    fin = models.DateField()

    class Meta:
        unique_together = ("year", "week")
        ordering = ["year", "week"]

    def __str__(self):
        return f"S{self.week}/{self.year}"


class ViajeSemana(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="viajes")
    semana = models.ForeignKey(Semana, on_delete=models.CASCADE, related_name="viajes")
    total = models.IntegerField(default=0)
    entradas = models.IntegerField(default=0)
    retrasos = models.IntegerField(default=0)
    ns = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("cliente", "semana")


class CRRutaSemana(models.Model):
    WINDOW_CHOICES = [("14d", "14 días"), ("7d", "Semana")]

    grupo = models.ForeignKey(GrupoCliente, on_delete=models.CASCADE, related_name="cr_rutas")
    semana = models.ForeignKey(Semana, on_delete=models.CASCADE, related_name="cr_rutas")
    ruta_seq = models.CharField(max_length=20)
    descripcion = models.CharField(max_length=200, blank=True)
    shift = models.CharField(max_length=5, blank=True)
    route_type = models.CharField(max_length=5, blank=True)
    window_mode = models.CharField(max_length=5, choices=WINDOW_CHOICES, default="14d")
    criterio = models.CharField(max_length=40, default="done+etaTS")
    calidad = models.FloatField(null=True, blank=True)
    servicios = models.IntegerField(default=0)
    source = models.CharField(max_length=10, default="api")  # api|gps

    class Meta:
        unique_together = ("grupo", "semana", "ruta_seq", "window_mode")
        indexes = [models.Index(fields=["semana", "window_mode"])]


class CRClienteSemana(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="cr")
    semana = models.ForeignKey(Semana, on_delete=models.CASCADE, related_name="cr")
    window_mode = models.CharField(max_length=5, default="14d")
    calidad = models.FloatField(null=True, blank=True)
    rutas = models.IntegerField(default=0)
    source = models.CharField(max_length=10, default="api")

    class Meta:
        unique_together = ("cliente", "semana", "window_mode")
        indexes = [models.Index(fields=["semana", "window_mode"])]


class ServicioRutaSemana(models.Model):
    """Detalle normalizado de cada servicio del reporte rid=5.

    `eta` = horario real y `time` = horario programado.
    `dif_ini`/`dif_fin` = real - programado en minutos.
    """

    business_unit = models.ForeignKey(
        BusinessUnit, on_delete=models.PROTECT, related_name="servicios"
    )
    grupo = models.ForeignKey(
        GrupoCliente, on_delete=models.PROTECT, related_name="servicios"
    )
    semana = models.ForeignKey(
        Semana, on_delete=models.PROTECT, related_name="servicios"
    )
    external_id = models.CharField(max_length=40)
    service_id = models.CharField(max_length=60, blank=True)
    ruta_seq = models.CharField(max_length=20)
    descripcion = models.CharField(max_length=200, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    car = models.CharField(max_length=80, blank=True)
    operador = models.CharField(max_length=120, blank=True)
    nomina = models.CharField(max_length=40, blank=True)
    prog_ini = models.TimeField(null=True, blank=True)
    real_ini = models.TimeField(null=True, blank=True)
    dif_ini = models.IntegerField(null=True, blank=True)
    prog_fin = models.TimeField(null=True, blank=True)
    real_fin = models.TimeField(null=True, blank=True)
    dif_fin = models.IntegerField(null=True, blank=True)
    diagnostico_inicio = models.CharField(max_length=20, blank=True)
    diagnostico_viaje = models.CharField(max_length=80, blank=True)
    estado_viaje = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=5, blank=True)
    tipo_viaje = models.CharField(max_length=5, blank=True)
    shift = models.CharField(max_length=5, blank=True)
    record_quality = models.CharField(max_length=5, blank=True)
    es_entrada = models.BooleanField(default=False)
    es_retraso = models.BooleanField(default=False)
    source = models.CharField(max_length=10, default="api")
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business_unit", "semana", "external_id")
        indexes = [
            models.Index(fields=["business_unit", "semana", "ruta_seq"]),
            models.Index(fields=["business_unit", "semana", "es_retraso"]),
        ]
        verbose_name = "Servicio de ruta"
        verbose_name_plural = "Servicios de ruta"


class RutaIndicadoresSemana(models.Model):
    """Resumen de servicios, retrasos y NS por ruta y semana."""

    business_unit = models.ForeignKey(
        BusinessUnit, on_delete=models.CASCADE, related_name="ruta_indicadores"
    )
    grupo = models.ForeignKey(
        GrupoCliente, on_delete=models.CASCADE, related_name="ruta_indicadores"
    )
    semana = models.ForeignKey(
        Semana, on_delete=models.CASCADE, related_name="ruta_indicadores"
    )
    ruta_seq = models.CharField(max_length=20)
    descripcion = models.CharField(max_length=200, blank=True)
    servicios = models.IntegerField(default=0)
    entradas = models.IntegerField(default=0)
    retrasos = models.IntegerField(default=0)
    ns = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=10, default="api")
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business_unit", "semana", "grupo", "ruta_seq")
        indexes = [models.Index(fields=["business_unit", "semana"])]
        verbose_name = "Indicadores por ruta"
        verbose_name_plural = "Indicadores por ruta"


class MaeRuta(models.Model):
    """Snapshot de ruta (para el detalle del drill)."""

    grupo = models.ForeignKey(GrupoCliente, on_delete=models.CASCADE, related_name="rutas")
    ruta_seq = models.CharField(max_length=20)
    descripcion = models.CharField(max_length=200, blank=True)
    shift = models.CharField(max_length=5, blank=True)
    route_type = models.CharField(max_length=5, blank=True)
    quality = models.FloatField(null=True, blank=True)
    history_size = models.IntegerField(default=0)
    n_stops = models.IntegerField(default=0)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("grupo", "ruta_seq")


class GpsPunto(models.Model):
    """Puntos GPS crudos por (auto, día UTC) para refinamiento."""

    car = models.CharField(max_length=30)
    dia_utc = models.DateField()
    puntos = models.JSONField(default=list)

    class Meta:
        unique_together = ("car", "dia_utc")


class RefinamientoRuta(models.Model):
    """Rutas que se refinan con GPS (detección real de parada).

    Criterio por defecto: 200 m, como la plataforma Bustrax
    (`tracker/eta/eta.php:780`, `$md = 200`).
    """

    grupo = models.ForeignKey(
        GrupoCliente, on_delete=models.CASCADE, related_name="refinamientos"
    )
    ruta_seq = models.CharField(max_length=20)
    activo = models.BooleanField(default=True)
    tol_m = models.PositiveIntegerField(default=200, help_text="Tolerancia en metros (plataforma: 200).")
    ventana_min = models.PositiveIntegerField(
        null=True, blank=True, help_text="Minutos alrededor de la parada. Vacío = todo el servicio."
    )
    notas = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("grupo", "ruta_seq")
        verbose_name = "Refinamiento GPS"
        verbose_name_plural = "Refinamientos GPS"

    def __str__(self):
        return f"{self.grupo.group} · ruta {self.ruta_seq} ({self.tol_m} m)"


class SyncLog(models.Model):
    ESTADOS = [("ok", "OK"), ("error", "Error"), ("parcial", "Parcial")]

    proceso = models.CharField(max_length=60)
    year = models.IntegerField(null=True, blank=True)
    week = models.IntegerField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="ok")
    mensaje = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]


class PerfilUsuario(models.Model):
    """Scope del usuario: qué clientes/plantas puede ver."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    clientes = models.ManyToManyField(Cliente, blank=True, related_name="usuarios")
    es_admin = models.BooleanField(
        default=False, help_text="Acceso total a todos los clientes y plazas."
    )

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        if self.es_admin:
            return f"{self.user.username} (admin)"
        nombres = ", ".join(c.nombre for c in self.clientes.all()) or "sin clientes"
        return f"{self.user.username} → {nombres}"
