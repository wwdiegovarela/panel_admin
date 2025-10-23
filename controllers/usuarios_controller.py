"""
Controlador para gestión de usuarios
"""
from typing import List, Optional, Dict, Any
# Importación removida para inicialización perezosa
from models.usuario_model import Usuario


class UsuariosController:
    """Controlador para gestión de usuarios"""
    
    def __init__(self):
        self._service = None
    
    @property
    def service(self):
        """Obtener servicio de usuarios (inicialización perezosa)"""
        if self._service is None:
            from services.specific.usuarios_service import UsuariosService
            self._service = UsuariosService()
        return self._service
    
    def get_usuarios(self, cliente_rol: Optional[str] = None) -> List[Usuario]:
        """Obtener lista de usuarios"""
        return self.service.get_usuarios(cliente_rol)
    
    def get_usuario_by_email(self, email: str) -> Optional[Usuario]:
        """Obtener usuario por email"""
        return self.service.get_usuario_by_email(email)
    
    def create_usuario(self, usuario_data: Dict[str, Any], password: str) -> Dict[str, Any]:
        """Crear nuevo usuario"""
        try:
            # Validar datos requeridos (cliente_rol puede ser None si ver_todas_instalaciones o si se deduce por instalaciones)
            required_fields = ['email_login', 'nombre_completo']
            for field in required_fields:
                if not usuario_data.get(field):
                    return {'success': False, 'error': f'Campo requerido: {field}'}
            
            # Crear modelo de usuario
            usuario = Usuario(
                email_login=usuario_data['email_login'],
                firebase_uid='',  # Se asignará en el servicio
                cliente_rol=usuario_data['cliente_rol'],
                nombre_completo=usuario_data['nombre_completo'],
                cargo=usuario_data.get('cargo'),
                telefono=usuario_data.get('telefono'),
                rol_id=usuario_data.get('rol_id', 'CLIENTE'),
                ver_todas_instalaciones=usuario_data.get('ver_todas_instalaciones', False)
            )
            
            return self.service.create_usuario(usuario, password)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_usuario(self, email: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar usuario"""
        return self.service.update_usuario(email, updates)
    
    def delete_usuario(self, email: str) -> Dict[str, Any]:
        """Eliminar usuario"""
        return self.service.delete_usuario(email)
    
    def toggle_usuario_activo(self, email: str, activo: bool) -> Dict[str, Any]:
        """Activar/desactivar usuario"""
        return self.service.toggle_usuario_activo(email, activo)
    
    def get_roles(self) -> List[Dict[str, Any]]:
        """Obtener lista de roles disponibles"""
        return self.service.get_roles()
    
    def update_rol_usuario(self, email: str, rol_id: str) -> Dict[str, Any]:
        """Actualizar rol de usuario"""
        return self.service.update_rol_usuario(email, rol_id)
    
    def validate_usuario_data(self, usuario_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validar datos de usuario"""
        errors = []
        
        # Validar email
        email = usuario_data.get('email_login', '')
        if not email or '@' not in email:
            errors.append('Email inválido')
        
        # Validar nombre completo
        if not usuario_data.get('nombre_completo'):
            errors.append('Nombre completo es requerido')
        
        # Validar cliente
        if not usuario_data.get('cliente_rol'):
            errors.append('Cliente es requerido')
        
        if errors:
            return {'success': False, 'errors': errors}
        
        return {'success': True}
