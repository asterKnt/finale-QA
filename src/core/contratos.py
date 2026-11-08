"""Validador centralizado de contratos JSON Schema multi-version (v1, v2+) para Clic Justo."""

import json
import re
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from src.core.config import CONTRATOS_DIR

PATRON_CONTRATO = re.compile(r"^(?P<tipo>[a-zA-Z0-9_]+)\.v(?P<version>[0-9]+)\.json$")


class ValidadorContratos:
    """Compila y valida esquemas formales JSON Schema draft 2020-12 indexados por (tipo, version)."""

    def __init__(self, ruta_contratos: Path = CONTRATOS_DIR) -> None:
        self.ruta_contratos = ruta_contratos
        self._validadores: dict[tuple[str, int], Draft202012Validator] = {}
        self._tipos_conocidos: set[str] = set()
        self._cargar_esquemas()

    @property
    def versiones_registradas(self) -> set[tuple[str, int]]:
        """Retorna el conjunto de pares (tipo, version) compilados en memoria."""
        return set(self._validadores.keys())

    def _cargar_esquemas(self) -> None:
        """Descubre y compila automaticamente todos los esquemas <tipo>.v<version>.json."""
        for ruta_archivo in sorted(self.ruta_contratos.glob("*.v*.json")):
            coincidencia = PATRON_CONTRATO.match(ruta_archivo.name)
            if not coincidencia:
                continue
            tipo = coincidencia.group("tipo")
            version = int(coincidencia.group("version"))
            with open(ruta_archivo, encoding="utf-8") as f:
                esquema = cast(dict[str, Any], json.load(f))
            Draft202012Validator.check_schema(esquema)
            self._validadores[(tipo, version)] = Draft202012Validator(esquema)
            self._tipos_conocidos.add(tipo)

    def validar_evento(self, payload: dict[str, Any]) -> tuple[bool, str, str | None, str | None]:
        """Valida un evento entrante contra su contrato correspondiente segun (tipo, version).

        Returns:
            Tuple con (es_valido, tipo_evento, error_tipo, error_detalle).
        """
        tipo = str(payload.get("tipo", "desconocido"))
        if tipo not in self._tipos_conocidos:
            return (
                False,
                tipo,
                "DiscriminatorError",
                f"Tipo de evento '{tipo}' no reconocido en contratos registrados ({sorted(self._tipos_conocidos)})",
            )

        version_raw = payload.get("version")
        if isinstance(version_raw, bool) or not isinstance(version_raw, int):
            # Si falta 'version' o tiene tipo incorrecto, delegamos al validador v1 del tipo para reporte estandar
            validador_base = self._validadores.get((tipo, 1))
            if validador_base is not None:
                errores_base = list(validador_base.iter_errors(payload))
                if errores_base:
                    primer = errores_base[0]
                    ruta = ".".join(str(p) for p in primer.path)
                    campo = f" en '{ruta}'" if ruta else ""
                    return (False, tipo, "ValidationError", f"{primer.message}{campo}")
            return (
                False,
                tipo,
                "ValidationError",
                f"El campo 'version' es requerido y debe ser un entero valido (recibido: {version_raw!r})",
            )

        llave = (tipo, version_raw)
        if llave not in self._validadores:
            return (
                False,
                tipo,
                "SchemaEvolutionError",
                f"La version {version_raw} para el tipo '{tipo}' no tiene un contrato registrado.",
            )

        validador = self._validadores[llave]
        errores = list(validador.iter_errors(payload))
        if not errores:
            return (True, tipo, None, None)

        primer_error = errores[0]
        ruta = ".".join(str(p) for p in primer_error.path)
        campo = f" en '{ruta}'" if ruta else ""
        detalle = f"{primer_error.message}{campo}"
        return (False, tipo, "ValidationError", detalle)
