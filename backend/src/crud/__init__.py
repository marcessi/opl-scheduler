"""Capa CRUD: acceso puro a la base de datos sin lógica de negocio.

Reglas:
- No lanza excepciones de dominio.
- No realiza ``session.commit()``: las transacciones las controla la capa de servicios.
- Recibe siempre la ``Session`` como primer parámetro.
"""
