// Adaptador sobre tipos auto-generados por openapi-typescript.
// Para regenerar: npm run gen:api (requiere uvicorn en :8000).
// No editar los tipos que vienen de types.gen.ts — editar schemas.py y regenerar.

import type { components } from './types.gen'

type S = components['schemas']

export type FamiliaOut = S['FamiliaOut']
export type ArticuloOut = S['ArticuloOut']
export type OperarioOut = S['OperarioOut']
export type OperarioFamiliaOut = S['OperarioFamiliaOut']
export type OperarioArticuloOut = S['OperarioArticuloOut']
export type OplOut = S['OplOut']
export type ImportEntityResult = S['ImportEntityResult']
export type CargaOut = S['CargaOut']
export type AsignacionItemOut = S['AsignacionItemOut']
export type CargaOperarioOut = S['CargaOperarioOut']
export type MetricasOut = S['MetricasOut']
export type ResultadoOut = S['ResultadoOut']
export type AsignacionDetalleOut = S['AsignacionDetalleOut']
// `perfil` añadido en schemas.py; el puente `& { perfil... }` mantiene el tipo
// disponible hasta el próximo `npm run gen:api` (queda redundante tras regenerar).
export type RepartoResumenOut = S['RepartoResumenOut'] & { perfil?: string | null }
export type RepartoDetalleOut = S['RepartoDetalleOut']

// Endpoint /repartos/{semana}/progreso no tiene response_model Pydantic → no aparece en OpenAPI
export interface ProgresoFases {
  base: string
  eficiencia: string
  equidad_peso: string
  equidad_articulos: string
}

export interface ProgresoConfig {
  ids_opls: string[]
  n_opls: number
  perfil: string
  tiempo_maximo_min: number
  tiempo_estimado_seg: number
}

export interface ProgresoOut {
  fase: string
  estado: string
  ejecutando: boolean
  terminado: boolean
  inicio_ts: number | null
  error: string | null
  config: ProgresoConfig | null
  fases: ProgresoFases
}

export interface EstadoOptimizacionOut {
  semana_en_curso: string | null
  fase: string | null
  estado: string | null
  inicio_ts: number | null
  n_opls: number | null
}

// /auth/me devuelve unknown en OpenAPI (sin response_model) → tipo manual
export interface User {
  username: string
}

export type LoginResponse = S['TokenResponse']
