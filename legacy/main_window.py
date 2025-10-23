"""
Ventana principal del Panel Admin
"""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from config.settings import *
from ui.usuarios_tab import UsuariosTab
from ui.contactos_tab import ContactosTab
from ui.instalaciones_tab import InstalacionesTab


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""
    
    def __init__(self, usuario_autenticado=None):
        super().__init__()
        self.usuario_autenticado = usuario_autenticado
        
        # Título con nombre del usuario
        if usuario_autenticado:
            nombre = usuario_autenticado.get('nombre_completo', 'Usuario')
            self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - {nombre}")
        else:
            self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Aplicar estilos
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLOR_BACKGROUND};
            }}
            QTabWidget::pane {{
                border: 1px solid #ddd;
                background-color: white;
            }}
            QTabBar::tab {{
                background-color: #f0f0f0;
                color: {COLOR_TEXT};
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_PRIMARY};
                color: white;
            }}
            QTabBar::tab:hover {{
                background-color: #e0e0e0;
            }}
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #025a8a;
            }}
            QPushButton:pressed {{
                background-color: #014060;
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {COLOR_PRIMARY};
            }}
            QTableWidget {{
                border: 1px solid #ddd;
                gridline-color: #f0f0f0;
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_PRIMARY};
                color: white;
            }}
            QHeaderView::section {{
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 2px solid {COLOR_PRIMARY};
                font-weight: bold;
            }}
        """)
        
        # Crear widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        
        # Agregar tabs
        try:
            print("[MAIN] Creando tab de Usuarios...")
            self.usuarios_tab = UsuariosTab()
            print("[MAIN] Tab Usuarios creado OK")
            
            print("[MAIN] Creando tab de Contactos...")
            self.contactos_tab = ContactosTab()
            print("[MAIN] Tab Contactos creado OK")
            
            print("[MAIN] Creando tab de Instalaciones...")
            self.instalaciones_tab = InstalacionesTab()
            print("[MAIN] Tab Instalaciones creado OK")
            
            print("[MAIN] Agregando tabs al widget...")
            self.tabs.addTab(self.usuarios_tab, "👤 Usuarios")
            self.tabs.addTab(self.contactos_tab, "📞 Contactos")
            self.tabs.addTab(self.instalaciones_tab, "🏢 Instalaciones")
            print("[MAIN] Tabs agregados OK")
            
            # Conectar señales
            print("[MAIN] Conectando señales...")
            self.usuarios_tab.status_message.connect(self.show_status_message)
            self.contactos_tab.status_message.connect(self.show_status_message)
            self.instalaciones_tab.status_message.connect(self.show_status_message)
            print("[MAIN] Señales conectadas OK")
        except Exception as e:
            print(f"[ERROR] Error al inicializar tabs: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error de Inicializacion",
                f"No se pudo inicializar la aplicacion:\n{str(e)}\n\n"
                "Verifica que las credenciales de Google Cloud esten configuradas correctamente."
            )
        
        layout.addWidget(self.tabs)
        
        
        # Barra de estado
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Mostrar información del usuario autenticado
        if usuario_autenticado:
            nombre = usuario_autenticado.get('nombre_completo', 'Usuario')
            rol = usuario_autenticado.get('nombre_rol', 'Administrador')
            email = usuario_autenticado.get('email_login', '')
            self.statusBar.showMessage(f"Sesion activa: {nombre} ({rol}) - {email}")
        else:
            self.statusBar.showMessage("Listo")
    
    def show_status_message(self, message: str, timeout: int = 3000):
        """Mostrar mensaje en la barra de estado"""
        self.statusBar.showMessage(message, timeout)
    
    def show_error(self, title: str, message: str):
        """Mostrar diálogo de error"""
        QMessageBox.critical(self, title, message)
    
    def show_success(self, title: str, message: str):
        """Mostrar diálogo de éxito"""
        QMessageBox.information(self, title, message)
    
    def show_warning(self, title: str, message: str):
        """Mostrar diálogo de advertencia"""
        QMessageBox.warning(self, title, message)
    
    def confirm(self, title: str, message: str) -> bool:
        """Mostrar diálogo de confirmación"""
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes
    

