"""
Utilidades para el módulo de pedidos.

Contiene el mapa de transiciones → roles permitidos y el helper de validación
de permisos por transición, reutilizados por PedidoService.

No hacer commit aquí: el UoW del llamador es responsable de persistir.
"""

from app.modules.rol.enums import RolEnum


# Mapa de transición (estado_actual, estado_destino) → conjunto de roles que
# pueden ejecutar esa transición. Las transiciones NO listadas no tienen control
# fino de rol (quedan sujetas solo al require_role del router).
#
# Nota: CANCELADO se maneja por separado en `cancelar()` (requiere ADMIN), por
# eso no aparece aquí; avanzar_estado solo avanza hacia adelante en el flujo.

TRANSICION_ROLES: dict[tuple[str, str], set[RolEnum]] = {
    # Confirmar pedido
    ("PENDIENTE", "CONFIRMADO"): {RolEnum.CAJA, RolEnum.ADMIN},

    # Pasar a preparación desde CONFIRMADO
    ("CONFIRMADO", "EN_PREPARACION"): {RolEnum.CAJA, RolEnum.COCINA, RolEnum.ADMIN},

    # Marcar terminado — retiro local
    ("EN_PREPARACION", "LISTO_PARA_RETIRAR"): {RolEnum.COCINA, RolEnum.ADMIN},

    # Marcar terminado — delivery
    ("EN_PREPARACION", "ENVIADO"): {RolEnum.COCINA, RolEnum.ADMIN},

    # Marcar entregado — retiro local
    ("LISTO_PARA_RETIRAR", "ENTREGADO"): {RolEnum.ADMIN},

    # Marcar entregado — delivery
    ("ENVIADO", "ENTREGADO"): {RolEnum.ADMIN},
}


def validar_rol_para_transicion(
    estado_actual: str,
    estado_destino: str,
    roles_usuario: list[str],
) -> bool:
    """
    Retorna True si alguno de los roles del usuario está autorizado para
    ejecutar la transición (estado_actual → estado_destino).

    Si la transición no está en el mapa, se considera permitida para cualquier
    rol (comportamiento abierto — el control grueso del router sigue aplicando).

    Args:
        estado_actual: Código del estado actual del pedido.
        estado_destino: Código del estado al que se quiere avanzar.
        roles_usuario: Lista de códigos de rol del usuario autenticado.

    Returns:
        True si la transición está permitida, False si no.
    """
    clave = (estado_actual, estado_destino)
    roles_permitidos = TRANSICION_ROLES.get(clave)

    if roles_permitidos is None:
        # Transición no mapeada → no hay restricción adicional de rol.
        return True

    roles_set = set(roles_usuario)
    return bool(roles_set & {r.value for r in roles_permitidos})
