"""
Aplicación principal refactorizada - Panel Admin WFSA v2.0.0
"""
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from ui.login_window import LoginWindow
from ui.main_window_refactored import MainWindow
from services.firebase_service import FirebaseService
from config.settings import APP_VERSION


class PanelAdminApp:
    """Aplicación principal refactorizada"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Panel Admin WFSA")
        self.app.setApplicationVersion(APP_VERSION)
        self.app.setOrganizationName("Worldwide")
        
        # Configurar estilos globales
        self.app.setStyleSheet("""
            QApplication {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QWidget {
                background-color: #f8f9fa;
            }
        """)
        
        self.login_window = None
        self.main_window = None
        self.firebase_service = FirebaseService()
    
    def run(self):
        """Ejecutar aplicación"""
        try:
            # Mostrar ventana de login
            self.show_login()
            
            # Ejecutar aplicación
            sys.exit(self.app.exec())
            
        except Exception as e:
            QMessageBox.critical(None, "Error Fatal", f"Error al iniciar la aplicación: {str(e)}")
            sys.exit(1)
    
    def show_login(self):
        """Mostrar ventana de login"""
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.on_login_success)
        self.login_window.show()
    
    def on_login_success(self, usuario_data):
        """Manejar login exitoso"""
        try:
            # Cerrar ventana de login
            self.login_window.close()
            
            # Mostrar ventana principal refactorizada
            self.main_window = MainWindow(usuario_data)
            self.main_window.show()
            
            print(f"✅ Usuario logueado: {usuario_data.get('email_login', 'N/A')}")
            print(f"🏗️ Arquitectura refactorizada v{APP_VERSION}")
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error al abrir la ventana principal: {str(e)}")
            self.show_login()  # Volver al login en caso de error


def main():
    """Función principal"""
    try:
        app = PanelAdminApp()
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Aplicación cerrada por el usuario")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
