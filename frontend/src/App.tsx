import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { SolverProvider } from './context/SolverContext'
import RutaProtegida from './components/RutaProtegida'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import DatosMaestros from './pages/DatosMaestros'
import Repartos from './pages/Repartos'
import RepartoDetalle from './pages/RepartoDetalle'

/**
 * Raíz de la aplicación: monta los providers (auth, solver), el router y las rutas.
 *
 * Todas las rutas salvo `/login` van protegidas por {@link RutaProtegida} y
 * envueltas en {@link Layout}.
 */
export default function App() {
  return (
    <AuthProvider>
      <SolverProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <RutaProtegida>
                <Layout>
                  <Dashboard />
                </Layout>
              </RutaProtegida>
            }
          />
          <Route
            path="/datos-maestros"
            element={
              <RutaProtegida>
                <Layout>
                  <DatosMaestros />
                </Layout>
              </RutaProtegida>
            }
          />
          <Route
            path="/repartos"
            element={
              <RutaProtegida>
                <Layout><Repartos /></Layout>
              </RutaProtegida>
            }
          />
          <Route
            path="/repartos/:semana"
            element={
              <RutaProtegida>
                <Layout><RepartoDetalle /></Layout>
              </RutaProtegida>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      </SolverProvider>
    </AuthProvider>
  )
}
