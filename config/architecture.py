"""
Configuración de la nueva arquitectura de la aplicación
"""
from typing import Optional


class ApplicationControllers:
    """Clase para gestionar todos los controladores de la aplicación con inicialización perezosa"""
    
    def __init__(self):
        self._usuarios_controller = None
        self._instalaciones_controller = None
        self._contactos_controller = None
    
    def get_usuarios_controller(self):
        """Obtener controlador de usuarios (inicialización perezosa)"""
        if self._usuarios_controller is None:
            from controllers.usuarios_controller import UsuariosController
            self._usuarios_controller = UsuariosController()
        return self._usuarios_controller
    
    def get_instalaciones_controller(self):
        """Obtener controlador de instalaciones (inicialización perezosa)"""
        if self._instalaciones_controller is None:
            from controllers.instalaciones_controller import InstalacionesController
            self._instalaciones_controller = InstalacionesController()
        return self._instalaciones_controller
    
    def get_contactos_controller(self):
        """Obtener controlador de contactos (inicialización perezosa)"""
        if self._contactos_controller is None:
            from controllers.contactos_controller import ContactosController
            self._contactos_controller = ContactosController()
        return self._contactos_controller
    
    # Propiedades para compatibilidad
    @property
    def usuarios(self):
        return self.get_usuarios_controller()
    
    @property
    def instalaciones(self):
        return self.get_instalaciones_controller()
    
    @property
    def contactos(self):
        return self.get_contactos_controller()


# Instancia global de controladores
controllers = ApplicationControllers()
