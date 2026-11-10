"""Pruebas unitarias para reglas de negocio de la Capa Gold (CTR, baselines y reglas de accion)."""

from decimal import Decimal

from src.api.rutas_campanias import evaluar_regla_accion_campania


def test_evaluar_regla_accion_pausar_por_presupuesto_agotado() -> None:
    """Valida la accion 'pausar' cuando el gasto consumido hoy alcanza o supera el presupuesto diario."""
    accion = evaluar_regla_accion_campania(
        presupuesto_diario=Decimal("100.00"),
        gasto_hoy=Decimal("100.00"),
        gasto_ultima_hora=Decimal("10.00"),
        promedio_historico=Decimal("12.00"),
        pct_invalidos_hora=5.0,
    )
    assert accion == "pausar"


def test_evaluar_regla_accion_pausar_por_dispositivos_invalidos() -> None:
    """Valida la accion 'pausar' si mas del 30% de los clics vienen de dispositivos sospechosos."""
    accion = evaluar_regla_accion_campania(
        presupuesto_diario=Decimal("100.00"),
        gasto_hoy=Decimal("40.00"),
        gasto_ultima_hora=Decimal("10.00"),
        promedio_historico=Decimal("12.00"),
        pct_invalidos_hora=35.0,
    )
    assert accion == "pausar"


def test_evaluar_regla_accion_revisar_por_pico_gasto() -> None:
    """Valida la accion 'revisar' cuando el gasto de la ultima hora es >= 3 veces el promedio historico."""
    accion = evaluar_regla_accion_campania(
        presupuesto_diario=Decimal("500.00"),
        gasto_hoy=Decimal("150.00"),
        gasto_ultima_hora=Decimal("45.00"),  # 45.00 >= 3 * 15.00
        promedio_historico=Decimal("15.00"),
        pct_invalidos_hora=10.0,
    )
    assert accion == "revisar"


def test_evaluar_regla_accion_normal() -> None:
    """Valida la accion 'normal' cuando la operacion esta dentro de baselines esperados."""
    accion = evaluar_regla_accion_campania(
        presupuesto_diario=Decimal("500.00"),
        gasto_hoy=Decimal("150.00"),
        gasto_ultima_hora=Decimal("20.00"),
        promedio_historico=Decimal("18.00"),
        pct_invalidos_hora=8.0,
    )
    assert accion == "normal"
