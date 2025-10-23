"""
Ventana principal refactorizada
"""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QStatusBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
# Importación removida para evitar inicialización temprana
from ui.tabs.usuarios_tab_refactored import UsuariosTab
from ui.tabs.instalaciones_tab_refactored import InstalacionesTab
from ui.tabs.contactos_tab_refactored import ContactosTab
from config.settings import COLOR_PRIMARY, COLOR_SUCCESS


class MainWindow(QMainWindow):
    """Ventana principal refactorizada"""
    
    def __init__(self, usuario_logueado):
        super().__init__()
        self.usuario_logueado = usuario_logueado
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz de usuario"""
        self.setWindowTitle("Panel Admin WFSA - v2.0.0")
        self.setMinimumSize(1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header con información del usuario
        header_layout = QHBoxLayout()
        
        # Título
        title_label = QLabel("🏢 Panel Admin WFSA")
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {COLOR_PRIMARY};
                padding: 15px;
            }}
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Info del usuario logueado
        user_info = QLabel(f"👤 {self.usuario_logueado.get('nombre_completo', 'Usuario')}")
        user_info.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                color: {COLOR_PRIMARY};
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
            }}
        """)
        header_layout.addWidget(user_info)
        
        layout.addLayout(header_layout)
        
        # Tabs principales
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0275AA;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)
        
        # Tab de usuarios (refactorizado)
        self.usuarios_tab = UsuariosTab()
        self.tab_widget.addTab(self.usuarios_tab, "👥 Usuarios")
        
        # Tab de instalaciones (refactorizado)
        self.instalaciones_tab = InstalacionesTab()
        self.tab_widget.addTab(self.instalaciones_tab, "🏭 Instalaciones")
        
        # Tab de contactos (refactorizado)
        self.contactos_tab = ContactosTab()
        self.tab_widget.addTab(self.contactos_tab, "👤 Contactos")
        
        # Conectar señales de todos los tabs
        self.usuarios_tab.status_message.connect(self.show_status_message)
        self.instalaciones_tab.status_message.connect(self.show_status_message)
        self.contactos_tab.status_message.connect(self.show_status_message)
        
        layout.addWidget(self.tab_widget)
        
        # Barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✅ Aplicación iniciada correctamente")
        
        # Aplicar estilos globales
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
        """)
    
    def show_status_message(self, message, duration=3000):
        """Mostrar mensaje en la barra de estado"""
        self.status_bar.showMessage(message, duration)
    
    def closeEvent(self, event):
        """Manejar cierre de la aplicación"""
        # Aquí podrías agregar lógica de limpieza si es necesario
        event.accept()
