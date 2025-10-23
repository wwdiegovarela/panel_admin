"""
Modelo de datos para Usuario
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Usuario:
    """Modelo de datos para Usuario"""
    email_login: str
    firebase_uid: str
    cliente_rol: str
    nombre_completo: str
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    rol_id: str = "CLIENTE"
    nombre_rol: str = "Cliente"
    ver_todas_instalaciones: bool = False
    activo: bool = True
    ultima_sesion: Optional[datetime] = None
    fecha_creacion: Optional[datetime] = None
    permisos: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Inicializar permisos por defecto si no existen"""
        if self.permisos is None:
            self.permisos = {
                'puede_ver_cobertura': True,
                'puede_ver_encuestas': True,
                'puede_enviar_mensajes': True,
                'puede_ver_empresas': False,
                'puede_ver_metricas_globales': False,
                'puede_ver_trabajadores': False,
                'puede_ver_mensajes_recibidos': False,
                'es_admin': False
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para BigQuery"""
        return {
            'email_login': self.email_login,
            'firebase_uid': self.firebase_uid,
            'cliente_rol': self.cliente_rol,
            'nombre_completo': self.nombre_completo,
            'cargo': self.cargo,
            'telefono': self.telefono,
            'rol_id': self.rol_id,
            'ver_todas_instalaciones': self.ver_todas_instalaciones,
            'activo': self.activo,
            'ultima_sesion': self.ultima_sesion.isoformat() if self.ultima_sesion else None,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Usuario':
        """Crear Usuario desde diccionario de BigQuery"""
        return cls(
            email_login=data.get('email_login', ''),
            firebase_uid=data.get('firebase_uid', ''),
            cliente_rol=data.get('cliente_rol', ''),
            nombre_completo=data.get('nombre_completo', ''),
            cargo=data.get('cargo'),
            telefono=data.get('telefono'),
            rol_id=data.get('rol_id', 'CLIENTE'),
            nombre_rol=data.get('nombre_rol', 'Cliente'),
            ver_todas_instalaciones=data.get('ver_todas_instalaciones', False),
            activo=data.get('activo', True),
            ultima_sesion=datetime.fromisoformat(data['ultima_sesion']) if data.get('ultima_sesion') else None,
            fecha_creacion=datetime.fromisoformat(data['fecha_creacion']) if data.get('fecha_creacion') else None,
            permisos=data.get('permisos', {})
        )
