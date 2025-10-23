"""
Modelo de datos para Instalación
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Instalacion:
    """Modelo de datos para Instalación"""
    instalacion_rol: str
    cliente_rol: str
    zona: Optional[str] = None
    nombre_instalacion: Optional[str] = None
    direccion: Optional[str] = None
    activo: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para BigQuery"""
        return {
            'instalacion_rol': self.instalacion_rol,
            'cliente_rol': self.cliente_rol,
            'zona': self.zona,
            'nombre_instalacion': self.nombre_instalacion,
            'direccion': self.direccion,
            'activo': self.activo
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Instalacion':
        """Crear Instalacion desde diccionario de BigQuery"""
        return cls(
            instalacion_rol=data.get('instalacion_rol', ''),
            cliente_rol=data.get('cliente_rol', ''),
            zona=data.get('zona'),
            nombre_instalacion=data.get('nombre_instalacion'),
            direccion=data.get('direccion'),
            activo=data.get('activo', True)
        )


@dataclass
class InstalacionUsuario:
    """Modelo para relación Usuario-Instalación"""
    email_login: str
    instalacion_rol: str
    cliente_rol: str
    puede_ver: bool = True
    requiere_encuesta_individual: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para BigQuery"""
        return {
            'email_login': self.email_login,
            'instalacion_rol': self.instalacion_rol,
            'cliente_rol': self.cliente_rol,
            'puede_ver': self.puede_ver,
            'requiere_encuesta_individual': self.requiere_encuesta_individual
        }
