"""
Tab de gestión de usuarios
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
    QDialog, QFormLayout, QComboBox, QCheckBox, QMessageBox,
    QHeaderView, QListWidget, QListWidgetItem, QDialogButtonBox, QGroupBox, QTabWidget,
    QScrollArea, QFrame, QApplication, QFileDialog, QTextEdit
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QColor
from services.firebase_service import FirebaseService
from services.bigquery_service import BigQueryService
from config.settings import (
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ERROR, COLOR_SECONDARY,
    COLOR_ADMIN, COLOR_SUBGERENTE, COLOR_JEFE, COLOR_SUPERVISOR, COLOR_GERENTE, COLOR_CLIENTE
)
from ui.loading_dialog import ProgressDialog
from ui.carga_masiva_dialog import CargaMasivaDialog
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime


class UsuariosTab(QWidget):
    """Tab para gestionar usuarios"""
    
    status_message = Signal(str, int)
    
    def __init__(self):
        super().__init__()
        self.firebase_service = FirebaseService()
        self.bigquery_service = BigQueryService()
        self.datos_cargados = False
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz de usuario"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        title = QLabel("Gestión de Usuarios")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLOR_PRIMARY};")
        layout.addWidget(title)
        
        # Barra de herramientas
        toolbar = QHBoxLayout()
        
        # Búsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar por email o nombre...")
        self.search_input.textChanged.connect(self.filtrar_usuarios)
        toolbar.addWidget(self.search_input)
        
        # Filtro por rol ← NUEVO
        self.rol_filter_combo = QComboBox()
        self.rol_filter_combo.addItem("Todos los roles", "")
        self.rol_filter_combo.addItem("ADMIN_WFSA", "ADMIN_WFSA")
        self.rol_filter_combo.addItem("SUBGERENTE_WFSA", "SUBGERENTE_WFSA")
        self.rol_filter_combo.addItem("JEFE_WFSA", "JEFE_WFSA")
        self.rol_filter_combo.addItem("SUPERVISOR_WFSA", "SUPERVISOR_WFSA")
        self.rol_filter_combo.addItem("GERENTE_WFSA", "GERENTE_WFSA")
        self.rol_filter_combo.addItem("CLIENTE", "CLIENTE")
        self.rol_filter_combo.currentTextChanged.connect(self.filtrar_usuarios)
        toolbar.addWidget(QLabel("Filtrar por rol:"))
        toolbar.addWidget(self.rol_filter_combo)
        
        # Botones
        btn_nuevo = QPushButton("➕ Nuevo Usuario")
        btn_nuevo.clicked.connect(self.nuevo_usuario)
        toolbar.addWidget(btn_nuevo)
        
        btn_carga_masiva = QPushButton("📊 Carga Masiva")
        btn_carga_masiva.clicked.connect(self.carga_masiva_usuarios)
        btn_carga_masiva.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SECONDARY};
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #d45e0a;
            }}
        """)
        toolbar.addWidget(btn_carga_masiva)
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.cargar_usuarios)
        toolbar.addWidget(btn_refresh)
        
        # Botón para limpiar cache ← NUEVO
        btn_clear_cache = QPushButton("🗑️ Limpiar Cache")
        btn_clear_cache.setToolTip("Limpiar cache de BigQuery para forzar actualización")
        btn_clear_cache.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #E64A19;
            }}
        """)
        btn_clear_cache.clicked.connect(self.limpiar_cache)
        toolbar.addWidget(btn_clear_cache)
        
        layout.addLayout(toolbar)
        
        # Tabla de usuarios
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "Email", "Nombre", "Cliente", "Rol", "Cargo", "Activo", "Ver Todas", "Acciones"
        ])
        
        # Configurar tabla
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.tabla)
    
    def get_rol_color(self, rol_id: str) -> str:
        """Obtiene el color para un rol específico (consistentes con la app móvil)"""
        colores = {
            'ADMIN_WFSA': COLOR_ADMIN,        # Púrpura
            'SUBGERENTE_WFSA': COLOR_SUBGERENTE,   # Naranja profundo
            'JEFE_WFSA': COLOR_JEFE,         # Rojo
            'SUPERVISOR_WFSA': COLOR_SUPERVISOR,   # Amarillo
            'GERENTE_WFSA': COLOR_GERENTE,      # Verde
            'CLIENTE': COLOR_CLIENTE            # Azul WFSA
        }
        return colores.get(rol_id, COLOR_CLIENTE)
    
    def showEvent(self, event):
        """Evento cuando se muestra la pestaña - lazy loading"""
        super().showEvent(event)
        if not self.datos_cargados:
            self.cargar_usuarios()
            self.datos_cargados = True
    
    def cargar_usuarios(self):
        """Cargar usuarios desde BigQuery"""
        try:
            self.status_message.emit("Cargando usuarios...", 0)
            # Usar el nuevo método que incluye roles
            usuarios = self.bigquery_service.get_usuarios_con_roles()
            self.usuarios_data = usuarios
            
            # Debug: imprimir información de roles
            print(f"[DEBUG] Usuarios cargados: {len(usuarios)}")
            for usuario in usuarios[:3]:  # Solo los primeros 3 para debug
                print(f"[DEBUG] Usuario: {usuario.get('email_login')} - Rol: {usuario.get('rol_id')} - Nombre Rol: {usuario.get('nombre_rol')}")
            
            self.mostrar_usuarios(usuarios)
            self.status_message.emit(f"{len(usuarios)} usuarios cargados", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar usuarios: {str(e)}")
            self.status_message.emit("Error al cargar usuarios", 5000)
    
    def mostrar_usuarios(self, usuarios):
        """Mostrar usuarios en la tabla"""
        self.tabla.setRowCount(len(usuarios))
        
        for i, usuario in enumerate(usuarios):
            # Email
            self.tabla.setItem(i, 0, QTableWidgetItem(usuario['email_login']))
            
            # Nombre
            self.tabla.setItem(i, 1, QTableWidgetItem(usuario['nombre_completo']))
            
            # Cliente (truncar si es muy largo)
            cliente_text = usuario['cliente_rol']
            if len(cliente_text) > 20:
                cliente_text = cliente_text[:17] + "..."
            cliente_item = QTableWidgetItem(cliente_text)
            cliente_item.setToolTip(usuario['cliente_rol'])  # Tooltip con texto completo
            self.tabla.setItem(i, 2, cliente_item)
            
            # Rol ← NUEVO
            rol_item = QTableWidgetItem(usuario.get('nombre_rol', 'Cliente'))
            rol_id = usuario.get('rol_id', 'CLIENTE')
            rol_item.setBackground(QColor(self.get_rol_color(rol_id)))
            rol_item.setForeground(QColor('white'))
            rol_item.setTextAlignment(Qt.AlignCenter)
            
            # Agregar tooltip con información del rol
            rol_tooltip = f"Rol: {usuario.get('nombre_rol', 'Cliente')}\n"
            rol_tooltip += f"ID: {rol_id}\n"
            if 'permisos' in usuario:
                permisos = usuario['permisos']
                rol_tooltip += "Permisos:\n"
                if permisos.get('es_admin', False):
                    rol_tooltip += "• Administrador\n"
                if permisos.get('puede_ver_cobertura', False):
                    rol_tooltip += "• Ver Cobertura\n"
                if permisos.get('puede_ver_encuestas', False):
                    rol_tooltip += "• Ver Encuestas\n"
                if permisos.get('puede_enviar_mensajes', False):
                    rol_tooltip += "• Enviar Mensajes\n"
                if permisos.get('puede_ver_empresas', False):
                    rol_tooltip += "• Ver Empresas\n"
                if permisos.get('puede_ver_metricas_globales', False):
                    rol_tooltip += "• Ver Métricas Globales\n"
                if permisos.get('puede_ver_trabajadores', False):
                    rol_tooltip += "• Ver Trabajadores\n"
                if permisos.get('puede_ver_mensajes_recibidos', False):
                    rol_tooltip += "• Ver Mensajes Recibidos\n"
            
            rol_item.setToolTip(rol_tooltip)
            self.tabla.setItem(i, 3, rol_item)
            
            # Cargo
            cargo = usuario.get('cargo', '') or ''
            self.tabla.setItem(i, 4, QTableWidgetItem(cargo))
            
            # Activo
            activo_item = QTableWidgetItem("✓" if usuario.get('activo', False) else "✗")
            activo_item.setTextAlignment(Qt.AlignCenter)
            if usuario.get('activo', False):
                activo_item.setForeground(Qt.green)
            else:
                activo_item.setForeground(Qt.red)
            self.tabla.setItem(i, 5, activo_item)
            
            # Ver todas instalaciones
            ver_todas = QTableWidgetItem("✓" if usuario.get('ver_todas_instalaciones', False) else "✗")
            ver_todas.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(i, 6, ver_todas)
            
            # Botones de acción
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(3)
            
            btn_permisos = QPushButton("🔑")
            btn_permisos.setToolTip("Editar Permisos de Instalaciones")
            btn_permisos.setStyleSheet(f"background-color: {COLOR_PRIMARY}; padding: 4px 8px; font-size: 11px;")
            btn_permisos.clicked.connect(lambda checked, u=usuario: self.editar_permisos(u))
            btn_layout.addWidget(btn_permisos)
            
            
            # Botón "Asignar Contactos" solo para usuarios CLIENTE
            rol_id = usuario.get('rol_id', '')
            if rol_id == 'CLIENTE':
                btn_contactos = QPushButton("📞")
                btn_contactos.setToolTip("Asignar Contactos")
                btn_contactos.setStyleSheet("background-color: #00BCD4; padding: 4px 8px; font-size: 11px;")
                btn_contactos.clicked.connect(lambda checked, u=usuario: self.asignar_contactos(u))
                btn_layout.addWidget(btn_contactos)
            
            btn_editar = QPushButton("✏️")
            btn_editar.setToolTip("Editar Usuario")
            btn_editar.setStyleSheet("background-color: #FF9800; padding: 4px 8px; font-size: 11px;")
            btn_editar.clicked.connect(lambda checked, u=usuario: self.editar_usuario(u))
            btn_layout.addWidget(btn_editar)
            
            btn_password = QPushButton("🔒")
            btn_password.setToolTip("Resetear Contraseña")
            btn_password.setStyleSheet("background-color: #9C27B0; padding: 4px 8px; font-size: 11px;")
            btn_password.clicked.connect(lambda checked, u=usuario: self.resetear_password(u))
            btn_layout.addWidget(btn_password)
            
            # Botón activar/desactivar
            activo = usuario.get('activo', True)
            btn_toggle = QPushButton("✓" if activo else "✗")
            btn_toggle.setToolTip("Desactivar Usuario" if activo else "Activar Usuario")
            btn_toggle.setStyleSheet(f"background-color: {'#4CAF50' if activo else '#F44336'}; padding: 4px 8px; font-size: 11px;")
            btn_toggle.clicked.connect(lambda checked, u=usuario: self.toggle_usuario(u))
            btn_layout.addWidget(btn_toggle)
            
            btn_eliminar = QPushButton("🗑️")
            btn_eliminar.setToolTip("Eliminar Usuario")
            btn_eliminar.setStyleSheet("background-color: #F44336; padding: 4px 8px; font-size: 11px;")
            btn_eliminar.clicked.connect(lambda checked, u=usuario: self.eliminar_usuario(u))
            btn_layout.addWidget(btn_eliminar)
            
            self.tabla.setCellWidget(i, 7, btn_widget)
    
    def filtrar_usuarios(self, texto=""):
        """Filtrar usuarios por texto de búsqueda y rol"""
        if not hasattr(self, 'usuarios_data'):
            return
        
        # Obtener filtros
        texto_busqueda = self.search_input.text().lower() if hasattr(self, 'search_input') else ""
        rol_filtro = self.rol_filter_combo.currentData() if hasattr(self, 'rol_filter_combo') else ""
        
        usuarios_filtrados = []
        
        for usuario in self.usuarios_data:
            # Filtro por texto
            cumple_texto = True
            if texto_busqueda:
                cumple_texto = (
                    texto_busqueda in usuario['email_login'].lower() or 
                    texto_busqueda in usuario['nombre_completo'].lower()
                )
            
            # Filtro por rol
            cumple_rol = True
            if rol_filtro:
                cumple_rol = usuario.get('rol_id', 'CLIENTE') == rol_filtro
            
            if cumple_texto and cumple_rol:
                usuarios_filtrados.append(usuario)
        
        self.mostrar_usuarios(usuarios_filtrados)
    
    def nuevo_usuario(self):
        """Abrir diálogo para crear nuevo usuario"""
        dialog = NuevoUsuarioDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.cargar_usuarios()
    
    def carga_masiva_usuarios(self):
        """Abrir diálogo para carga masiva de usuarios desde Excel"""
        dialog = CargaMasivaDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.cargar_usuarios()
    
    def editar_usuario(self, usuario):
        """Editar un usuario existente"""
        dialog = EditarUsuarioDialog(self, usuario)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_usuarios()
    
    def editar_permisos(self, usuario):
        """Editar permisos de un usuario"""
        dialog = PermisosDialog(usuario, self)
        if dialog.exec() == QDialog.Accepted:
            self.cargar_usuarios()
    
    def asignar_contactos(self, usuario):
        """Asignar contactos específicos por instalación a un usuario"""
        dialog = AsignarContactosDialog(self, usuario)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.status_message.emit("✅ Contactos asignados correctamente", 3000)
    
    def resetear_password(self, usuario):
        """Resetear contraseña de un usuario"""
        dialog = ResetPasswordDialog(self, usuario)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_usuarios()
    
    def toggle_usuario(self, usuario):
        """Activar o desactivar un usuario"""
        email = usuario['email_login']
        activo = usuario.get('activo', True)
        accion = "desactivar" if activo else "activar"
        
        respuesta = QMessageBox.question(
            self,
            f"Confirmar {accion}",
            f"¿Estás seguro de que quieres {accion} al usuario '{email}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                # Actualizar en Firebase
                if activo:
                    resultado_firebase = self.firebase_service.disable_user(email)
                else:
                    resultado_firebase = self.firebase_service.enable_user(email)
                
                if not resultado_firebase['success']:
                    raise Exception(resultado_firebase.get('error', 'Error en Firebase'))
                
                # Actualizar en BigQuery
                resultado_bq = self.bigquery_service.update_usuario(email, activo=not activo)
                
                if resultado_bq['success']:
                    self.status_message.emit(f"✅ Usuario {accion}do correctamente", 3000)
                    self.cargar_usuarios()
                else:
                    raise Exception(resultado_bq.get('error', 'Error en BigQuery'))
            
            except Exception as e:
                self.status_message.emit(f"❌ Error al {accion} usuario: {str(e)}", 5000)
                QMessageBox.critical(self, "Error", f"No se pudo {accion} el usuario:\n{str(e)}")
    
    def eliminar_usuario(self, usuario):
        """Eliminar un usuario"""
        email = usuario['email_login']
        
        respuesta = QMessageBox.warning(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de que quieres ELIMINAR al usuario '{email}'?\n\n"
            "Esta acción eliminará el usuario de Firebase y lo marcará como inactivo en BigQuery.\n"
            "⚠️ ESTA ACCIÓN NO SE PUEDE DESHACER.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                # Eliminar de Firebase
                resultado_firebase = self.firebase_service.delete_user(email)
                
                if not resultado_firebase['success']:
                    raise Exception(resultado_firebase.get('error', 'Error en Firebase'))
                
                # Marcar como inactivo en BigQuery
                resultado_bq = self.bigquery_service.delete_usuario(email)
                
                if resultado_bq['success']:
                    self.status_message.emit(f"✅ Usuario eliminado correctamente", 3000)
                    self.cargar_usuarios()
                else:
                    raise Exception(resultado_bq.get('error', 'Error en BigQuery'))
            
            except Exception as e:
                self.status_message.emit(f"❌ Error al eliminar usuario: {str(e)}", 5000)
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el usuario:\n{str(e)}")
    
    def cambiar_rol_usuario(self, email_login: str):
        """Cambiar el rol de un usuario existente"""
        try:
            # Obtener información del usuario actual
            usuarios = self.bigquery_service.get_usuarios_con_roles()
            usuario_actual = next((u for u in usuarios if u['email_login'] == email_login), None)
            
            if not usuario_actual:
                QMessageBox.warning(self, "Error", f"No se encontró el usuario: {email_login}")
                return
            
            # Obtener roles disponibles
            roles = self.bigquery_service.get_roles()
            
            # Crear diálogo para seleccionar nuevo rol
            dialog = QDialog(self)
            dialog.setWindowTitle("Cambiar Rol de Usuario")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(400)
            
            layout = QVBoxLayout(dialog)
            
            # Información del usuario
            info_label = QLabel(f"Usuario: {email_login}")
            info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(info_label)
            
            # Rol actual
            rol_actual = usuario_actual.get('nombre_rol', 'Cliente')
            rol_actual_label = QLabel(f"Rol actual: {rol_actual}")
            rol_actual_label.setStyleSheet("color: #666; font-size: 12px;")
            layout.addWidget(rol_actual_label)
            
            layout.addWidget(QLabel(""))  # Espacio
            
            # Selector de rol
            layout.addWidget(QLabel("Nuevo Rol:"))
            rol_combo = QComboBox()
            for rol in roles:
                rol_combo.addItem(rol['nombre_rol'], rol['rol_id'])
            
            # Seleccionar rol actual si existe
            rol_actual_id = usuario_actual.get('rol_id', 'CLIENTE')
            index_actual = rol_combo.findData(rol_actual_id)
            if index_actual >= 0:
                rol_combo.setCurrentIndex(index_actual)
            
            layout.addWidget(rol_combo)
            
            # Descripción del rol
            descripcion_label = QLabel()
            descripcion_label.setWordWrap(True)
            descripcion_label.setStyleSheet("color: gray; font-style: italic; padding: 5px; background-color: #f5f5f5; border-radius: 5px;")
            layout.addWidget(descripcion_label)
            
            # Grupo de permisos
            permisos_group = QGroupBox("Permisos del Rol Seleccionado")
            permisos_group.setStyleSheet("QGroupBox { font-weight: bold; }")
            permisos_layout = QVBoxLayout()
            
            permisos_checks = {
                'puede_ver_cobertura': QCheckBox("Ver Cobertura"),
                'puede_ver_encuestas': QCheckBox("Ver Encuestas"),
                'puede_enviar_mensajes': QCheckBox("Enviar Mensajes"),
                'puede_ver_empresas': QCheckBox("Ver Empresas"),
                'puede_ver_metricas_globales': QCheckBox("Ver Métricas Globales"),
                'puede_ver_trabajadores': QCheckBox("Ver Trabajadores"),
                'puede_ver_mensajes_recibidos': QCheckBox("Ver Mensajes Recibidos"),
                'es_admin': QCheckBox("Administrador")
            }
            
            for check in permisos_checks.values():
                check.setEnabled(False)  # Solo lectura
                check.setStyleSheet("color: gray;")
                permisos_layout.addWidget(check)
            
            permisos_group.setLayout(permisos_layout)
            layout.addWidget(permisos_group)
            
            # Actualizar descripción y permisos cuando cambia el rol
            def on_rol_changed(index):
                if index >= 0 and index < len(roles):
                    rol = roles[index]
                    descripcion_label.setText(rol.get('descripcion', ''))
                    
                    # Actualizar permisos
                    permisos = rol.get('permisos', {})
                    for key, check in permisos_checks.items():
                        check.setChecked(permisos.get(key, False))
            
            rol_combo.currentIndexChanged.connect(on_rol_changed)
            
            # Llamar una vez para mostrar el rol actual
            on_rol_changed(rol_combo.currentIndex())
            
            # Botones
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            if dialog.exec() == QDialog.Accepted:
                nuevo_rol_id = rol_combo.currentData()
                if nuevo_rol_id and nuevo_rol_id != rol_actual_id:
                    # Confirmar cambio
                    nuevo_rol_nombre = rol_combo.currentText()
                    reply = QMessageBox.question(
                        self, "Confirmar Cambio de Rol",
                        f"¿Estás seguro de cambiar el rol de {email_login} de '{rol_actual}' a '{nuevo_rol_nombre}'?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        # Actualizar rol en BigQuery
                        result = self.bigquery_service.actualizar_rol_usuario(email_login, nuevo_rol_id)
                        if result['success']:
                            QMessageBox.information(self, "Éxito", f"Rol actualizado de '{rol_actual}' a '{nuevo_rol_nombre}' para {email_login}")
                            self.cargar_usuarios()
                        else:
                            QMessageBox.critical(self, "Error", f"Error al actualizar rol: {result['error']}")
                elif nuevo_rol_id == rol_actual_id:
                    QMessageBox.information(self, "Información", "El usuario ya tiene el rol seleccionado")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cambiar rol: {str(e)}")
    
    def cambiar_rol_usuario_seleccionado(self):
        """Cambiar rol del usuario seleccionado en la tabla"""
        current_row = self.tabla.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Advertencia", "Selecciona un usuario de la tabla")
            return
        
        email_login = self.tabla.item(current_row, 0).text()
        self.cambiar_rol_usuario(email_login)
    
    def limpiar_cache(self):
        """Limpiar cache de BigQuery para forzar actualización"""
        try:
            self.bigquery_service.clear_cache()
            self.status_message.emit("✅ Cache limpiado, recargando datos...", 2000)
            self.cargar_usuarios()
        except Exception as e:
            QMessageBox.warning(self, "Advertencia", f"Error al limpiar cache: {str(e)}")


class NuevoUsuarioDialog(QDialog):
    """Diálogo para crear un nuevo usuario"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.firebase_service = FirebaseService()
        self.bigquery_service = BigQueryService()
        self.roles_disponibles = []
        self.clientes_disponibles = []
        self.setWindowTitle("Nuevo Usuario")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.init_ui()
        self.cargar_roles()
        # Cargar instalaciones automáticamente (ya no necesitamos cargar clientes por separado)
        self.cargar_instalaciones_clientes()
    
    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout(self)
        
        # Formulario
        form = QFormLayout()
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("usuario@ejemplo.com")
        form.addRow("Email:", self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Mínimo 6 caracteres")
        form.addRow("Contraseña:", self.password_input)
        
        self.nombre_input = QLineEdit()
        form.addRow("Nombre Completo:", self.nombre_input)
        
        # Campo cliente (se construye automáticamente)
        self.cliente_display = QLineEdit()
        self.cliente_display.setReadOnly(True)
        self.cliente_display.setPlaceholderText("Se construye automáticamente basado en las instalaciones seleccionadas")
        self.cliente_display.setStyleSheet("background-color: #f5f5f5; color: #666;")
        form.addRow("Cliente (Auto):", self.cliente_display)
        
        # Rol ← NUEVO
        self.rol_combo = QComboBox()
        self.rol_combo.currentIndexChanged.connect(self.on_rol_changed)
        form.addRow("Rol:", self.rol_combo)
        
        # Descripción del rol ← NUEVO
        self.rol_descripcion = QLabel()
        self.rol_descripcion.setWordWrap(True)
        self.rol_descripcion.setStyleSheet("color: gray; font-style: italic; font-size: 11px;")
        form.addRow("", self.rol_descripcion)
        
        self.cargo_input = QLineEdit()
        self.cargo_input.setPlaceholderText("Ej: Supervisor")
        form.addRow("Cargo:", self.cargo_input)
        
        self.telefono_input = QLineEdit()
        self.telefono_input.setPlaceholderText("+56912345678")
        form.addRow("Teléfono:", self.telefono_input)
        
        self.ver_todas_check = QCheckBox("Puede ver todas las instalaciones del cliente")
        self.ver_todas_check.stateChanged.connect(self.toggle_instalaciones)
        form.addRow("", self.ver_todas_check)
        
        # Checkbox "Es contacto?" (solo para roles != CLIENTE)
        self.es_contacto_check = QCheckBox("Es contacto de WhatsApp")
        self.es_contacto_check.setStyleSheet("color: #0275AA; font-weight: bold;")
        self.es_contacto_check.setToolTip("Marcar si este usuario también debe aparecer como contacto en WhatsApp")
        self.es_contacto_check.setVisible(False)  # Oculto por defecto, se muestra según rol
        form.addRow("", self.es_contacto_check)
        
        layout.addLayout(form)
        
        # Grupo de instalaciones
        instalaciones_group = QGroupBox("Instalaciones Permitidas")
        instalaciones_group_layout = QVBoxLayout()
        
        # Filtros para instalaciones
        filtros_layout = QHBoxLayout()
        
        # Filtro por zona
        filtros_layout.addWidget(QLabel("Filtrar por zona:"))
        self.zona_filter = QComboBox()
        self.zona_filter.addItem("Todas las zonas", "")
        self.zona_filter.currentTextChanged.connect(self.filtrar_instalaciones)
        filtros_layout.addWidget(self.zona_filter)
        
        # Filtro por cliente
        filtros_layout.addWidget(QLabel("Filtrar por cliente:"))
        self.cliente_filter = QComboBox()
        self.cliente_filter.addItem("Todos los clientes", "")
        self.cliente_filter.currentTextChanged.connect(self.filtrar_instalaciones)
        filtros_layout.addWidget(self.cliente_filter)
        
        # Botón "Seleccionar todas"
        self.seleccionar_todas_inst_check = QCheckBox("Seleccionar todas las instalaciones visibles")
        self.seleccionar_todas_inst_check.setStyleSheet("color: #0275AA; font-weight: bold;")
        self.seleccionar_todas_inst_check.stateChanged.connect(self.toggle_todas_instalaciones)
        filtros_layout.addWidget(self.seleccionar_todas_inst_check)
        
        instalaciones_group_layout.addLayout(filtros_layout)
        
        inst_hint = QLabel("Por defecto se muestran todas las instalaciones. Usa los filtros para reducir la lista.")
        inst_hint.setStyleSheet("color: gray; font-size: 11px; font-style: italic;")
        instalaciones_group_layout.addWidget(inst_hint)
        
        # Contenedor con scroll para checkboxes de instalaciones
        scroll_instalaciones = QScrollArea()
        scroll_instalaciones.setWidgetResizable(True)
        scroll_instalaciones.setMaximumHeight(350)
        scroll_instalaciones.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                background-color: white;
            }
        """)
        
        self.instalaciones_widget = QFrame()
        self.instalaciones_layout = QVBoxLayout(self.instalaciones_widget)
        self.instalaciones_layout.setContentsMargins(8, 8, 8, 8)
        self.instalaciones_layout.setSpacing(5)
        
        # Aquí se agregarán los checkboxes dinámicamente
        self.instalaciones_checks = {}  # {instalacion_rol: QCheckBox}
        self.instalaciones_con_cliente = {}  # {instalacion_rol: cliente_rol}
        
        scroll_instalaciones.setWidget(self.instalaciones_widget)
        instalaciones_group_layout.addWidget(scroll_instalaciones)
        
        instalaciones_group.setLayout(instalaciones_group_layout)
        layout.addWidget(instalaciones_group)
        
        # Grupo de permisos ← NUEVO
        # Información adicional del rol (solo descripción)
        rol_info_label = QLabel("El rol seleccionado determinará los permisos del usuario en el sistema.")
        rol_info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px; background-color: #f5f5f5; border-radius: 5px;")
        rol_info_label.setWordWrap(True)
        layout.addWidget(rol_info_label)
        
        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.crear_usuario)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def cargar_roles(self):
        """Cargar roles disponibles"""
        try:
            self.roles_disponibles = self.bigquery_service.get_roles()
            
            for rol in self.roles_disponibles:
                self.rol_combo.addItem(rol['nombre_rol'], rol['rol_id'])
            
            # Seleccionar CLIENTE por defecto
            index = self.rol_combo.findData('CLIENTE')
            if index >= 0:
                self.rol_combo.setCurrentIndex(index)
        
        except Exception as e:
            QMessageBox.warning(self, "Advertencia", f"No se pudieron cargar los roles: {str(e)}")
            # Agregar rol por defecto
            self.rol_combo.addItem("Cliente", "CLIENTE")
    
    def cargar_clientes(self):
        """Ya no es necesario cargar clientes por separado - se hace automáticamente"""
        # Este método ya no se usa, pero lo mantenemos por compatibilidad
        pass
    
    def toggle_todos_clientes(self):
        """Seleccionar/deseleccionar todos los clientes"""
        seleccionar_todos = self.seleccionar_todos_clientes_check.isChecked()
        for checkbox in self.clientes_checks.values():
            checkbox.setChecked(seleccionar_todos)
    
    def cargar_instalaciones_clientes(self):
        """Cargar todas las instalaciones por defecto con filtros"""
        # Limpiar instalaciones actuales
        for checkbox in self.instalaciones_checks.values():
            checkbox.deleteLater()
        self.instalaciones_checks.clear()
        self.instalaciones_con_cliente.clear()
        
        try:
            # Cargar TODAS las instalaciones por defecto
            instalaciones = self.bigquery_service.get_instalaciones_con_zonas()
            
            # Guardar todas las instalaciones para filtrado
            self.todas_instalaciones = instalaciones
            
            # Cargar filtros
            self.cargar_filtros_instalaciones()
            
            # Mostrar todas las instalaciones inicialmente
            self.mostrar_instalaciones_filtradas()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las instalaciones: {str(e)}")
    
    def cargar_filtros_instalaciones(self):
        """Cargar opciones de filtros para instalaciones"""
        if not hasattr(self, 'todas_instalaciones'):
            return
        
        # Limpiar filtros existentes
        self.zona_filter.clear()
        self.cliente_filter.clear()
        
        # Agregar opción "Todas"
        self.zona_filter.addItem("Todas las zonas", "")
        self.cliente_filter.addItem("Todos los clientes", "")
        
        # Obtener zonas únicas
        zonas = set()
        clientes = set()
        
        for inst in self.todas_instalaciones:
            if inst.get('zona'):
                zonas.add(inst['zona'])
            if inst.get('cliente_rol'):
                clientes.add(inst['cliente_rol'])
        
        # Agregar zonas al filtro
        for zona in sorted(zonas):
            self.zona_filter.addItem(zona, zona)
        
        # Agregar clientes al filtro
        for cliente in sorted(clientes):
            self.cliente_filter.addItem(cliente, cliente)
        
        # Conectar señal para actualizar clientes cuando cambie la zona
        self.zona_filter.currentTextChanged.connect(self.actualizar_clientes_por_zona)
    
    def filtrar_instalaciones(self):
        """Filtrar instalaciones según los filtros seleccionados"""
        if not hasattr(self, 'todas_instalaciones'):
            return
        
        zona_seleccionada = self.zona_filter.currentData()
        cliente_seleccionado = self.cliente_filter.currentData()
        
        # Filtrar instalaciones
        instalaciones_filtradas = []
        for inst in self.todas_instalaciones:
            cumple_zona = not zona_seleccionada or inst.get('zona') == zona_seleccionada
            cumple_cliente = not cliente_seleccionado or inst.get('cliente_rol') == cliente_seleccionado
            
            if cumple_zona and cumple_cliente:
                instalaciones_filtradas.append(inst)
        
        # Mostrar instalaciones filtradas
        self.mostrar_instalaciones_filtradas(instalaciones_filtradas)
    
    def actualizar_clientes_por_zona(self):
        """Actualizar lista de clientes según la zona seleccionada"""
        if not hasattr(self, 'todas_instalaciones'):
            return
        
        zona_seleccionada = self.zona_filter.currentData()
        
        # Guardar el cliente actualmente seleccionado
        cliente_actual = self.cliente_filter.currentData()
        
        # Limpiar filtro de clientes
        self.cliente_filter.clear()
        self.cliente_filter.addItem("Todos los clientes", "")
        
        # Obtener clientes únicos de la zona seleccionada
        clientes_zona = set()
        
        for inst in self.todas_instalaciones:
            # Si no hay zona seleccionada, mostrar todos los clientes
            if not zona_seleccionada:
                if inst.get('cliente_rol'):
                    clientes_zona.add(inst['cliente_rol'])
            else:
                # Si hay zona seleccionada, solo mostrar clientes de esa zona
                if inst.get('zona') == zona_seleccionada and inst.get('cliente_rol'):
                    clientes_zona.add(inst['cliente_rol'])
        
        # Agregar clientes al filtro
        for cliente in sorted(clientes_zona):
            self.cliente_filter.addItem(cliente, cliente)
        
        # Intentar restaurar el cliente seleccionado si aún está disponible
        if cliente_actual and cliente_actual in [self.cliente_filter.itemData(i) for i in range(self.cliente_filter.count())]:
            index = self.cliente_filter.findData(cliente_actual)
            if index >= 0:
                self.cliente_filter.setCurrentIndex(index)
        
        # Aplicar filtros automáticamente
        self.filtrar_instalaciones()
    
    def mostrar_instalaciones_filtradas(self, instalaciones=None):
        """Mostrar instalaciones en la lista con checkboxes"""
        # Limpiar instalaciones actuales
        for checkbox in self.instalaciones_checks.values():
            checkbox.deleteLater()
        self.instalaciones_checks.clear()
        self.instalaciones_con_cliente.clear()
        
        # Limpiar el layout completamente
        while self.instalaciones_layout.count():
            child = self.instalaciones_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if instalaciones is None:
            instalaciones = getattr(self, 'todas_instalaciones', [])
        
        # Si no hay instalaciones que coincidan con los filtros, mostrar mensaje
        if not instalaciones:
            no_results_label = QLabel("No hay instalaciones que coincidan con los filtros seleccionados.")
            no_results_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
            no_results_label.setAlignment(Qt.AlignCenter)
            self.instalaciones_layout.addWidget(no_results_label)
            return
        
        try:
            for inst in instalaciones:
                instalacion_rol = inst['instalacion_rol']
                cliente_rol = inst.get('cliente_rol', 'Sin cliente')
                zona = inst.get('zona', 'Sin zona')
                
                # Crear texto descriptivo
                texto_instalacion = f"{instalacion_rol} ({cliente_rol})"
                if zona:
                    texto_instalacion += f" - Zona: {zona}"
                
                # Crear contenedor horizontal para checkbox y texto
                container = QWidget()
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 2, 0, 2)
                container_layout.setSpacing(8)
                
                # Crear checkbox
                checkbox = QCheckBox()
                checkbox.setFixedSize(18, 18)
                checkbox.setStyleSheet("""
                            QCheckBox::indicator {
                                width: 18px;
                                height: 18px;
                        border: 2px solid #ccc;
                        border-radius: 3px;
                        background-color: white;
                            }
                            QCheckBox::indicator:checked {
                                background-color: #0275AA;
                                border: 2px solid #0275AA;
                        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
                    }
                    QCheckBox::indicator:hover {
                                border: 2px solid #0275AA;
                            }
                        """)
                
                # Crear label para el texto con word wrap
                label = QLabel(texto_instalacion)
                label.setWordWrap(True)
                label.setStyleSheet("""
                    QLabel {
                        font-size: 13px;
                        color: #333;
                        padding: 2px;
                    }
                """)
                label.setMinimumHeight(20)
                
                # Conectar el checkbox al label para que sea clickeable
                checkbox.toggled.connect(lambda checked, lbl=label: lbl.setStyleSheet("""
                    QLabel {
                        font-size: 13px;
                        color: #333;
                        padding: 2px;
                        text-decoration: %s;
                    }
                """ % ("line-through" if checked else "none")))
                
                # Agregar al layout
                container_layout.addWidget(checkbox)
                container_layout.addWidget(label, 1)  # El 1 hace que el label tome el espacio restante
                
                # Conectar evento para actualizar cliente automáticamente
                checkbox.stateChanged.connect(self.actualizar_cliente_automatico)
                
                self.instalaciones_checks[instalacion_rol] = checkbox
                self.instalaciones_con_cliente[instalacion_rol] = cliente_rol
                self.instalaciones_layout.addWidget(container)
            
            # Agregar spacer al final
            self.instalaciones_layout.addStretch()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al mostrar instalaciones: {str(e)}")
    
    def actualizar_cliente_automatico(self):
        """Actualizar campo cliente basado en instalaciones seleccionadas"""
        clientes_seleccionados = set()
        
        for instalacion_rol, checkbox in self.instalaciones_checks.items():
            if checkbox.isChecked():
                cliente = self.instalaciones_con_cliente.get(instalacion_rol)
                if cliente:
                    clientes_seleccionados.add(cliente)
        
        # Actualizar campo cliente
        if clientes_seleccionados:
            cliente_text = ", ".join(sorted(clientes_seleccionados))
            self.cliente_display.setText(cliente_text)
        else:
            self.cliente_display.setText("")
    
    def toggle_todas_instalaciones(self):
        """Seleccionar/deseleccionar todas las instalaciones visibles"""
        seleccionar_todas = self.seleccionar_todas_inst_check.isChecked()
        for checkbox in self.instalaciones_checks.values():
            checkbox.setChecked(seleccionar_todas)
    
    def toggle_instalaciones(self):
        """Habilitar/deshabilitar checkboxes de instalaciones"""
        ver_todas = self.ver_todas_check.isChecked()
        for checkbox in self.instalaciones_checks.values():
            checkbox.setEnabled(not ver_todas)
    
    def on_rol_changed(self, index):
        """Actualizar cuando cambia el rol"""
        if index < 0 or index >= len(self.roles_disponibles):
            return
        
        rol = self.roles_disponibles[index]
        rol_id = rol.get('rol_id', '')
        
        # Actualizar descripción
        self.rol_descripcion.setText(rol.get('descripcion', ''))
        
        # Mostrar/ocultar checkbox "Es contacto?" solo si NO es CLIENTE
        if rol_id != 'CLIENTE':
            self.es_contacto_check.setVisible(True)
        else:
            self.es_contacto_check.setVisible(False)
            self.es_contacto_check.setChecked(False)
    
    def crear_usuario(self):
        """Crear usuario en Firebase y BigQuery"""
        # Validar campos
        email = self.email_input.text().strip()
        password = self.password_input.text()
        nombre = self.nombre_input.text().strip()
        rol_id = self.rol_combo.currentData()
        
        # Obtener instalaciones seleccionadas
        instalaciones_seleccionadas = {}
        for instalacion_rol, checkbox in self.instalaciones_checks.items():
            if checkbox.isChecked():
                cliente_rol = self.instalaciones_con_cliente.get(instalacion_rol)
                if cliente_rol:
                    instalaciones_seleccionadas[instalacion_rol] = cliente_rol
        
        print(f"[DEBUG] Instalaciones seleccionadas: {len(instalaciones_seleccionadas)}")
        print(f"[DEBUG] Ver todas instalaciones: {self.ver_todas_check.isChecked()}")
        print(f"[DEBUG] Es contacto: {self.es_contacto_check.isChecked()}")
        print(f"[DEBUG] Rol ID: {rol_id}")
        
        if not all([email, password, nombre]):
            QMessageBox.warning(self, "Campos requeridos", 
                              "Por favor completa todos los campos obligatorios")
            return
        
        if not instalaciones_seleccionadas:
            QMessageBox.warning(self, "Instalaciones requeridas", 
                              "Por favor selecciona al menos una instalación")
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "Contraseña inválida",
                              "La contraseña debe tener al menos 6 caracteres")
            return
        
        # Construir cliente_rol basado en instalaciones seleccionadas
        clientes_unicos = set(instalaciones_seleccionadas.values())
        cliente_rol_concatenado = ",".join(sorted(clientes_unicos))
        
        # Calcular pasos totales
        total_pasos = 2  # Firebase + BigQuery
        if instalaciones_seleccionadas:
            total_pasos += 1  # Instalaciones
        if self.es_contacto_check.isChecked() and rol_id != 'CLIENTE':
            total_pasos += 2  # Crear contacto + Sincronizar instalaciones
        
        # Mostrar diálogo de progreso
        progress = ProgressDialog(self, "Creando Usuario", total_pasos)
        progress.show()
        QApplication.processEvents()
        
        try:
            # PASO 1: Crear en Firebase
            progress.update_progress(1, "Creando usuario en Firebase Authentication...")
            result = self.firebase_service.create_user(email, password, nombre)
            
            if not result['success']:
                progress.close()
                QMessageBox.critical(self, "Error", result['error'])
                return
            
            firebase_uid = result['uid']
            
            # PASO 2: Crear en BigQuery
            progress.update_progress(2, "Guardando usuario en BigQuery...")
            result_bq = self.bigquery_service.create_usuario(
                email=email,
                firebase_uid=firebase_uid,
                cliente_rol=cliente_rol_concatenado,
                nombre_completo=nombre,
                rol_id=rol_id,
                cargo=self.cargo_input.text().strip() or None,
                telefono=self.telefono_input.text().strip() or None,
                ver_todas_instalaciones=self.ver_todas_check.isChecked()
            )
            
            if not result_bq['success']:
                progress.close()
                QMessageBox.critical(self, "Error", 
                                  f"Usuario creado en Firebase pero error en BigQuery: {result_bq['error']}")
                return
            
            paso_actual = 2
            
            # PASO 3: Guardar instalaciones seleccionadas (SIEMPRE asignar si hay seleccionadas)
                if instalaciones_seleccionadas:
                    paso_actual += 1
                    progress.update_progress(paso_actual, f"Asignando {len(instalaciones_seleccionadas)} instalaciones...")
                print(f"[DEBUG] Asignando instalaciones: {instalaciones_seleccionadas}")
                result_instalaciones = self.bigquery_service.asignar_instalaciones_multi_cliente(
                        email,
                        instalaciones_seleccionadas
                    )
                print(f"[DEBUG] Resultado asignación instalaciones: {result_instalaciones}")
            else:
                print(f"[DEBUG] No se asignan instalaciones - No hay instalaciones seleccionadas")
            
            # PASO 4 y 5: Si está marcado como contacto, crear y sincronizar
            if self.es_contacto_check.isChecked() and rol_id != 'CLIENTE':
                paso_actual += 1
                progress.update_progress(paso_actual, "Creando contacto de WhatsApp...")
                result_contacto = self.bigquery_service.create_contacto(
                    nombre=nombre,
                    telefono=self.telefono_input.text().strip() or None,
                    cargo=self.cargo_input.text().strip() or None,
                    email=email,
                    es_usuario_app=True
                )
                
                # Sincronizar instalaciones del usuario con instalaciones del contacto
                if result_contacto['success'] and instalaciones_seleccionadas:
                    paso_actual += 1
                    progress.update_progress(paso_actual, "Sincronizando instalaciones del contacto...")
                    self.bigquery_service.sincronizar_instalaciones_contacto(
                        email,
                        instalaciones_seleccionadas
                    )
            
            progress.close()
            
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Error inesperado:\n{str(e)}")
            return
        
        clientes_texto = ", ".join(clientes_unicos)
        mensaje_exito = f"Usuario {email} creado exitosamente\nClientes: {clientes_texto}\nRol: {self.rol_combo.currentText()}"
        
        # Información sobre instalaciones
        if self.ver_todas_check.isChecked():
            mensaje_exito += "\n🌐 Puede ver TODAS las instalaciones"
        else:
            num_instalaciones = sum(1 for cb in self.instalaciones_checks.values() if cb.isChecked())
            if num_instalaciones > 0:
                mensaje_exito += f"\n📍 {num_instalaciones} instalaciones asignadas"
        
        if self.es_contacto_check.isChecked() and rol_id != 'CLIENTE':
            mensaje_exito += "\n✅ También creado como contacto de WhatsApp"
        
        QMessageBox.information(self, "Éxito", mensaje_exito)
        self.accept()


class PermisosDialog(QDialog):
    """Diálogo para editar permisos de un usuario"""
    
    def __init__(self, usuario, parent=None):
        super().__init__(parent)
        self.usuario = usuario
        self.bigquery_service = BigQueryService()
        self.instalaciones_con_cliente = {}  # {instalacion_rol: cliente_rol}
        self.instalaciones_checks = {}  # {instalacion_rol: {'puede_ver': QCheckBox, 'requiere_encuesta': QCheckBox}}
        self.todas_instalaciones = []  # Todas las instalaciones disponibles
        self.setWindowTitle(f"Permisos - {usuario['nombre_completo']}")
        self.setModal(True)
        self.setMinimumSize(1200, 800)
        self.resize(1200, 800)
        self.init_ui()
        self.cargar_datos()
    
    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout(self)
        
        # Info del usuario
        info_label = QLabel(f"<b>Usuario:</b> {self.usuario['email_login']}<br>"
                           f"<b>Cliente:</b> {self.usuario['cliente_rol']}")
        layout.addWidget(info_label)
        
        
        # Filtros para instalaciones
        filtros_group = QGroupBox("Filtros para instalaciones")
        filtros_layout = QHBoxLayout(filtros_group)
        
        # Filtro por zona
        filtros_layout.addWidget(QLabel("Zona:"))
        self.zona_filter = QComboBox()
        self.zona_filter.addItem("Todas las zonas")
        self.zona_filter.currentTextChanged.connect(self.actualizar_clientes_por_zona)
        filtros_layout.addWidget(self.zona_filter)
        
        # Filtro por cliente
        filtros_layout.addWidget(QLabel("Cliente:"))
        self.cliente_filter = QComboBox()
        self.cliente_filter.addItem("Todos los clientes")
        self.cliente_filter.currentTextChanged.connect(self.filtrar_instalaciones)
        filtros_layout.addWidget(self.cliente_filter)
        
        # Botón para filtrar
        self.filtrar_btn = QPushButton("🔍 Filtrar")
        self.filtrar_btn.clicked.connect(self.filtrar_instalaciones)
        filtros_layout.addWidget(self.filtrar_btn)
        
        # Botón para seleccionar todas las visibles
        self.seleccionar_todas_check = QCheckBox("Seleccionar todas las instalaciones visibles")
        self.seleccionar_todas_check.stateChanged.connect(self.toggle_todas_instalaciones)
        filtros_layout.addWidget(self.seleccionar_todas_check)
        
        filtros_layout.addStretch()
        layout.addWidget(filtros_group)
        
        # Instalaciones
        group_inst = QGroupBox("Instalaciones Permitidas")
        group_layout = QVBoxLayout(group_inst)
        
        # Encabezados con mejor espaciado
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 10, 20, 10)
        header_layout.setSpacing(20)
        
        # Columna 1: Instalación (más ancha)
        inst_label = QLabel("<b>Instalación</b>")
        inst_label.setMinimumWidth(400)
        inst_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        header_layout.addWidget(inst_label)
        
        # Columna 2: Puede ver
        puede_ver_label = QLabel("<b>Puede ver</b>")
        puede_ver_label.setMinimumWidth(120)
        puede_ver_label.setAlignment(Qt.AlignCenter)
        puede_ver_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        header_layout.addWidget(puede_ver_label)
        
        # Columna 3: Requiere encuesta
        requiere_encuesta_label = QLabel("<b>Requiere encuesta<br>individual</b>")
        requiere_encuesta_label.setMinimumWidth(150)
        requiere_encuesta_label.setAlignment(Qt.AlignCenter)
        requiere_encuesta_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        header_layout.addWidget(requiere_encuesta_label)
        
        header_layout.addStretch()
        group_layout.addWidget(header_widget)
        
        # Contenedor con scroll para checkboxes de instalaciones
        scroll_instalaciones = QScrollArea()
        scroll_instalaciones.setWidgetResizable(True)
        scroll_instalaciones.setMinimumHeight(400)
        scroll_instalaciones.setMaximumHeight(500)
        scroll_instalaciones.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                background-color: white;
                border-radius: 5px;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #ccc;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #999;
            }
        """)
        
        # Tabla de instalaciones con columnas separadas
        self.instalaciones_table = QTableWidget()
        self.instalaciones_table.setColumnCount(4)
        self.instalaciones_table.setHorizontalHeaderLabels([
            "Instalación", 
            "Zona", 
            "Puede ver", 
            "Requiere encuesta individual"
        ])
        
        # Configurar estilos de la tabla
        self.instalaciones_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                gridline-color: #e0e0e0;
                selection-background-color: #f0f8ff;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #f0f8ff;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #0275AA;
                font-weight: bold;
                color: #333;
            }
        """)
        
        # Configurar columnas
        self.instalaciones_table.setColumnWidth(0, 300)  # Instalación
        self.instalaciones_table.setColumnWidth(1, 150)  # Zona
        self.instalaciones_table.setColumnWidth(2, 100)   # Puede ver
        self.instalaciones_table.setColumnWidth(3, 150)   # Requiere encuesta
        
        # Deshabilitar edición de texto
        self.instalaciones_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        scroll_instalaciones.setWidget(self.instalaciones_table)
        group_layout.addWidget(scroll_instalaciones)
        
        layout.addWidget(group_inst)
        
        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.guardar_permisos)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def cargar_datos(self):
        """Cargar instalaciones y permisos actuales"""
        try:
            # Cargar todas las instalaciones disponibles
            self.todas_instalaciones = self.bigquery_service.get_instalaciones_con_zonas()
            
            # Cargar instalaciones asignadas al usuario con detalles
            self.instalaciones_detalle = self.bigquery_service.get_instalaciones_usuario_detalle(
                self.usuario['email_login']
            )
            
            # Cargar filtros
            self.cargar_filtros_instalaciones()
            
            # Mostrar todas las instalaciones inicialmente
            self.mostrar_instalaciones_filtradas(self.todas_instalaciones)
            
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos: {str(e)}")
    
    def cargar_filtros_instalaciones(self):
        """Cargar opciones de filtros basadas en las instalaciones disponibles"""
        try:
            # Cargar zonas únicas
            zonas = set()
            clientes = set()
            
            for inst in self.todas_instalaciones:
                if inst.get('zona'):
                    zonas.add(inst['zona'])
                if inst.get('cliente_rol'):
                    clientes.add(inst['cliente_rol'])
                        # Guardar relación instalación -> cliente
                        self.instalaciones_con_cliente[inst['instalacion_rol']] = inst['cliente_rol']
            
            # Cargar zonas en el combo
            self.zona_filter.clear()
            self.zona_filter.addItem("Todas las zonas")
            for zona in sorted(zonas):
                self.zona_filter.addItem(zona)
            
            # Cargar clientes en el combo
            self.cliente_filter.clear()
            self.cliente_filter.addItem("Todos los clientes")
            for cliente in sorted(clientes):
                self.cliente_filter.addItem(cliente)
                
        except Exception as e:
            print(f"Error al cargar filtros: {e}")
    
    def actualizar_clientes_por_zona(self):
        """Actualizar lista de clientes basada en la zona seleccionada"""
        try:
            zona_seleccionada = self.zona_filter.currentText()
            
            # Limpiar combo de clientes
            self.cliente_filter.clear()
            self.cliente_filter.addItem("Todos los clientes")
            
            if zona_seleccionada != "Todas las zonas":
                # Filtrar clientes por zona
                clientes_zona = set()
                for inst in self.todas_instalaciones:
                    if inst.get('zona') == zona_seleccionada and inst.get('cliente_rol'):
                        clientes_zona.add(inst['cliente_rol'])
                
                # Agregar clientes de la zona
                for cliente in sorted(clientes_zona):
                    self.cliente_filter.addItem(cliente)
            else:
                # Mostrar todos los clientes
                clientes_todos = set()
                for inst in self.todas_instalaciones:
                    if inst.get('cliente_rol'):
                        clientes_todos.add(inst['cliente_rol'])
                
                for cliente in sorted(clientes_todos):
                    self.cliente_filter.addItem(cliente)
            
            # Filtrar instalaciones automáticamente
            self.filtrar_instalaciones()
            
        except Exception as e:
            print(f"Error al actualizar clientes por zona: {e}")
    
    def filtrar_instalaciones(self):
        """Filtrar instalaciones basado en los filtros seleccionados"""
        try:
            zona_seleccionada = self.zona_filter.currentText()
            cliente_seleccionado = self.cliente_filter.currentText()
            
            instalaciones_filtradas = []
            
            for inst in self.todas_instalaciones:
                # Filtrar por zona
                if zona_seleccionada != "Todas las zonas":
                    if inst.get('zona') != zona_seleccionada:
                        continue
                
                # Filtrar por cliente
                if cliente_seleccionado != "Todos los clientes":
                    if inst.get('cliente_rol') != cliente_seleccionado:
                        continue
                
                instalaciones_filtradas.append(inst)
            
            # Mostrar instalaciones filtradas
            self.mostrar_instalaciones_filtradas(instalaciones_filtradas)
            
        except Exception as e:
            print(f"Error al filtrar instalaciones: {e}")
    
    def mostrar_instalaciones_filtradas(self, instalaciones=None):
        """Mostrar instalaciones filtradas en tabla"""
        try:
            # Limpiar tabla actual
            self.instalaciones_table.setRowCount(0)
            self.instalaciones_checks.clear()
            
            if not instalaciones:
                return
            
            # Configurar número de filas
            self.instalaciones_table.setRowCount(len(instalaciones))
            
            # Llenar tabla con datos
            for row, inst in enumerate(instalaciones):
                instalacion_rol = inst['instalacion_rol']
                zona = inst.get('zona', 'Sin zona')
                
                # Columna 0: Nombre de la instalación
                inst_item = QTableWidgetItem(instalacion_rol)
                inst_item.setFont(QFont("Arial", 10, QFont.Bold))
                self.instalaciones_table.setItem(row, 0, inst_item)
                
                # Columna 1: Zona
                zona_item = QTableWidgetItem(zona)
                zona_item.setFont(QFont("Arial", 9))
                zona_item.setForeground(QColor("#666666"))
                self.instalaciones_table.setItem(row, 1, zona_item)
                
                # Columna 2: Checkbox "Puede ver"
                puede_ver_check = QCheckBox()
                puede_ver_check.setStyleSheet("""
                    QCheckBox {
                        spacing: 5px;
                    }
                    QCheckBox::indicator {
                        width: 20px;
                        height: 20px;
                        border: 2px solid #ddd;
                        border-radius: 4px;
                        background-color: white;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #0275AA;
                        border: 2px solid #0275AA;
                        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNSA4TDIgNiIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
                    }
                    QCheckBox::indicator:hover {
                        border: 2px solid #0275AA;
                    }
                """)
                
                # Pre-marcar si está asignada
                if instalacion_rol in self.instalaciones_detalle:
                    puede_ver_check.setChecked(True)
                
                self.instalaciones_table.setCellWidget(row, 2, puede_ver_check)
                
                # Columna 3: Checkbox "Requiere encuesta individual"
                requiere_encuesta_check = QCheckBox()
                requiere_encuesta_check.setStyleSheet("""
                    QCheckBox {
                        spacing: 5px;
                    }
                    QCheckBox::indicator {
                        width: 20px;
                        height: 20px;
                        border: 2px solid #ddd;
                        border-radius: 4px;
                        background-color: white;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #FF9800;
                        border: 2px solid #FF9800;
                        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNSA4TDIgNiIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
                    }
                    QCheckBox::indicator:hover {
                        border: 2px solid #FF9800;
                    }
                """)
                
                # Pre-marcar si requiere encuesta individual
                if instalacion_rol in self.instalaciones_detalle:
                    requiere_encuesta_check.setChecked(
                        self.instalaciones_detalle[instalacion_rol].get('requiere_encuesta_individual', False)
                    )
                
                # Deshabilitar si "Puede ver" no está marcado
                requiere_encuesta_check.setEnabled(puede_ver_check.isChecked())
                
                # Conectar evento para habilitar/deshabilitar
                puede_ver_check.stateChanged.connect(
                    lambda state, req_check=requiere_encuesta_check: 
                    self.toggle_requiere_encuesta(state, req_check)
                )
                
                self.instalaciones_table.setCellWidget(row, 3, requiere_encuesta_check)
                
                # Guardar referencias para acceso posterior
                self.instalaciones_checks[instalacion_rol] = {
                    'puede_ver': puede_ver_check,
                    'requiere_encuesta': requiere_encuesta_check
                }
                
            # Ajustar altura de filas
            self.instalaciones_table.verticalHeader().setDefaultSectionSize(50)
            
        except Exception as e:
            print(f"Error al mostrar instalaciones filtradas: {e}")
    
    def toggle_todas_instalaciones(self):
        """Seleccionar/deseleccionar todas las instalaciones visibles"""
        seleccionar_todas = self.seleccionar_todas_check.isChecked()
        for checks in self.instalaciones_checks.values():
            checks['puede_ver'].setChecked(seleccionar_todas)
            if seleccionar_todas:
                checks['requiere_encuesta'].setEnabled(True)
            else:
                checks['requiere_encuesta'].setEnabled(False)
                checks['requiere_encuesta'].setChecked(False)
    
    
    def toggle_requiere_encuesta(self, state, requiere_encuesta_check):
        """Habilitar/deshabilitar checkbox de requiere encuesta según puede_ver"""
        if state == Qt.CheckState.Checked.value:
            requiere_encuesta_check.setEnabled(True)
        else:
            requiere_encuesta_check.setEnabled(False)
            requiere_encuesta_check.setChecked(False)
    
    def guardar_permisos(self):
        """Guardar permisos del usuario"""
        # Calcular pasos
        total_pasos = 1  # Actualizar ver_todas
        
        # Verificar si hay instalaciones seleccionadas
        hay_instalaciones = False
        if not self.ver_todas_check.isChecked():
            for checks in self.instalaciones_checks.values():
                if checks['puede_ver'].isChecked():
                    hay_instalaciones = True
                    break
        
        if hay_instalaciones:
            total_pasos += 1  # Asignar instalaciones
        
        contacto = self.bigquery_service.get_contacto_por_email(self.usuario['email_login'])
        if contacto:
            total_pasos += 1  # Sincronizar contacto
        
        # Mostrar diálogo de progreso
        progress = ProgressDialog(self, "Actualizando Permisos", total_pasos)
        progress.show()
        QApplication.processEvents()
        
        try:
            paso_actual = 0
            
            # PASO 1: Actualizar ver_todas_instalaciones
            paso_actual += 1
            progress.update_progress(paso_actual, "Actualizando configuración de instalaciones...")
            self.bigquery_service.update_usuario(
                self.usuario['email_login'],
                ver_todas_instalaciones=self.ver_todas_check.isChecked()
            )
            
            # PASO 2: Si no ve todas, guardar instalaciones específicas
            instalaciones_con_cliente = {}
            instalaciones_detalle = {}
            
            if not self.ver_todas_check.isChecked():
                # Obtener instalaciones seleccionadas con su cliente correspondiente y detalle
                for instalacion_rol, checks in self.instalaciones_checks.items():
                    if checks['puede_ver'].isChecked():
                        cliente_rol = self.instalaciones_con_cliente.get(instalacion_rol)
                        if cliente_rol:
                            instalaciones_con_cliente[instalacion_rol] = cliente_rol
                            instalaciones_detalle[instalacion_rol] = {
                                'requiere_encuesta_individual': checks['requiere_encuesta'].isChecked()
                            }
                
                if instalaciones_con_cliente:
                    paso_actual += 1
                    progress.update_progress(paso_actual, f"Asignando {len(instalaciones_con_cliente)} instalaciones...")
                    # Usar método que maneja múltiples clientes con detalle
                    self.bigquery_service.asignar_instalaciones_multi_cliente(
                        self.usuario['email_login'],
                        instalaciones_con_cliente,
                        instalaciones_detalle
                    )
            
            # PASO 3: Si el usuario es contacto, sincronizar instalaciones
            if contacto and instalaciones_con_cliente:
                paso_actual += 1
                progress.update_progress(paso_actual, "Sincronizando instalaciones del contacto...")
                self.bigquery_service.sincronizar_instalaciones_contacto(
                    self.usuario['email_login'],
                    instalaciones_con_cliente
                )
            
            progress.close()
            
            # Mensaje de éxito con información sobre encuestas individuales
            num_requieren_encuesta = sum(1 for checks in self.instalaciones_checks.values() 
                                        if checks['puede_ver'].isChecked() and checks['requiere_encuesta'].isChecked())
            
            mensaje = "Permisos actualizados correctamente"
            if num_requieren_encuesta > 0:
                mensaje += f"\n\n📋 {num_requieren_encuesta} instalación(es) marcadas como 'Requiere encuesta individual'"
            
            QMessageBox.information(self, "Éxito", mensaje)
            self.accept()
            
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Error al guardar permisos: {str(e)}")


class EditarUsuarioDialog(QDialog):
    """Diálogo para editar información de un usuario"""
    
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.bigquery_service = BigQueryService()
        self.firebase_service = FirebaseService()
        self.clientes_disponibles = []
        
        self.setWindowTitle(f"Editar Usuario - {usuario['email_login']}")
        self.setMinimumWidth(600)
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout(self)
        
        # Formulario
        form = QFormLayout()
        
        # Email (solo lectura)
        email_label = QLabel(self.usuario['email_login'])
        email_label.setStyleSheet("font-weight: bold; color: #666;")
        form.addRow("Email:", email_label)
        
        # Nombre completo
        self.nombre_input = QLineEdit()
        self.nombre_input.setText(self.usuario.get('nombre_completo', ''))
        form.addRow("Nombre Completo:", self.nombre_input)
        
        # Cliente actual (solo lectura)
        cliente_actual = self.usuario.get('cliente_rol', 'Sin cliente asignado')
        cliente_label = QLabel(cliente_actual)
        cliente_label.setStyleSheet("font-weight: bold; color: #666; background-color: #f5f5f5; padding: 8px; border-radius: 4px;")
        form.addRow("Cliente actual:", cliente_label)
        
        # Cargo
        self.cargo_input = QLineEdit()
        self.cargo_input.setText(self.usuario.get('cargo', '') or '')
        form.addRow("Cargo:", self.cargo_input)
        
        # Teléfono
        self.telefono_input = QLineEdit()
        self.telefono_input.setText(self.usuario.get('telefono', '') or '')
        form.addRow("Teléfono:", self.telefono_input)
        
        # Rol
        self.rol_combo = QComboBox()
        form.addRow("Rol:", self.rol_combo)
        
        # Checkbox "Es contacto?" (solo para roles != CLIENTE)
        self.es_contacto_check = QCheckBox("Es contacto de WhatsApp")
        self.es_contacto_check.setStyleSheet("color: #0275AA; font-weight: bold;")
        self.es_contacto_check.setToolTip("Marcar si este usuario también debe aparecer como contacto en WhatsApp")
        self.es_contacto_check.setVisible(False)  # Se muestra según el rol
        form.addRow("", self.es_contacto_check)
        
        # Ahora sí conectar el evento y cargar roles
        self.rol_combo.currentIndexChanged.connect(self.on_rol_changed)
        self.cargar_roles()
        
        layout.addLayout(form)
        
        # Botones
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.guardar)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Estilos
        self.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #0275AA;
            }
        """)
    
    
    def cargar_roles(self):
        """Cargar roles disponibles"""
        try:
            self.roles_disponibles = self.bigquery_service.get_roles()
            rol_actual = self.usuario.get('rol_id', 'CLIENTE')
            
            for i, rol in enumerate(self.roles_disponibles):
                self.rol_combo.addItem(rol['nombre_rol'], rol['rol_id'])
                if rol['rol_id'] == rol_actual:
                    self.rol_combo.setCurrentIndex(i)
            
            # Verificar si el usuario ya es contacto
            self.verificar_es_contacto()
            
        except Exception as e:
            print(f"Error al cargar roles: {e}")
            self.rol_combo.addItem("Cliente", "CLIENTE")
    
    def verificar_es_contacto(self):
        """Verificar si el usuario ya existe como contacto"""
        try:
            # Consultar si existe en contactos con este email
            contactos = self.bigquery_service.get_contactos()
            es_contacto = any(c.get('email') == self.usuario['email_login'] for c in contactos)
            
            if es_contacto:
                self.es_contacto_check.setChecked(True)
        except Exception as e:
            print(f"Error al verificar contacto: {e}")
    
    def on_rol_changed(self, index):
        """Mostrar/ocultar checkbox según el rol"""
        rol_id = self.rol_combo.currentData()
        
        if rol_id and rol_id != 'CLIENTE':
            self.es_contacto_check.setVisible(True)
        else:
            self.es_contacto_check.setVisible(False)
            self.es_contacto_check.setChecked(False)
    
    def guardar(self):
        """Guardar cambios"""
        try:
            nombre = self.nombre_input.text().strip()
            cargo = self.cargo_input.text().strip() or None
            telefono = self.telefono_input.text().strip() or None
            rol_id = self.rol_combo.currentData()
            
            if not nombre:
                QMessageBox.warning(self, "Campo requerido", "El nombre completo es obligatorio")
                return
            
            # Obtener estado de contacto
            es_contacto_actual = self.es_contacto_check.isChecked()
            
            # Calcular pasos totales
            total_pasos = 2  # Firebase + BigQuery
            if es_contacto_actual:
                total_pasos += 1  # Sincronizar contacto
            
            # Mostrar diálogo de progreso
            progress = ProgressDialog(self, "Actualizando Usuario", total_pasos)
            progress.show()
            QApplication.processEvents()
            
            try:
                paso_actual = 0
                
                # Actualizar en Firebase
                    paso_actual += 1
                progress.update_progress(paso_actual, "Actualizando en Firebase...")
                
                firebase_result = self.firebase_service.update_user(
                    self.usuario['firebase_uid'],
                    display_name=nombre
                )
                
                if not firebase_result['success']:
                    progress.close()
                    QMessageBox.critical(self, "Error", f"Error en Firebase: {firebase_result['error']}")
                    return
                
                # Actualizar en BigQuery
                paso_actual += 1
                progress.update_progress(paso_actual, "Actualizando en BigQuery...")
                
                bigquery_result = self.bigquery_service.update_usuario(
                    self.usuario['email_login'],
                    nombre_completo=nombre,
                    cargo=cargo,
                    telefono=telefono,
                    rol_id=rol_id
                )
                
                if not bigquery_result['success']:
                    progress.close()
                    QMessageBox.critical(self, "Error", f"Error en BigQuery: {bigquery_result['error']}")
                    return
                
                # Sincronizar contacto si es necesario
                if es_contacto_actual:
                    paso_actual += 1
                    progress.update_progress(paso_actual, "Sincronizando contacto...")
                    
                    # Obtener instalaciones actuales del usuario para sincronizar
                    instalaciones_actuales = self.bigquery_service.get_instalaciones_usuario(
                        self.usuario['email_login']
                    )
                    
                    if instalaciones_actuales:
                        # Crear dict con cliente_rol para cada instalación
                        instalaciones_con_cliente = {}
                        for inst in instalaciones_actuales:
                            # Obtener el cliente_rol de la instalación
                            instalaciones_info = self.bigquery_service.get_instalaciones()
                            for inst_info in instalaciones_info:
                                if inst_info['instalacion_rol'] == inst:
                                    instalaciones_con_cliente[inst] = inst_info['cliente_rol']
                                    break
                        
                        # Sincronizar instalaciones del contacto
                        sync_result = self.bigquery_service.sincronizar_instalaciones_contacto(
                            self.usuario['email_login'],
                            instalaciones_con_cliente
                        )
                        
                        if not sync_result['success']:
                            print(f"Advertencia: No se pudo sincronizar contacto: {sync_result['error']}")
                
                progress.close()
                
                # Mostrar resumen
                mensaje = f"Usuario actualizado correctamente:\n\n"
                mensaje += f"• Nombre: {nombre}\n"
                mensaje += f"• Cargo: {cargo or 'No especificado'}\n"
                mensaje += f"• Teléfono: {telefono or 'No especificado'}\n"
                mensaje += f"• Rol: {rol_id}\n"
                
                if es_contacto_actual:
                    mensaje += f"• Contacto sincronizado: Sí\n"
                
                QMessageBox.information(self, "Éxito", mensaje)
                self.accept()
                
            except Exception as e:
                progress.close()
                QMessageBox.critical(self, "Error", f"Error durante la actualización: {str(e)}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")


