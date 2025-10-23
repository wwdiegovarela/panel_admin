"""
Servicio específico para gestión de usuarios
"""
from typing import List, Optional, Dict, Any
# Importaciones removidas para inicialización perezosa
from models.usuario_model import Usuario


class UsuariosService:
    """Servicio para gestión de usuarios"""
    
    def __init__(self):
        self._bigquery_service = None
        self._firebase_service = None
    
    @property
    def bigquery_service(self):
        """Obtener servicio de BigQuery (inicialización perezosa)"""
        if self._bigquery_service is None:
            from services.bigquery_service import BigQueryService
            self._bigquery_service = BigQueryService()
        return self._bigquery_service
    
    @property
    def firebase_service(self):
        """Obtener servicio de Firebase (inicialización perezosa)"""
        if self._firebase_service is None:
            from services.firebase_service import FirebaseService
            self._firebase_service = FirebaseService()
        return self._firebase_service
    
    def get_usuarios(self, cliente_rol: Optional[str] = None) -> List[Usuario]:
        """Obtener lista de usuarios"""
        try:
            usuarios_data = self.bigquery_service.get_usuarios_con_roles(cliente_rol)
            return [Usuario.from_dict(usuario) for usuario in usuarios_data]
        except Exception as e:
            print(f"Error al obtener usuarios: {e}")
            return []
    
    def get_usuario_by_email(self, email: str) -> Optional[Usuario]:
        """Obtener usuario por email"""
        try:
            usuario_data = self.bigquery_service.get_usuario(email)
            if usuario_data:
                return Usuario.from_dict(usuario_data)
            return None
        except Exception as e:
            print(f"Error al obtener usuario {email}: {e}")
            return None
    
    def create_usuario(self, usuario: Usuario, password: str) -> Dict[str, Any]:
        """Crear nuevo usuario"""
        try:
            # Crear en Firebase
            firebase_result = self.firebase_service.create_user(
                usuario.email_login, 
                password, 
                usuario.nombre_completo
            )
            
            if not firebase_result['success']:
                return firebase_result
            
            # Setear UID para persistir en BigQuery
            usuario.firebase_uid = firebase_result.get('uid', '')
            
            # Crear en BigQuery
            bigquery_result = self.bigquery_service.create_usuario(
                usuario.email_login,
                usuario.firebase_uid,
                (usuario.cliente_rol or ''),
                usuario.nombre_completo,
                usuario.rol_id,
                usuario.cargo,
                usuario.telefono,
                usuario.ver_todas_instalaciones,
            )
            
            if not bigquery_result['success']:
                # Rollback: eliminar de Firebase si falla BigQuery
                self.firebase_service.delete_user(usuario.email_login)
                return bigquery_result
            
            return {'success': True, 'message': 'Usuario creado exitosamente'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_usuario(self, email: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar usuario"""
        try:
            result = self.bigquery_service.update_usuario(email, **updates)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_usuario(self, email: str) -> Dict[str, Any]:
        """Eliminar usuario"""
        try:
            # Eliminar de Firebase primero
            fb = self.firebase_service.delete_user(email)
            if not fb.get('success'):
                return fb

            # Eliminar totalmente en BigQuery (relaciones + usuario)
            bq = self.bigquery_service.delete_usuario_total(email)
            return bq
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def toggle_usuario_activo(self, email: str, activo: bool) -> Dict[str, Any]:
        """Activar/desactivar usuario"""
        try:
            result = self.bigquery_service.update_usuario(email, activo=activo)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_roles(self) -> List[Dict[str, Any]]:
        """Obtener lista de roles disponibles"""
        try:
            return self.bigquery_service.get_roles()
        except Exception as e:
            print(f"Error al obtener roles: {e}")
            return []
    
    def update_rol_usuario(self, email: str, rol_id: str) -> Dict[str, Any]:
        """Actualizar rol de usuario"""
        try:
            result = self.bigquery_service.actualizar_rol_usuario(email, rol_id)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
