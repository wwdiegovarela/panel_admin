"""
Servicio específico para gestión de instalaciones
"""
from typing import List, Optional, Dict, Any
# Importación removida para inicialización perezosa
from models.instalacion_model import Instalacion, InstalacionUsuario


class InstalacionesService:
    """Servicio para gestión de instalaciones"""
    
    def __init__(self):
        self._bigquery_service = None
    
    @property
    def bigquery_service(self):
        """Obtener servicio de BigQuery (inicialización perezosa)"""
        if self._bigquery_service is None:
            from services.bigquery_service import BigQueryService
            self._bigquery_service = BigQueryService()
        return self._bigquery_service
    
    def get_instalaciones(self, cliente_rol: Optional[str] = None) -> List[Instalacion]:
        """Obtener lista de instalaciones"""
        try:
            if cliente_rol:
                instalaciones_data = self.bigquery_service.get_instalaciones(cliente_rol)
            else:
                instalaciones_data = self.bigquery_service.get_instalaciones_con_zonas()
            
            return [Instalacion.from_dict(inst) for inst in instalaciones_data]
        except Exception as e:
            print(f"Error al obtener instalaciones: {e}")
            return []
    
    def get_instalaciones_con_zonas(self, cliente_rol: Optional[str] = None) -> List[Instalacion]:
        """Obtener instalaciones con información de zonas"""
        try:
            instalaciones_data = self.bigquery_service.get_instalaciones_con_zonas(cliente_rol)
            return [Instalacion.from_dict(inst) for inst in instalaciones_data]
        except Exception as e:
            print(f"Error al obtener instalaciones con zonas: {e}")
            return []
    
    def get_instalaciones_usuario(self, email: str) -> List[str]:
        """Obtener IDs de instalaciones de un usuario específico"""
        try:
            instalaciones_data = self.bigquery_service.get_instalaciones_usuario(email)
            # Este método devuelve directamente IDs (str)
            return instalaciones_data or []
        except Exception as e:
            print(f"Error al obtener instalaciones del usuario {email}: {e}")
            return []
    
    def get_instalaciones_usuario_detalle(self, email: str) -> Dict[str, Dict[str, Any]]:
        """Obtener instalaciones del usuario con detalles de permisos"""
        try:
            return self.bigquery_service.get_instalaciones_usuario_detalle(email)
        except Exception as e:
            print(f"Error al obtener detalles de instalaciones: {e}")
            return {}
    
    def asignar_instalaciones_usuario(self, email: str, instalaciones: List[InstalacionUsuario]) -> Dict[str, Any]:
        """Asignar instalaciones a un usuario"""
        try:
            instalaciones_dict = {}
            instalaciones_detalle = {}
            
            for inst in instalaciones:
                instalaciones_dict[inst.instalacion_rol] = inst.cliente_rol
                instalaciones_detalle[inst.instalacion_rol] = {
                    'requiere_encuesta_individual': inst.requiere_encuesta_individual
                }
            
            result = self.bigquery_service.asignar_instalaciones_multi_cliente(
                email, instalaciones_dict, instalaciones_detalle
            )
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def desasignar_instalaciones_usuario(self, email: str, instalaciones_roles: List[str]) -> Dict[str, Any]:
        """Desasignar instalaciones de un usuario"""
        try:
            result = self.bigquery_service.desasignar_instalaciones_usuario(email, instalaciones_roles)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_zonas(self) -> List[str]:
        """Obtener lista de zonas disponibles"""
        try:
            instalaciones = self.get_instalaciones()
            zonas = set()
            for inst in instalaciones:
                if inst.zona:
                    zonas.add(inst.zona)
            return sorted(list(zonas))
        except Exception as e:
            print(f"Error al obtener zonas: {e}")
            return []
    
    def get_clientes_por_zona(self, zona: str) -> List[str]:
        """Obtener clientes de una zona específica"""
        try:
            instalaciones = self.get_instalaciones()
            clientes = set()
            for inst in instalaciones:
                if inst.zona == zona:
                    clientes.add(inst.cliente_rol)
            return sorted(list(clientes))
        except Exception as e:
            print(f"Error al obtener clientes por zona: {e}")
            return []
