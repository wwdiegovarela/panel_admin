"""
Modelo de datos para Contacto
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Contacto:
    """Modelo de datos para Contacto"""
    contacto_id: str
    nombre_contacto: str
    telefono: Optional[str] = None
    cargo: Optional[str] = None
    email: Optional[str] = None
    activo: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para BigQuery"""
        return {
            'contacto_id': self.contacto_id,
            'nombre_contacto': self.nombre_contacto,
            'telefono': self.telefono,
            'cargo': self.cargo,
            'email': self.email,
            'activo': self.activo
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contacto':
        """Crear Contacto desde diccionario de BigQuery"""
        return cls(
            contacto_id=data.get('contacto_id', ''),
            nombre_contacto=data.get('nombre_contacto', ''),
            telefono=data.get('telefono'),
            cargo=data.get('cargo'),
            email=data.get('email'),
            activo=data.get('activo', True)
        )


@dataclass
class ContactoInstalacion:
    """Modelo para relación Contacto-Instalación"""
    contacto_id: str
    instalacion_rol: str
    cliente_rol: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para BigQuery"""
        return {
            'contacto_id': self.contacto_id,
            'instalacion_rol': self.instalacion_rol,
            'cliente_rol': self.cliente_rol
        }
