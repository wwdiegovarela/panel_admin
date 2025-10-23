"""
Controlador para gestión de contactos
"""
from typing import List, Optional, Dict, Any
# Importación removida para inicialización perezosa
from models.contacto_model import Contacto, ContactoInstalacion


class ContactosController:
    """Controlador para gestión de contactos"""
    
    def __init__(self):
        self._service = None
    
    @property
    def service(self):
        """Obtener servicio de contactos (inicialización perezosa)"""
        if self._service is None:
            from services.specific.contactos_service import ContactosService
            self._service = ContactosService()
        return self._service
    
    def get_contactos(self, cliente_rol: Optional[str] = None) -> List[Contacto]:
        """Obtener lista de contactos"""
        return self.service.get_contactos(cliente_rol)
    
    def get_contacto_by_email(self, email: str) -> Optional[Contacto]:
        """Obtener contacto por email"""
        return self.service.get_contacto_by_email(email)
    
    def get_contactos_por_instalacion(self, instalacion_rol: str) -> List[Contacto]:
        """Obtener contactos de una instalación específica"""
        return self.service.get_contactos_por_instalacion(instalacion_rol)
    
    def get_todos_contactos_por_instalacion(self) -> Dict[str, List[Contacto]]:
        """Obtener todos los contactos agrupados por instalación"""
        return self.service.get_todos_contactos_por_instalacion()
    
    def get_contactos_usuario(self, email: str, instalacion_rol: str) -> List[str]:
        """Obtener contactos asignados a un usuario para una instalación"""
        return self.service.get_contactos_usuario(email, instalacion_rol)

    def asignar_contactos_usuario(self, email: str, instalacion_rol: str, contactos_ids: List[str], asignado_por: Optional[str] = None) -> Dict[str, Any]:
        """Asignar contactos a un usuario para una instalación"""
        return self.service.asignar_contactos_usuario(email, instalacion_rol, contactos_ids, asignado_por)
    
    def sincronizar_instalaciones_contacto(self, email: str, instalaciones: Dict[str, str]) -> Dict[str, Any]:
        """Sincronizar instalaciones de un contacto"""
        return self.service.sincronizar_instalaciones_contacto(email, instalaciones)
    
    def create_contacto(self, contacto_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear nuevo contacto"""
        try:
            # Validar datos
            validation = self.validate_contacto_data(contacto_data)
            if not validation['success']:
                return validation
            
            # Crear modelo de contacto
            contacto = Contacto(
                contacto_id=contacto_data['contacto_id'],
                nombre_contacto=contacto_data['nombre_contacto'],
                telefono=contacto_data.get('telefono'),
                cargo=contacto_data.get('cargo'),
                email=contacto_data.get('email')
            )
            
            return self.service.create_contacto(contacto)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_contacto(self, contacto_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar contacto"""
        return self.service.update_contacto(contacto_id, updates)
    
    def delete_contacto(self, contacto_id: str) -> Dict[str, Any]:
        """Eliminar contacto"""
        return self.service.delete_contacto(contacto_id)
    
    def validate_contacto_data(self, contacto_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validar datos de contacto"""
        errors = []
        
        # Validar contacto_id
        if not contacto_data.get('contacto_id'):
            errors.append('ID de contacto es requerido')
        
        # Validar nombre_contacto
        if not contacto_data.get('nombre_contacto'):
            errors.append('Nombre del contacto es requerido')
        
        # Validar email si se proporciona
        email = contacto_data.get('email', '')
        if email and '@' not in email:
            errors.append('Email inválido')
        
        if errors:
            return {'success': False, 'errors': errors}
        
        return {'success': True}
