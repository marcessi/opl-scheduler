"""Endpoint de health check para sondas de disponibilidad (load balancer, Docker)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    """Comprueba que el servicio está vivo.

    Returns:
        ``{"status": "ok"}`` con código 200 si la API responde.
    """
    return {"status": "ok"}
