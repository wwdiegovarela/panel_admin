"""
Ventana de Login para Panel Admin WFSA
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont
from services.firebase_service import FirebaseService
from services.bigquery_service import BigQueryService
from config.settings import COLOR_PRIMARY, COLOR_SECONDARY
import firebase_admin
from firebase_admin import auth as firebase_auth


class LoginWindow(QDialog):
    """Ventana de autenticación para el Panel Admin"""
    
    login_successful = Signal(dict)  # Señal para notificar login exitoso
    
    def __init__(self):
        super().__init__()
        self.firebase_service = FirebaseService()
        self.bigquery_service = BigQueryService()
        self.usuario_autenticado = None
        
        self.setWindowTitle("Iniciar Sesion - Panel Admin")
        self.setMinimumSize(450, 550)
        self.setMaximumSize(450, 550)
        self.setModal(True)
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz de login"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(40, 30, 40, 30)
        
        # Logo de la empresa
        from pathlib import Path
        logo_path = Path(__file__).parent.parent / "assets" / "images" / "logo.png"
        
        if logo_path.exists():
            logo_label = QLabel()
            logo_label.setFixedSize(200, 100)
            pixmap = QPixmap(str(logo_path))
            # Escalar el logo manteniendo aspecto
            scaled_pixmap = pixmap.scaled(200, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setScaledContents(False)
            layout.addWidget(logo_label, 0, Qt.AlignCenter)
        
        # Título
        titulo = QLabel("Panel de Administración")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setFixedHeight(30)
        titulo.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: 22px; font-weight: bold;")
        layout.addWidget(titulo)
        
        # Mensaje informativo
        info_label = QLabel("Ingresa tus credenciales de administrador")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setFixedHeight(20)
        info_label.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # Campo de email
        email_label = QLabel("Email:")
        email_label.setFixedHeight(20)
        email_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setFixedHeight(45)
        self.email_input.setPlaceholderText("tu.email@ejemplo.com")
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #0275AA;
            }
        """)
        layout.addWidget(self.email_input)
        
        # Campo de contraseña
        password_label = QLabel("Contraseña:")
        password_label.setFixedHeight(20)
        password_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setFixedHeight(45)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #0275AA;
            }
        """)
        self.password_input.returnPressed.connect(self.iniciar_sesion)
        layout.addWidget(self.password_input)
        
        layout.addSpacing(20)
        
        # Botón de login
        self.btn_login = QPushButton("Iniciar Sesión")
        self.btn_login.setFixedHeight(50)
        self.btn_login.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: white;
                padding: 15px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #025a8a;
            }}
            QPushButton:pressed {{
                background-color: #014670;
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
            }}
        """)
        self.btn_login.clicked.connect(self.iniciar_sesion)
        layout.addWidget(self.btn_login)
        
        layout.addSpacing(10)
        
        # Mensaje de advertencia
        warning_label = QLabel("Solo usuarios autorizados")
        warning_label.setAlignment(Qt.AlignCenter)
        warning_label.setFixedHeight(20)
        warning_label.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(warning_label)
        
        # Spacer al final
        layout.addStretch(1)
        
        # Estilo general
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
        """)
    
    def iniciar_sesion(self):
        """Procesar inicio de sesión"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        # Validar campos
        if not email or not password:
            QMessageBox.warning(self, "Campos requeridos", 
                              "Por favor ingresa email y contraseña")
            return
        
        # Deshabilitar botón mientras procesa
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Verificando...")
        
        try:
            # Autenticar usuario con email y contraseña
            print(f"[LOGIN] Autenticando usuario: {email}")
            usuario_firebase = self.firebase_service.authenticate_user(email, password)
            
            if not usuario_firebase:
                print(f"[LOGIN] Autenticación fallida para: {email}")
                QMessageBox.critical(self, "Error de Autenticacion",
                                   "Usuario no encontrado o credenciales invalidas")
                return
            
            print(f"[LOGIN] Usuario autenticado en Firebase: {usuario_firebase.get('uid')}")
            
            # Verificar en BigQuery que tenga permisos de admin
            print(f"[LOGIN] Consultando permisos en BigQuery...")
            usuarios = self.bigquery_service.get_usuarios_con_roles()
            usuario_data = None
            
            for usuario in usuarios:
                if usuario.get('email_login') == email:
                    usuario_data = usuario
                    break
            
            if not usuario_data:
                print(f"[LOGIN] Usuario no encontrado en BigQuery")
                QMessageBox.critical(self, "Error de Acceso",
                                   "Tu usuario no tiene acceso al Panel de Administracion.\n\n"
                                   "Contacta al administrador del sistema.")
                return
            
            print(f"[LOGIN] Usuario encontrado en BigQuery: {usuario_data.get('rol_id')}")
            
            # Verificar permisos de admin
            permisos = usuario_data.get('permisos', {})
            es_admin = permisos.get('es_admin', False)
            
            print(f"[LOGIN] Permisos de admin: {es_admin}")
            
            if not es_admin:
                print(f"[LOGIN] Usuario no tiene permisos de admin")
                QMessageBox.critical(self, "Acceso Denegado",
                                   f"Tu rol ({usuario_data.get('nombre_rol', 'Usuario')}) no tiene "
                                   f"permisos de administrador.\n\n"
                                   f"Solo administradores pueden acceder a este panel.")
                return
            
            # Verificar que el usuario esté activo
            if not usuario_data.get('activo', False):
                print(f"[LOGIN] Usuario está inactivo")
                QMessageBox.critical(self, "Usuario Inactivo",
                                   "Tu cuenta esta desactivada.\n\n"
                                   "Contacta al administrador del sistema.")
                return
            
            # Login exitoso
            self.usuario_autenticado = usuario_data
            
            # Emitir señal de login exitoso
            self.login_successful.emit(usuario_data)
            
            # Pasar directamente a la pantalla principal sin mensaje
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error",
                               f"Error al iniciar sesión:\n{str(e)}")
        
        finally:
            # Rehabilitar botón
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Iniciar Sesión")
    
    def get_usuario_autenticado(self):
        """Obtener datos del usuario autenticado"""
        return self.usuario_autenticado

