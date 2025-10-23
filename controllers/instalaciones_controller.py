"""
Controlador para gestión de instalaciones
"""
from typing import List, Optional, Dict, Any
# Importación removida para inicialización perezosa
from models.instalacion_model import Instalacion, InstalacionUsuario


class InstalacionesController:
    """Controlador para gestión de instalaciones"""
    
    def __init__(self):
        self._service = None
    
    @property
    def service(self):
        """Obtener servicio de instalaciones (inicialización perezosa)"""
        if self._service is None:
            from services.specific.instalaciones_service import InstalacionesService
            self._service = InstalacionesService()
        return self._service
    
    def get_instalaciones(self, cliente_rol: Optional[str] = None) -> List[Instalacion]:
        """Obtener lista de instalaciones"""
        return self.service.get_instalaciones(cliente_rol)
    
    def get_instalaciones_con_zonas(self, cliente_rol: Optional[str] = None) -> List[Instalacion]:
        """Obtener instalaciones con información de zonas"""
        return self.service.get_instalaciones_con_zonas(cliente_rol)
    
    def get_instalaciones_usuario(self, email: str) -> List[str]:
        """Obtener IDs de instalaciones de un usuario específico"""
        return self.service.get_instalaciones_usuario(email)
    
    def get_instalaciones_usuario_detalle(self, email: str) -> Dict[str, Dict[str, Any]]:
        """Obtener instalaciones del usuario con detalles de permisos"""
        return self.service.get_instalaciones_usuario_detalle(email)
    
    def asignar_instalaciones_usuario(self, email: str, instalaciones_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Asignar instalaciones a un usuario"""
        try:
            # Convertir datos a modelos
            instalaciones = []
            for inst_data in instalaciones_data:
                instalacion = InstalacionUsuario(
                    email_login=email,
                    instalacion_rol=inst_data['instalacion_rol'],
                    cliente_rol=inst_data['cliente_rol'],
                    puede_ver=inst_data.get('puede_ver', True),
                    requiere_encuesta_individual=inst_data.get('requiere_encuesta_individual', False)
                )
                instalaciones.append(instalacion)
            
            return self.service.asignar_instalaciones_usuario(email, instalaciones)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def desasignar_instalaciones_usuario(self, email: str, instalaciones_roles: List[str]) -> Dict[str, Any]:
        """Desasignar instalaciones de un usuario"""
        return self.service.desasignar_instalaciones_usuario(email, instalaciones_roles)
    
    def get_zonas(self) -> List[str]:
        """Obtener lista de zonas disponibles"""
        return self.service.get_zonas()
    
    def get_clientes_por_zona(self, zona: str) -> List[str]:
        """Obtener clientes de una zona específica"""
        return self.service.get_clientes_por_zona(zona)
    
    def get_instalaciones_filtradas(self, zona: Optional[str] = None, cliente: Optional[str] = None) -> List[Instalacion]:
        """Obtener instalaciones filtradas por zona y/o cliente"""
        try:
            instalaciones = self.service.get_instalaciones()
            
            if zona:
                instalaciones = [inst for inst in instalaciones if inst.zona == zona]
            
            if cliente:
                instalaciones = [inst for inst in instalaciones if inst.cliente_rol == cliente]
            
            return instalaciones
            
        except Exception as e:
            print(f"Error al filtrar instalaciones: {e}")
            return []
    
    def validate_instalacion_data(self, instalacion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validar datos de instalación"""
        errors = []
        
        # Validar instalacion_rol
        if not instalacion_data.get('instalacion_rol'):
            errors.append('ID de instalación es requerido')
        
        # Validar cliente_rol
        if not instalacion_data.get('cliente_rol'):
            errors.append('Cliente es requerido')
        
        if errors:
            return {'success': False, 'errors': errors}
        
        return {'success': True}
