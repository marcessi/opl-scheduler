import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiFetch, apiFetchBlob, ApiError } from '../api/client'
import { useSolver } from '../context/useSolver'

import { MODO_FASES_ACTIVAS, TIEMPO_DEFAULT, type PerfilKey, type StepKey } from './repartos/constantes'
import { getTiempoLabel as getTiempoLabelForMin } from './repartos/utilidades'
import ResumenReparto from './repartos/ResumenReparto'
import WizardView    from './repartos/WizardView'
import PegarOplModal, { type PegarResult } from './repartos/PegarOplModal'
import AnadirOplManualModal from './repartos/AnadirOplManualModal'
import TimelineBoard, { type LimpiarOpts } from './repartos/TimelineBoard'
import type {
  RepartoDetalleOut,
  OplOut,
  OperarioOut,
  ArticuloOut,
  ResultadoOut,
  ProgresoOut,
  AsignacionDetalleOut,
} from '../api/types'

// ── Página principal ───────────────────────────────────────────────────────────

/**
 * Página de detalle de una semana: orquesta el wizard de optimización y la vista de
 * resultados (timeline de asignaciones, ajustes manuales, aprobación y exportación).
 */
export default function RepartoDetalle() {
  const { semana } = useParams<{ semana: string }>()
  const { activo: solverActivo, estado: solverEstado, refrescar: solverRefrescar } = useSolver()
  const solverEnEstaSemana = solverActivo && solverEstado.semana_en_curso === semana
  const solverBloqueoOtraSemana = solverActivo && !solverEnEstaSemana

  // Datos cargados
  const [reparto, setReparto]     = useState<RepartoDetalleOut | null>(null)
  const [opls, setOpls]           = useState<OplOut[] | null>(null)
  const [operarios, setOperarios] = useState<OperarioOut[] | null>(null)
  const [articulos, setArticulos] = useState<ArticuloOut[] | null>(null)
  const [loadError, setLoadError] = useState('')

  const articulosByRef = useMemo(
    () => new Map((articulos ?? []).map(a => [a.referencia, a.descripcion])),
    [articulos],
  )

  // Wizard
  const [step, setStep] = useState<StepKey>('opls')

  // Selección de OPLs
  const [selectedOplIds, setSelectedOplIds] = useState<string[]>([])
  const [showPegarModal, setShowPegarModal] = useState(false)
  const [showManualModal, setShowManualModal] = useState(false)

  // Configuración del optimizador
  const [perfil, setPerfil] = useState<PerfilKey>('balanceado')
  const [tiempoMaximoMin, setTiempoMaximoMin] = useState(TIEMPO_DEFAULT)

  // Vista
  const [forceWizard, setForceWizard] = useState(false)
  const [keepResultsView, setKeepResultsView] = useState(false)

  // Ejecución y progreso
  const [optimizing, setOptimizing] = useState(false)
  const [optimizeError, setOptimizeError] = useState('')
  const [progreso, setProgreso] = useState<ProgresoOut | null>(null)
  const [resultado, setResultado] = useState<ResultadoOut | null>(null)
  const pollingRef = useRef<number | null>(null)

  // ── Carga inicial ──────────────────────────────────────────────

  useEffect(() => {
    if (!semana) return
    setReparto(null)
    setOpls(null)
    setLoadError('')
    setKeepResultsView(false)

    apiFetch<RepartoDetalleOut>(`/repartos/${semana}`)
      .then(data => setReparto(data))
      .catch(err => {
        if (err instanceof ApiError && err.status === 404) {
          setReparto({ semana: semana, aprobado: false, fecha_aprobacion: null, estado_base: null, estado_eficiencia: null, estado_equidad_peso: null, estado_equidad_articulos: null, asignaciones: [] })
          return
        }
        setLoadError(err instanceof Error ? err.message : 'Error')
      })

    apiFetch<OplOut[]>('/opls')
      .then(data => setOpls(data))
      .catch(err => setLoadError(err instanceof Error ? err.message : 'Error'))

    apiFetch<OperarioOut[]>('/operarios')
      .then(data => setOperarios(data.filter(op => op.horas_semanales > 0)))
      .catch(() => {})

    apiFetch<ArticuloOut[]>('/articulos')
      .then(data => setArticulos(data))
      .catch(() => {})
  }, [semana])

  // ── Handlers ───────────────────────────────────────────────────

  function handlePerfilChange(key: PerfilKey) {
    setPerfil(key)
  }

  function handlePegarDone(ids: string[]): PegarResult {
    const oplMap = new Map((opls ?? []).map(o => [o.id, o]))
    const asignMap = new Map((reparto?.asignaciones ?? []).map(a => [a.id_opl, a]))

    const seleccionadas: string[] = []
    const yaRepartidas: string[] = []
    const noExisten: string[] = []

    ids.forEach(id => {
      const opl = oplMap.get(id)
      if (!opl) { noExisten.push(id); return }
      const asig = asignMap.get(id)
      const disponible = asig ? !asig.es_fija : !opl.asignado_a
      if (disponible) seleccionadas.push(id)
      else yaRepartidas.push(id)
    })

    setSelectedOplIds(prev => {
      const set = new Set(prev)
      seleccionadas.forEach(id => set.add(id))
      return [...set]
    })

    return { seleccionadas, yaRepartidas, noExisten }
  }

  function handleOplManualCreated(opl: OplOut) {
    setOpls(prev => [...(prev ?? []), opl])
    setSelectedOplIds(prev => [...new Set([...prev, opl.id])])
  }

  // ── Polling ────────────────────────────────────────────────────

  function stopPolling() {
    if (pollingRef.current !== null) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  function startPolling() {
    if (!semana) return
    stopPolling()
    pollingRef.current = window.setInterval(async () => {
      try {
        const data = await apiFetch<ProgresoOut>(`/repartos/${semana}/progreso`)
        setProgreso(data)

        if (data.terminado) {
          stopPolling()

          if (data.cancelado) {
            // La BD no se ha tocado: volver al estado previo al lanzamiento.
            setOptimizing(false)
            setProgreso(null)
            setOptimizeError('')
            setStep('config')
          } else if (data.error) {
            setOptimizeError(data.error)
            setOptimizing(false)
          } else {
            try {
              const rep = await apiFetch<RepartoDetalleOut>(`/repartos/${semana}`)
              setReparto(rep)
            } catch (err) {
              setOptimizeError(err instanceof Error ? err.message : 'Error')
            }
            setForceWizard(false)
            setKeepResultsView(true)
            setOptimizing(false)
            try {
              const res = await apiFetch<ResultadoOut>(`/repartos/${semana}/resultado`)
              setResultado(res)
            } catch {
              // la vista de resultados muestra igual con datos del reparto
            }
          }
        }
      } catch {
        // silenciar errores de polling
      }
    }, 1500)
  }

  useEffect(() => {
    return () => stopPolling()
  }, [])

  // Cuando el contexto global detecta un solver activo en esta semana,
  // recuperar progreso completo y entrar en modo ejecución.
  useEffect(() => {
    if (!semana) return
    if (!solverEnEstaSemana) return
    if (optimizing) return
    apiFetch<ProgresoOut>(`/repartos/${semana}/progreso`).then(data => {
      setProgreso(data)
      if (data.config) {
        if (Array.isArray(data.config.ids_opls)) setSelectedOplIds(data.config.ids_opls)
        if (data.config.perfil) setPerfil(data.config.perfil as PerfilKey)
        if (typeof data.config.tiempo_maximo_min === 'number') setTiempoMaximoMin(data.config.tiempo_maximo_min)
      }
      setOptimizing(true)
      setStep('ejecucion')
      startPolling()
    }).catch(() => {})
  }, [semana, solverEnEstaSemana]) // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch resultado al cargar un reparto ya optimizado
  useEffect(() => {
    if (!reparto || !semana) return
    if (reparto.estado_base && !resultado && !optimizing) {
      apiFetch<ResultadoOut>(`/repartos/${semana}/resultado`)
        .then(res => setResultado(res))
        .catch(() => {})
    }
  }, [reparto, resultado, optimizing, semana])

  // ── Ejecución del optimizador ────────────────────────────────────

  async function ejecutarOptimizacion() {
    if (!semana) return
    setOptimizing(true)
    setKeepResultsView(false)
    setOptimizeError('')
    setResultado(null)
    const oplIdsParaOptimizar = Array.from(new Set([...selectedOplIds, ...obligatoriaIds]))
    const fasesActivas = MODO_FASES_ACTIVAS[perfil]
    setProgreso({
      fase: 'BASE',
      estado: 'PENDIENTE',
      ejecutando: true,
      terminado: false,
      cancelado: false,
      inicio_ts: Date.now() / 1000,
      error: null,
      config: {
        ids_opls: oplIdsParaOptimizar,
        n_opls: oplIdsParaOptimizar.length,
        perfil,
        tiempo_maximo_min: tiempoMaximoMin,
        tiempo_estimado_seg: tiempoMaximoMin * 60,
      },
      fases: {
        base: 'PENDIENTE',
        eficiencia: fasesActivas.eficiencia ? 'PENDIENTE' : 'NO_EJECUTADA',
        equidad_peso: fasesActivas.equidad_peso ? 'PENDIENTE' : 'NO_EJECUTADA',
        equidad_articulos: fasesActivas.equidad_articulos ? 'PENDIENTE' : 'NO_EJECUTADA',
      },
    })

    try {
      const token = localStorage.getItem('jwt_token')
      const res = await fetch(`/repartos/${semana}/optimizar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          ids_opls: oplIdsParaOptimizar,
          perfil,
          tiempo_maximo_min: tiempoMaximoMin,
        }),
      })
      if (!res.ok && res.status !== 202) {
        const body = await res.json().catch(() => ({})) as { detail?: string }
        throw new Error(body.detail ?? `HTTP ${res.status}`)
      }
      solverRefrescar()
      startPolling()
    } catch (err) {
      setOptimizing(false)
      setOptimizeError(err instanceof Error ? err.message : 'Error')
    }
  }

  async function cancelarOptimizacion() {
    if (!semana) return
    stopPolling()
    try {
      const token = localStorage.getItem('jwt_token')
      await fetch(`/repartos/${semana}/cancelar`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
    } catch {
      // aunque falle la petición, revertimos la UI: nada se ha persistido
    }
    // La BD no se ha modificado: volver al estado previo al lanzamiento.
    setOptimizing(false)
    setProgreso(null)
    setOptimizeError('')
    setStep('config')
    solverRefrescar()
  }

  async function limpiarSelectivo(opts: LimpiarOpts) {
    if (!semana) return
    await apiFetch<unknown>(`/repartos/${semana}/limpiar-selectivo`, {
      method: 'POST',
      body: JSON.stringify(opts),
    })
    const repartoActualizado = await apiFetch<RepartoDetalleOut>(`/repartos/${semana}`)
    setReparto(repartoActualizado)
    setKeepResultsView(true)
    setResultado(null)
  }

  async function handleExportExcel() {
    if (!semana) return
    try {
      await apiFetchBlob(`/repartos/${semana}/excel`, `reparto-${semana}.xlsx`)
    } catch (err) {
      setOptimizeError(err instanceof Error ? err.message : 'Error')
    }
  }

  async function handleAddOpls(ids: string[]) {
    if (!semana) return
    await apiFetch(`/repartos/${semana}/asignaciones`, {
      method: 'POST',
      body: JSON.stringify({ ids_opls: ids }),
    })
    const rep = await apiFetch<RepartoDetalleOut>(`/repartos/${semana}`)
    setReparto(rep)
    setKeepResultsView(true)
    setResultado(null)
  }

  // ── Helpers optimistas para timeline ───────────────────────────

  function actualizarAsignacionLocal(idOpl: string, changes: Partial<AsignacionDetalleOut>) {
    setReparto(prev => {
      if (!prev) return prev
      return {
        ...prev,
        asignaciones: prev.asignaciones.map(a =>
          a.id_opl === idOpl ? { ...a, ...changes } : a
        ),
      }
    })
  }

  async function patchAsignacion(idOpl: string, body: { dni_operario: string | null; es_fija: boolean }) {
    if (!semana) return
    const rep = await apiFetch<RepartoDetalleOut>(`/repartos/${semana}/asignaciones/${idOpl}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
    setReparto(rep)
    setKeepResultsView(true)
    setResultado(null)
  }

  // ── Drop en timeline ────────────────────────────────────────────

  async function handleTimelineDrop(idOpl: string, dniDestino: string | null) {
    const asig = reparto?.asignaciones?.find(a => a.id_opl === idOpl)
    const operarioDestino = dniDestino ? (operarios ?? []).find(o => o.dni === dniDestino) : null
    actualizarAsignacionLocal(idOpl, {
      dni_operario: dniDestino,
      nombre_operario: operarioDestino?.nombre_completo ?? null,
      es_fija: !!dniDestino,
    })
    try {
      await patchAsignacion(idOpl, {
        dni_operario: dniDestino,
        es_fija: !!dniDestino,
      })
    } catch (err) {
      if (asig) actualizarAsignacionLocal(idOpl, { dni_operario: asig.dni_operario, nombre_operario: asig.nombre_operario, es_fija: asig.es_fija })
      setOptimizeError(err instanceof Error ? err.message : 'Error')
    }
  }

  // ── Toggle es_fija en timeline ──────────────────────────────────

  async function handleToggleFija(opl: AsignacionDetalleOut) {
    const nuevaFija = !opl.es_fija
    actualizarAsignacionLocal(opl.id_opl, { es_fija: nuevaFija })
    try {
      await patchAsignacion(opl.id_opl, {
        dni_operario: opl.dni_operario ?? null,
        es_fija: nuevaFija,
      })
    } catch (err) {
      actualizarAsignacionLocal(opl.id_opl, { es_fija: opl.es_fija })
      setOptimizeError(err instanceof Error ? err.message : 'Error')
    }
  }

  // ── Render ─────────────────────────────────────────────────────

  if (loadError) return (
    <>
      <h1 className="page-title">Reparto</h1>
      <p className="error-msg">{loadError}</p>
    </>
  )

  if (!reparto) return (
    <>
      <h1 className="page-title">Reparto</h1>
      <p style={{ color: 'var(--text-muted)' }}>Cargando...</p>
    </>
  )

  const isAprobado  = reparto.aprobado

  const asignaciones = reparto.asignaciones ?? []
  const asignEnEstaSemana = new Map(asignaciones.map(a => [a.id_opl, a]))
  const oplsDisponibles = opls?.filter(o => {
    const asig = asignEnEstaSemana.get(o.id)
    if (asig) return !asig.es_fija
    return !o.asignado_a
  }) ?? null

  const oplsSinReparto = (opls ?? []).filter(o =>
    !asignEnEstaSemana.has(o.id) && !o.asignado_a
  )

  const obligatoriaIds = (oplsDisponibles ?? [])
    .filter(o => asignEnEstaSemana.get(o.id)?.tipo_asignacion === 'obligatoria')
    .map(o => o.id)

  const canGoToConfig = selectedOplIds.length > 0 || obligatoriaIds.length > 0
  const canGoToExec   = canGoToConfig && perfil != null
  const hasBeenOptimized = (reparto.asignaciones ?? []).some(a => a.dni_operario && a.tipo_asignacion !== 'arrastre')
  const showResultsView  = isAprobado || (!optimizing && (keepResultsView || (hasBeenOptimized && !forceWizard)))

  const progresoConfig   = progreso?.config ?? null
  const summaryOplCount  = typeof progresoConfig?.n_opls === 'number'
    ? progresoConfig.n_opls
    : selectedOplIds.length + obligatoriaIds.length
  const summaryPerfilKey = (progresoConfig?.perfil ?? perfil) as PerfilKey
  const summaryTiempo    = getTiempoLabelForMin(progresoConfig?.tiempo_maximo_min ?? tiempoMaximoMin)

  return (
    <>
      <h1 className="page-title">Reparto</h1>

      <div className="dashboard-grid">
        <ResumenReparto
          semana={semana ?? ''}
          isAprobado={isAprobado}
          reparto={reparto}
          operarios={operarios ?? []}
          resultado={resultado}
          optimizeError={optimizeError}
          showFases={showResultsView}
        />

        {/* Timeline Gantt */}
        {showResultsView && asignaciones.length > 0 && (
          <TimelineBoard
            asignaciones={asignaciones}
            operarios={operarios ?? []}
            onDrop={handleTimelineDrop}
            onToggleFija={handleToggleFija}
            readonly={isAprobado || solverBloqueoOtraSemana}
            onExportExcel={handleExportExcel}
            onReoptimize={() => {
              const reoptimizables = asignaciones
                .filter(a => a.tipo_asignacion === 'normal' && !a.es_fija)
                .map(a => a.id_opl)
              setSelectedOplIds(reoptimizables)
              setForceWizard(true)
              setKeepResultsView(false)
              setResultado(null)
              setProgreso(null)
              setStep('opls')
            }}
            onLimpiarSelectivo={limpiarSelectivo}
            oplsSinReparto={oplsSinReparto}
            onAddOpls={handleAddOpls}
            articulosByRef={articulosByRef}
          />
        )}

        {/* Wizard de optimización */}
        {!isAprobado && !showResultsView && (
          <WizardView
            step={step}
            setStep={setStep}
            canGoToConfig={canGoToConfig}
            canGoToExec={canGoToExec}
            hasBeenOptimized={hasBeenOptimized}
            opls={oplsDisponibles}
            selectedOplIds={selectedOplIds}
            obligatoriaIds={obligatoriaIds}
            onSelectionChange={setSelectedOplIds}
            onShowPegar={() => setShowPegarModal(true)}
            onShowManual={() => setShowManualModal(true)}
            perfil={perfil}
            onPerfilChange={handlePerfilChange}
            tiempoMaximoMin={tiempoMaximoMin}
            setTiempoMaximo={setTiempoMaximoMin}
            progreso={progreso}
            optimizing={optimizing}
            optimizeError={optimizeError}
            summaryOplCount={summaryOplCount}
            summaryPerfilKey={summaryPerfilKey}
            summaryTiempo={summaryTiempo}
            onEjecutar={ejecutarOptimizacion}
            onCancelar={cancelarOptimizacion}
            onVolverResultados={() => setForceWizard(false)}
            solverBloqueo={solverBloqueoOtraSemana}
            articulosByRef={articulosByRef}
          />
        )}
      </div>

      {showPegarModal && (
        <PegarOplModal
          onClose={() => setShowPegarModal(false)}
          onPegarDone={handlePegarDone}
        />
      )}

      {showManualModal && (
        <AnadirOplManualModal
          articulos={articulos ?? []}
          onClose={() => setShowManualModal(false)}
          onCreated={handleOplManualCreated}
        />
      )}
    </>
  )
}
