from enum import StrEnum


class RolEnum(StrEnum):
    """Constantes de roles del sistema. Se mantienen como StrEnum
    para facilitar comparaciones en código mientras la fuente de verdad
    vive en la tabla `rol`."""

    ADMIN  = "ADMIN"
    CLIENT = "CLIENT"
    COCINA = "COCINA"
    CAJA   = "CAJA"
