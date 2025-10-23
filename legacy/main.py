"""
Panel de Administración - WFSA
Gestión de usuarios, contactos e instalaciones
"""
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtGui import QIcon
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from config.settings import APP_NAME, APP_VERSION


def configurar_credenciales():
    """Configurar credenciales de Google Cloud automáticamente"""
    # Detectar si está corriendo desde .exe o desde Python
    if getattr(sys, 'frozen', False):
        # Corriendo desde .exe compilado
        base_path = Path(sys.executable).parent
    else:
        # Corriendo desde Python (desarrollo)
        base_path = Path(__file__).parent
    
    # Buscar archivo de credenciales
    # Primero intenta en la carpeta raíz
    credentials_file = base_path / "worldwide-470917-b0939d44c1ae.json"
    
    # Si no existe, intenta en subcarpeta "credenciales"
    if not credentials_file.exists():
        credentials_file = base_path / "credenciales" / "worldwide-470917-b0939d44c1ae.json"
    
    # Verificar si existe
    if credentials_file.exists():
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_file)
        print(f"[OK] Credenciales cargadas desde: {credentials_file}")
        return True
    else:
        # Mostrar error si no se encuentra
        print(f"[ERROR] No se encontró el archivo de credenciales")
        print(f"        Buscado en: {credentials_file}")
        return False


def main():
    """Punto de entrada de la aplicación"""
    # Configurar credenciales ANTES de crear la aplicación
    if not configurar_credenciales():
        # Crear app solo para mostrar mensaje de error
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Error de Configuración",
            "No se encontró el archivo de credenciales de Google Cloud.\n\n"
            "Por favor asegúrate de que el archivo:\n"
            "'worldwide-470917-b0939d44c1ae.json'\n\n"
            "esté en la misma carpeta que el ejecutable.\n\n"
            "Contacta al administrador si el problema persiste."
        )
        sys.exit(1)
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # Mostrar ventana de login PRIMERO
    print("[MAIN] Mostrando ventana de login...")
    login_window = LoginWindow()
    
    resultado_login = login_window.exec()
    print(f"[MAIN] Resultado del login: {resultado_login}")
    
    if resultado_login == QDialog.Accepted:
        # Login exitoso - obtener usuario autenticado
        usuario_autenticado = login_window.get_usuario_autenticado()
        print(f"[MAIN] Usuario autenticado: {usuario_autenticado.get('email_login') if usuario_autenticado else 'None'}")
        
        # Crear y mostrar ventana principal
        print("[MAIN] Creando ventana principal...")
        try:
            main_window = MainWindow(usuario_autenticado)
            print("[MAIN] Mostrando ventana principal...")
            main_window.show()
            print("[MAIN] Ventana principal mostrada correctamente")
            
            sys.exit(app.exec())
        except Exception as e:
            print(f"[ERROR] Error al crear ventana principal: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(None, "Error", f"Error al iniciar aplicacion:\n{str(e)}")
            sys.exit(1)
    else:
        # Login cancelado o fallido
        print("[INFO] Login cancelado por el usuario")
        sys.exit(0)


if __name__ == "__main__":
    main()

