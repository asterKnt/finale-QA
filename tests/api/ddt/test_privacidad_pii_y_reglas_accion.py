"""Pruebas dirigidas por datos (DDT) para privacidad (PII) y reglas de accion operacional."""

from decimal import Decimal

import pytest

from src.api.rutas_campanias import evaluar_regla_accion_campania


@pytest.mark.parametrize(
    "presupuesto,gasto_hoy,gasto_hora,promedio_hist,pct_invalidos,accion_esperada",
    [
        # Presupuesto totalmente agotado -> pausar
        (Decimal("100.00"), Decimal("100.00"), Decimal("5.00"), Decimal("10.00"), 0.0, "pausar"),
        # Porcentaje de clics de dispositivos invalidos > 30% -> pausar
        (Decimal("500.00"), Decimal("50.00"), Decimal("10.00"), Decimal("10.00"), 30.1, "pausar"),
        # Gasto de la ultima hora triplica el promedio historico (>= 3x) -> revisar
        (Decimal("500.00"), Decimal("100.00"), Decimal("30.00"), Decimal("10.00"), 5.0, "revisar"),
        # Gasto de la ultima hora exactamente 3x promedio historico -> revisar
        (Decimal("500.00"), Decimal("100.00"), Decimal("15.00"), Decimal("5.00"), 0.0, "revisar"),
        # Comportamiento dentro de baselines esperados -> normal
        (Decimal("500.00"), Decimal("100.00"), Decimal("10.00"), Decimal("8.00"), 10.0, "normal"),
    ],
)
def test_evaluar_regla_accion_campania_ddt(
    presupuesto: Decimal,
    gasto_hoy: Decimal,
    gasto_hora: Decimal,
    promedio_hist: Decimal,
    pct_invalidos: float,
    accion_esperada: str,
) -> None:
    """Verifica la matriz de decisiones de accion operacional mediante DDT."""
    accion = evaluar_regla_accion_campania(
        presupuesto_diario=presupuesto,
        gasto_hoy=gasto_hoy,
        gasto_ultima_hora=gasto_hora,
        promedio_historico=promedio_hist,
        pct_invalidos_hora=pct_invalidos,
    )
    assert accion == accion_esperada
