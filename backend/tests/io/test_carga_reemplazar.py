"""
Tests del modo "reemplazar" seguro de cargar_entidades:
borra solo lo no referenciado, conserva lo en uso, upsert de conservadas,
y es atómico (rollback total si algo falla).
"""

from datetime import date

import pytest
from openpyxl import Workbook

import src.io.excel_datos_maestros as mod
from src.io.excel_datos_maestros import ESQUEMA, cargar_entidades, exportar_entidades
from src.database.schema import (
    Familia, Articulo, Operario, OPL, AsignacionOPL, Reparto, TipoAsignacion,
)

SEMANA = date(2025, 2, 3)

# Datos nuevos coherentes para el Excel de reemplazo
NUEVOS = {
    "familias":          [["Pintura", 2]],
    "articulos":         [["ART-NEW", "Pintura", "Nueva pieza", 2.0, 15.0]],
    "operarios":         [["99999999Z", "Nuevo Op", 40.0]],
    "operario_familia":  [["Pintura", "99999999Z", 3]],
    "operario_articulo": [["ART-NEW", "99999999Z", 12.0]],
    "opls":              [["OPL-NEW", "ART-NEW", 5]],
}


def _build_excel(tmp_path, datos: dict[str, list[list]]):
    """Crea un Excel de formato universal con las hojas/filas indicadas."""
    wb = Workbook()
    wb.remove(wb.active)
    for entidad, filas in datos.items():
        ws = wb.create_sheet(entidad)
        ws.append(ESQUEMA[entidad])
        for fila in filas:
            ws.append(fila)
    path = tmp_path / "carga.xlsx"
    wb.save(path)
    return str(path)


def _crear_reparto_con_asignacion(session):
    """Crea un reparto con una asignación sobre OPL-001 (la pone 'en uso')."""
    session.add(Reparto(
        semana=SEMANA, aprobado=False,
        estado_base="OPTIMA", estado_eficiencia="NO_EJECUTADA",
    ))
    session.add(AsignacionOPL(
        id_opl="OPL-001", semana=SEMANA, dni_operario="12345678A",
        tipo_asignacion=TipoAsignacion.NORMAL,
        tiempo_planificado=200.0, tiempo_estimado_operario=250.0,
        tiempo_total_teorico=300.0,
    ))
    session.commit()


def test_reemplazar_sin_datos_operacionales_borra_y_recarga(base_data, tmp_path):
    """Sin asignaciones, reemplazar sustituye todo (comportamiento clásico)."""
    path = _build_excel(tmp_path, NUEVOS)

    cargar_entidades(base_data, path, "reemplazar")

    # Lo viejo desaparece
    assert base_data.get(Familia, "Ensamblaje") is None
    assert base_data.get(Articulo, "ART-001") is None
    assert base_data.get(OPL, "OPL-001") is None
    assert base_data.get(Operario, "87654321B") is None
    # Lo nuevo está
    assert base_data.get(Familia, "Pintura") is not None
    assert base_data.get(Articulo, "ART-NEW") is not None
    assert base_data.get(OPL, "OPL-NEW") is not None


def test_reimportar_lo_exportado_no_anade_ni_elimina(base_data, tmp_path):
    """Exportar el estado actual y reimportarlo (reemplazar) no añade ni elimina
    nada; las filas reimportadas cuentan como modificadas."""
    path = str(tmp_path / "export.xlsx")
    exportar_entidades(base_data, path)

    res = cargar_entidades(base_data, path, "reemplazar")

    for entidad, r in res.items():
        assert r["anadidas"] == 0,   f"{entidad}: anadidas={r['anadidas']}"
        assert r["eliminados"] == 0, f"{entidad}: eliminados={r['eliminados']}"
    # Todo lo reimportado se cuenta como modificación
    assert res["familias"]["modificadas"] == 1
    assert res["operarios"]["modificadas"] == 2


def test_reemplazar_conserva_filas_en_uso(base_data, tmp_path):
    """Las filas referenciadas por un reparto se conservan; el resto se reemplaza."""
    _crear_reparto_con_asignacion(base_data)
    path = _build_excel(tmp_path, NUEVOS)

    res = cargar_entidades(base_data, path, "reemplazar")

    # Conservado por estar en uso (cadena OPL-001 -> ART-001 -> Ensamblaje, y op1)
    assert base_data.get(OPL, "OPL-001") is not None
    assert base_data.get(Articulo, "ART-001") is not None
    assert base_data.get(Familia, "Ensamblaje") is not None
    assert base_data.get(Operario, "12345678A") is not None
    # Lo no usado se reemplaza
    assert base_data.get(Operario, "87654321B") is None
    assert base_data.get(OPL, "OPL-NEW") is not None
    assert base_data.get(Operario, "99999999Z") is not None

    # Resumen agregado
    assert res["opls"]["conservados_en_uso"] == 1
    assert res["opls"]["eliminados"] == 0
    assert res["opls"]["anadidas"] == 1        # OPL-NEW
    assert res["opls"]["modificadas"] == 0
    assert res["operarios"]["conservados_en_uso"] == 1
    assert res["operarios"]["eliminados"] == 1
    assert res["operarios"]["anadidas"] == 1   # 99999999Z
    assert res["operarios"]["modificadas"] == 0


def test_reemplazar_actualiza_conservada_via_upsert(base_data, tmp_path):
    """Una fila en uso presente en el Excel se actualiza, sin duplicar ni petar."""
    _crear_reparto_con_asignacion(base_data)
    # Ensamblaje está en uso (ART-001 la referencia); el Excel la trae cambiada
    path = _build_excel(tmp_path, {"familias": [["Ensamblaje", 4]]})

    res = cargar_entidades(base_data, path, "reemplazar", entidades=["familias"])

    fam = base_data.get(Familia, "Ensamblaje")
    assert fam is not None
    assert fam.experiencia_requerida == 4          # upsert aplicado
    assert base_data.query(Familia).count() == 1   # sin duplicar
    assert res["familias"]["conservados_en_uso"] == 1
    assert res["familias"]["modificadas"] == 1     # upsert cuenta como modificación
    assert res["familias"]["anadidas"] == 0


def test_reemplazar_rollback_atomico_si_falla(base_data, tmp_path, monkeypatch):
    """Si el insert falla tras el borrado, se revierte todo: nada se pierde."""
    def boom(*a, **k):
        raise RuntimeError("fallo simulado en insert")
    monkeypatch.setattr(mod, "_bulk_ejecutar", boom)
    path = _build_excel(tmp_path, NUEVOS)

    with pytest.raises(RuntimeError):
        cargar_entidades(base_data, path, "reemplazar")

    base_data.rollback()  # como hace get_session ante una excepción

    # El borrado (no committeado) se deshizo: los datos originales siguen
    assert base_data.get(OPL, "OPL-001") is not None
    assert base_data.get(Articulo, "ART-001") is not None
    assert base_data.get(Operario, "87654321B") is not None
