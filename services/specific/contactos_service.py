"""
Servicio específico para gestión de contactos
"""
from typing import List, Optional, Dict, Any
# Importación removida para inicialización perezosa
from models.contacto_model import Contacto, ContactoInstalacion


class ContactosService:
    """Servicio para gestión de contactos"""
    
    def __init__(self):
        self._bigquery_service = None
    
    @property
    def bigquery_service(self):
        """Obtener servicio de BigQuery (inicialización perezosa)"""
        if self._bigquery_service is None:
            from services.bigquery_service import BigQueryService
            self._bigquery_service = BigQueryService()
        return self._bigquery_service
    
    def get_contactos(self, cliente_rol: Optional[str] = None) -> List[Contacto]:
        """Obtener lista de contactos"""
        try:
            contactos_data = self.bigquery_service.get_contactos(cliente_rol)
            return [Contacto.from_dict(contacto) for contacto in contactos_data]
        except Exception as e:
            print(f"Error al obtener contactos: {e}")
            return []
    
    def get_contacto_by_email(self, email: str) -> Optional[Contacto]:
        """Obtener contacto por email"""
        try:
            contacto_data = self.bigquery_service.get_contacto_por_email(email)
            if contacto_data:
                return Contacto.from_dict(contacto_data)
            return None
        except Exception as e:
            print(f"Error al obtener contacto {email}: {e}")
            return None
    
    def get_contactos_por_instalacion(self, instalacion_rol: str) -> List[Contacto]:
        """Obtener contactos de una instalación específica"""
        try:
            # En BigQueryService el nombre es get_contactos_instalacion
            contactos_data = self.bigquery_service.get_contactos_instalacion(instalacion_rol)
            return [Contacto.from_dict(contacto) for contacto in contactos_data]
        except Exception as e:
            print(f"Error al obtener contactos de instalación {instalacion_rol}: {e}")
            return []

    def get_instalaciones_contacto(self, contacto_id: str) -> List[str]:
        """Obtener instalaciones donde participa un contacto"""
        try:
            return self.bigquery_service.get_instalaciones_contacto(contacto_id)
        except Exception as e:
            print(f"Error al obtener instalaciones del contacto {contacto_id}: {e}")
            return []
    
    def get_todos_contactos_por_instalacion(self) -> Dict[str, List[Contacto]]:
        """Obtener todos los contactos agrupados por instalación"""
        try:
            contactos_data = self.bigquery_service.get_todos_contactos_por_instalacion()
            result = {}
            for instalacion, contactos in contactos_data.items():
                result[instalacion] = [Contacto.from_dict(contacto) for contacto in contactos]
            return result
        except Exception as e:
            print(f"Error al obtener contactos por instalación: {e}")
            return {}
    
    def get_contactos_usuario(self, email: str, instalacion_rol: str) -> List[str]:
        """Obtener contactos asignados a un usuario para una instalación"""
        try:
            return self.bigquery_service.get_contactos_usuario(email, instalacion_rol)
        except Exception:
            return []

    def asignar_contactos_usuario(self, email: str, instalacion_rol: str, contactos_ids: List[str], asignado_por: Optional[str] = None) -> Dict[str, Any]:
        """Asignar contactos a un usuario para una instalación"""
        try:
            asignado_por = asignado_por or email
            result = self.bigquery_service.asignar_contactos_usuario(email, instalacion_rol, contactos_ids, asignado_por)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def ensure_contacto_usuario_app(self, email: str, nombre: Optional[str] = None, telefono: Optional[str] = None, cargo: Optional[str] = None) -> Dict[str, Any]:
        """Asegurar que exista un contacto asociado al email (usuario app). Si no existe, lo crea."""
        try:
            existente = self.bigquery_service.get_contacto_por_email(email)
            if existente:
                return {'success': True, 'contacto_id': existente.get('contacto_id')}
            nombre_final = nombre or email
            create_res = self.bigquery_service.create_contacto(
                nombre=nombre_final,
                telefono=telefono or None,
                cargo=cargo or None,
                email=email,
                es_usuario_app=True
            )
            if not create_res.get('success', False):
                return create_res
            return {'success': True, 'contacto_id': create_res.get('contacto_id')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def sincronizar_instalaciones_contacto(self, email: str, instalaciones: Dict[str, str]) -> Dict[str, Any]:
        """Sincronizar instalaciones de un contacto"""
        try:
            result = self.bigquery_service.sincronizar_instalaciones_contacto(email, instalaciones)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_contacto(self, contacto: Contacto) -> Dict[str, Any]:
        """Crear nuevo contacto"""
        try:
            result = self.bigquery_service.create_contacto(contacto.to_dict())
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_contacto(self, contacto_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar contacto"""
        try:
            result = self.bigquery_service.update_contacto(contacto_id, **updates)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_contacto(self, contacto_id: str) -> Dict[str, Any]:
        """Eliminar contacto"""
        try:
            result = self.bigquery_service.delete_contacto(contacto_id)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
