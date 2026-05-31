/**
 * Error de una petición a la API, con el código HTTP asociado.
 *
 * `solverBlock` es `true` cuando el backend rechaza la acción (409) por haber una
 * optimización en curso, lo que permite a la UI mostrar un aviso específico.
 */
export class ApiError extends Error {
  public readonly solverBlock: boolean
  constructor(message: string, public readonly status: number) {
    super(message)
    this.name = 'ApiError'
    this.solverBlock = status === 409 && /Optimización en curso/i.test(message)
  }
}

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('jwt_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function clearToken(): void {
  localStorage.removeItem('jwt_token')
}

/**
 * Petición JSON a la API con el JWT inyectado automáticamente.
 *
 * Ante un 401 limpia el token almacenado; ante cualquier error lanza `ApiError`.
 * @param path Ruta del endpoint.
 * @param options Opciones de `fetch` (método, body, headers extra).
 * @returns El cuerpo de la respuesta parseado como JSON de tipo `T`.
 * @throws {ApiError} Si la respuesta no es satisfactoria.
 */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
    ...(options.headers as Record<string, string> | undefined),
  }

  const res = await fetch(path, { ...options, headers })

  if (res.status === 401) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    clearToken()
    throw new ApiError(body.detail ?? 'Sesión expirada', 401)
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new ApiError(body.detail ?? `HTTP ${res.status}`, res.status)
  }

  return res.json() as Promise<T>
}

/**
 * Subida multipart (importación de Excel).
 *
 * No fija `Content-Type` a propósito para que el navegador genere el `boundary`.
 * @param path Ruta del endpoint de carga.
 * @param formData Datos del formulario con el fichero.
 * @returns El cuerpo de la respuesta parseado como JSON de tipo `T`.
 * @throws {ApiError} Si la respuesta no es satisfactoria.
 */
export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  })
  if (res.status === 401) {
    clearToken()
    throw new ApiError('Sesión expirada', 401)
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new ApiError(body.detail ?? `HTTP ${res.status}`, res.status)
  }
  return res.json() as Promise<T>
}

/**
 * Descarga binaria (exportación de repartos o de errores).
 *
 * Recupera el blob y dispara la descarga en el navegador con el nombre dado.
 * @param path Ruta del endpoint de descarga.
 * @param filename Nombre de fichero sugerido para la descarga.
 * @throws {ApiError} Si la respuesta no es satisfactoria.
 */
export async function apiFetchBlob(path: string, filename = 'datos.xlsx'): Promise<void> {
  const res = await fetch(path, { headers: getAuthHeaders() })
  if (res.status === 401) {
    clearToken()
    throw new ApiError('Sesión expirada', 401)
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new ApiError(body.detail ?? `HTTP ${res.status}`, res.status)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