class ResetPasswordDialog(QDialog):
    """Diálogo para resetear contraseña de un usuario"""
    
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.firebase_service = FirebaseService()
        
        self.setWindowTitle(f"Resetear Contraseña - {usuario['email_login']}")
        self.setMinimumWidth(400)
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout(self)
        
        # Mensaje informativo
        info_label = QLabel(
            f"Ingresa una nueva contraseña para el usuario:\n"
            f"<b>{self.usuario['email_login']}</b>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #E3F2FD; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Formulario
        form = QFormLayout()
        
        # Nueva contraseña
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Mínimo 6 caracteres")
        form.addRow("Nueva Contraseña:", self.password_input)
        
        # Confirmar contraseña
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Repetir contraseña")
        form.addRow("Confirmar Contraseña:", self.confirm_password_input)
        
        # Checkbox para mostrar contraseña
        self.show_password_check = QCheckBox("Mostrar contraseña")
        self.show_password_check.stateChanged.connect(self.toggle_password_visibility)
        form.addRow("", self.show_password_check)
        
        layout.addLayout(form)
        
        # Advertencia
        warning_label = QLabel(
            "⚠️ El usuario deberá usar esta nueva contraseña para iniciar sesión."
        )
        warning_label.setStyleSheet("color: #FF9800; font-size: 11px; font-style: italic;")
        layout.addWidget(warning_label)
        
        # Botones
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.guardar)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Estilos
        self.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #0275AA;
            }
        """)
    
    def toggle_password_visibility(self, state):
        """Mostrar/ocultar contraseña"""
        if state == Qt.CheckState.Checked.value:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def guardar(self):
        """Resetear contraseña"""
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # Validaciones
        if not password:
            QMessageBox.warning(self, "Campo requerido", "Por favor ingresa una contraseña")
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "Contraseña inválida", "La contraseña debe tener al menos 6 caracteres")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Contraseñas no coinciden", "Las contraseñas ingresadas no coinciden")
            return
        
        # Confirmar acción
        respuesta = QMessageBox.question(
            self,
            "Confirmar cambio",
            f"¿Estás seguro de que quieres cambiar la contraseña de '{self.usuario['email_login']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                resultado = self.firebase_service.reset_password(
                    self.usuario['email_login'],
                    password
                )
                
                if resultado['success']:
                    QMessageBox.information(
                        self,
                        "Éxito",
                        "Contraseña actualizada correctamente.\n\n"
                        "El usuario puede iniciar sesión con la nueva contraseña."
                    )
                    self.accept()
                else:
                    raise Exception(resultado.get('error', 'Error desconocido'))
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo resetear la contraseña:\n{str(e)}")


class AsignarContactosDialog(QDialog):
    """Diálogo para asignar contactos específicos por instalación a un usuario"""
    
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.bigquery_service = BigQueryService()
        self.instalaciones_usuario = []
        self.contactos_por_instalacion = {}
        self.selecciones = {}  # {instalacion_rol: [contacto_ids]}
        
        self.setWindowTitle(f"Asignar Contactos - {usuario['nombre_completo']}")
        self.setMinimumSize(900, 700)
        self.resize(900, 700)
        self.init_ui()
        self.cargar_datos()
    
    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_label = QLabel(
            f"<b>Usuario:</b> {self.usuario['email_login']}<br>"
            f"<b>Cliente:</b> {self.usuario.get('cliente_rol', 'N/A')}"
        )
        header_label.setFixedHeight(60)
        header_label.setStyleSheet("""
            padding: 15px; 
            background-color: #E3F2FD; 
            border-radius: 8px;
            font-size: 14px;
        """)
        layout.addWidget(header_label)
        
        # Instrucciones
        instrucciones = QLabel(
            "Selecciona los contactos que este usuario podrá ver para cada instalación.\n"
            "Solo se muestran las instalaciones que el usuario tiene asignadas."
        )
        instrucciones.setWordWrap(True)
        instrucciones.setFixedHeight(45)
        instrucciones.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        layout.addWidget(instrucciones)
        
        # Tabs por instalación
        self.tabs_instalaciones = QTabWidget()
        self.tabs_instalaciones.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                background-color: white;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: #0275AA;
                color: white;
            }
        """)
        layout.addWidget(self.tabs_instalaciones, 1)
        
        # Botones
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        btn_guardar = QPushButton("Guardar Asignaciones")
        btn_guardar.setFixedHeight(45)
        btn_guardar.setMinimumWidth(200)
        btn_guardar.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #025a8a;
            }}
        """)
        btn_guardar.clicked.connect(self.guardar)
        button_layout.addWidget(btn_guardar)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(45)
        btn_cancelar.setMinimumWidth(150)
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancelar)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def cargar_datos(self):
        """Cargar instalaciones y contactos del usuario"""
        try:
            # Obtener instalaciones del usuario
            self.instalaciones_usuario = self.bigquery_service.get_instalaciones_usuario(
                self.usuario['email_login']
            )
            
            if not self.instalaciones_usuario:
                QMessageBox.warning(
                    self,
                    "Sin instalaciones",
                    "Este usuario no tiene instalaciones asignadas.\n"
                    "Primero asigna instalaciones desde el botón de Permisos."
                )
                self.reject()
                return
            
            # Para cada instalación, obtener contactos disponibles y asignados
            for instalacion_rol in self.instalaciones_usuario:
                # Obtener contactos disponibles para esta instalación
                contactos_disponibles = self.bigquery_service.get_contactos_instalacion(instalacion_rol)
                self.contactos_por_instalacion[instalacion_rol] = contactos_disponibles
                
                # Obtener contactos ya asignados al usuario para esta instalación
                contactos_asignados = self.bigquery_service.get_contactos_usuario(
                    self.usuario['email_login'],
                    instalacion_rol
                )
                self.selecciones[instalacion_rol] = contactos_asignados
                
                # Crear tab para esta instalación
                self.crear_tab_instalacion(instalacion_rol, contactos_disponibles, contactos_asignados)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos:\n{str(e)}")
            self.reject()
    
    def crear_tab_instalacion(self, instalacion_rol, contactos_disponibles, contactos_asignados):
        """Crear un tab para una instalación"""
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setSpacing(10)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        
        # Info
        info_label = QLabel(f"<b>{len(contactos_disponibles)}</b> contactos disponibles para esta instalación")
        info_label.setFixedHeight(30)
        info_label.setStyleSheet("padding: 8px; color: #666; font-size: 13px;")
        tab_layout.addWidget(info_label)
        
        # Botones de selección rápida
        quick_buttons_layout = QHBoxLayout()
        
        btn_seleccionar_todos = QPushButton("✓ Seleccionar Todos")
        btn_seleccionar_todos.setFixedHeight(35)
        btn_seleccionar_todos.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_seleccionar_todos.clicked.connect(
            lambda: self.seleccionar_todos_instalacion(instalacion_rol)
        )
        quick_buttons_layout.addWidget(btn_seleccionar_todos)
        
        btn_deseleccionar_todos = QPushButton("✗ Deseleccionar Todos")
        btn_deseleccionar_todos.setFixedHeight(35)
        btn_deseleccionar_todos.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_deseleccionar_todos.clicked.connect(
            lambda: self.deseleccionar_todos_instalacion(instalacion_rol)
        )
        quick_buttons_layout.addWidget(btn_deseleccionar_todos)
        
        quick_buttons_layout.addStretch()
        tab_layout.addLayout(quick_buttons_layout)
        
        # Lista de contactos con checkboxes
        lista_contactos = QListWidget()
        lista_contactos.setMinimumHeight(400)
        lista_contactos.setStyleSheet("""
            QListWidget {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 8px;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
                min-height: 60px;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        # Agregar contactos con checkbox
        for contacto in contactos_disponibles:
            item_widget = QWidget()
            item_widget.setMinimumHeight(70)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(10, 10, 10, 10)
            item_layout.setSpacing(10)
            
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setFixedSize(20, 20)
            checkbox.setStyleSheet("""
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                }
                QCheckBox::indicator:checked {
                    background-color: #0275AA;
                    border: 2px solid #0275AA;
                }
            """)
            checkbox.setChecked(contacto['contacto_id'] in contactos_asignados)
            checkbox.stateChanged.connect(
                lambda state, inst=instalacion_rol, cid=contacto['contacto_id']: 
                self.toggle_contacto(inst, cid, state)
            )
            item_layout.addWidget(checkbox)
            
            # Información del contacto
            info_layout = QVBoxLayout()
            info_layout.setSpacing(5)
            
            nombre_label = QLabel(f"<b>{contacto['nombre_contacto']}</b>")
            nombre_label.setFixedHeight(20)
            nombre_label.setStyleSheet("font-size: 14px;")
            info_layout.addWidget(nombre_label)
            
            detalles = []
            if contacto.get('telefono'):
                detalles.append(f"📱 {contacto['telefono']}")
            if contacto.get('cargo'):
                detalles.append(f"💼 {contacto['cargo']}")
            if contacto.get('email'):
                detalles.append(f"✉️ {contacto['email']}")
            
            if detalles:
                detalles_label = QLabel(" | ".join(detalles))
                detalles_label.setFixedHeight(20)
                detalles_label.setStyleSheet("color: #666; font-size: 11px;")
                info_layout.addWidget(detalles_label)
            
            item_layout.addLayout(info_layout, 1)
            
            # Crear item de lista
            list_item = QListWidgetItem(lista_contactos)
            list_item.setSizeHint(item_widget.sizeHint())
            lista_contactos.addItem(list_item)
            lista_contactos.setItemWidget(list_item, item_widget)
        
        tab_layout.addWidget(lista_contactos)
        
        # Agregar tab
        self.tabs_instalaciones.addTab(tab_widget, instalacion_rol)
    
    def toggle_contacto(self, instalacion_rol, contacto_id, state):
        """Marcar/desmarcar un contacto"""
        if state == Qt.CheckState.Checked.value:
            if contacto_id not in self.selecciones[instalacion_rol]:
                self.selecciones[instalacion_rol].append(contacto_id)
        else:
            if contacto_id in self.selecciones[instalacion_rol]:
                self.selecciones[instalacion_rol].remove(contacto_id)
    
    def seleccionar_todos_instalacion(self, instalacion_rol):
        """Seleccionar todos los contactos de una instalación"""
        tab_index = self.instalaciones_usuario.index(instalacion_rol)
        tab_widget = self.tabs_instalaciones.widget(tab_index)
        lista_contactos = tab_widget.findChild(QListWidget)
        
        # Marcar todos los checkboxes
        for i in range(lista_contactos.count()):
            item = lista_contactos.item(i)
            item_widget = lista_contactos.itemWidget(item)
            checkbox = item_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)
    
    def deseleccionar_todos_instalacion(self, instalacion_rol):
        """Deseleccionar todos los contactos de una instalación"""
        tab_index = self.instalaciones_usuario.index(instalacion_rol)
        tab_widget = self.tabs_instalaciones.widget(tab_index)
        lista_contactos = tab_widget.findChild(QListWidget)
        
        # Desmarcar todos los checkboxes
        for i in range(lista_contactos.count()):
            item = lista_contactos.item(i)
            item_widget = lista_contactos.itemWidget(item)
            checkbox = item_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)
    
    def guardar(self):
        """Guardar asignaciones de contactos"""
        try:
            total_asignados = 0
            
            # Guardar para cada instalación
            for instalacion_rol, contactos_ids in self.selecciones.items():
                resultado = self.bigquery_service.asignar_contactos_usuario(
                    self.usuario['email_login'],
                    instalacion_rol,
                    contactos_ids,
                    asignado_por="admin"  # Aquí podrías poner el email del admin actual
                )
                
                if not resultado['success']:
                    raise Exception(f"Error en {instalacion_rol}: {resultado.get('error')}")
                
                total_asignados += len(contactos_ids)
            
            QMessageBox.information(
                self,
                "Éxito",
                f"Se asignaron correctamente {total_asignados} contactos en total.\n\n"
                f"El usuario '{self.usuario['email_login']}' ahora puede ver estos contactos en la app."
            )
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar las asignaciones:\n{str(e)}")

