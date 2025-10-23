"""
Tab de gestión de usuarios - Versión refactorizada
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QToolButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
    QDialog, QFormLayout, QComboBox, QCheckBox, QMessageBox,
    QHeaderView, QListWidget, QListWidgetItem, QDialogButtonBox, QGroupBox, QTabWidget,
    QScrollArea, QFrame, QApplication, QFileDialog, QTextEdit
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QColor
from controllers.usuarios_controller import UsuariosController
from controllers.instalaciones_controller import InstalacionesController
from controllers.contactos_controller import ContactosController
from models.usuario_model import Usuario
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
    """Tab para gestionar usuarios - Versión refactorizada"""
    
    status_message = Signal(str, int)
    
    def __init__(self):
        super().__init__()
        # Inicialización perezosa de controladores
        self._usuarios_controller = None
        self._instalaciones_controller = None
        self._contactos_controller = None
        
        self.datos_cargados = False
        self.init_ui()
    
    def showEvent(self, event):
        """Cargar usuarios la primera vez que se muestra el tab"""
        super().showEvent(event)
        if not self.datos_cargados:
            try:
                self.cargar_usuarios()
            except Exception as e:
                print(f"Error cargando usuarios en showEvent: {e}")
    
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
        
        # Botón nuevo usuario
        self.nuevo_btn = QPushButton("➕ Nuevo Usuario")
        self.nuevo_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SUCCESS};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
        """)
        self.nuevo_btn.clicked.connect(self.nuevo_usuario)
        toolbar.addWidget(self.nuevo_btn)
        
        # Botón carga masiva
        self.carga_masiva_btn = QPushButton("📊 Carga Masiva")
        self.carga_masiva_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SECONDARY};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #5a6268;
            }}
        """)
        self.carga_masiva_btn.clicked.connect(self.carga_masiva_usuarios)
        toolbar.addWidget(self.carga_masiva_btn)
        
        # Campo de búsqueda
        toolbar.addWidget(QLabel("🔍 Buscar:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, email o cliente...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        self.search_input.textChanged.connect(self.filtrar_usuarios)
        toolbar.addWidget(self.search_input)
        
        # Filtro por rol
        toolbar.addWidget(QLabel("Rol:"))
        self.rol_filter_combo = QComboBox()
        self.rol_filter_combo.addItem("Todos los roles")
        self.rol_filter_combo.currentTextChanged.connect(self.filtrar_usuarios)
        toolbar.addWidget(self.rol_filter_combo)
        
        # Botón limpiar cache
        self.limpiar_cache_btn = QPushButton("🗑️ Limpiar Cache")
        self.limpiar_cache_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ERROR};
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #c82333;
            }}
        """)
        self.limpiar_cache_btn.clicked.connect(self.limpiar_cache)
        toolbar.addWidget(self.limpiar_cache_btn)

        # Botón sincronizar (refrescar lista)
        self.sincronizar_btn = QPushButton("🔄 Sincronizar")
        self.sincronizar_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SECONDARY};
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #5a6268;
            }}
        """)
        self.sincronizar_btn.clicked.connect(self.sincronizar_usuarios)
        toolbar.addWidget(self.sincronizar_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Barra de acciones basada en selección
        acciones_bar = QHBoxLayout()
        acciones_bar.setSpacing(8)
        
        self.btn_editar_sel = QToolButton()
        self.btn_editar_sel.setText("Editar")
        self.btn_editar_sel.setToolTip("Editar usuario seleccionado")
        self.btn_editar_sel.setEnabled(False)
        self.btn_editar_sel.clicked.connect(self.accion_editar_seleccionado)
        acciones_bar.addWidget(self.btn_editar_sel)
        
        self.btn_permisos_sel = QToolButton()
        self.btn_permisos_sel.setText("Permisos")
        self.btn_permisos_sel.setToolTip("Editar permisos del usuario seleccionado")
        self.btn_permisos_sel.setEnabled(False)
        self.btn_permisos_sel.clicked.connect(self.accion_permisos_seleccionado)
        acciones_bar.addWidget(self.btn_permisos_sel)
        
        self.btn_contactos_sel = QToolButton()
        self.btn_contactos_sel.setText("Contactos")
        self.btn_contactos_sel.setToolTip("Asignar contactos al usuario seleccionado")
        self.btn_contactos_sel.setEnabled(False)
        self.btn_contactos_sel.clicked.connect(self.accion_contactos_seleccionado)
        acciones_bar.addWidget(self.btn_contactos_sel)
        
        # Estilos bonitos para botones de acción
        self.btn_editar_sel.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLOR_PRIMARY};
                color: white;
                padding: 8px 14px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: #025a8a;
            }}
            QToolButton:disabled {{
                background-color: #b3d4e6; color: #f0f0f0;
            }}
        """)
        self.btn_permisos_sel.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLOR_SECONDARY};
                color: white;
                padding: 8px 14px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: #d45e0a;
            }}
            QToolButton:disabled {{
                background-color: #f7c69e; color: #f0f0f0;
            }}
        """)
        self.btn_contactos_sel.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLOR_SUCCESS};
                color: white;
                padding: 8px 14px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: #45a049;
            }}
            QToolButton:disabled {{
                background-color: #b6e1b6; color: #f0f0f0;
            }}
        """)
        
        # Botón eliminar (rojo)
        self.btn_eliminar_sel = QToolButton()
        self.btn_eliminar_sel.setText("Eliminar")
        self.btn_eliminar_sel.setToolTip("Eliminar usuario seleccionado")
        self.btn_eliminar_sel.setEnabled(False)
        self.btn_eliminar_sel.clicked.connect(self.accion_eliminar_seleccionado)
        self.btn_eliminar_sel.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLOR_ERROR};
                color: white;
                padding: 8px 14px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: #d32f2f;
            }}
            QToolButton:disabled {{
                background-color: #f8bcbc; color: #f0f0f0;
            }}
        """)
        acciones_bar.addWidget(self.btn_eliminar_sel)
        
        acciones_bar.addStretch()
        layout.addLayout(acciones_bar)
        
        # Tabla de usuarios
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Email", "Nombre", "Rol", "Cargo", "Estado", "Última Sesión", "Fecha Creación"
        ])
        # Selección por fila y única
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.update_action_buttons)
        
        # Configurar tabla
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Email
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Nombre
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Rol
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Cargo
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Estado
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Última Sesión
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Fecha Creación
        
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #333333;
            }
        """)
        
        layout.addWidget(self.table)
        
        # No cargar datos iniciales automáticamente
        # Se cargarán cuando el usuario acceda al tab
    
    @property
    def usuarios_controller(self):
        """Obtener controlador de usuarios (inicialización perezosa)"""
        if self._usuarios_controller is None:
            from controllers.usuarios_controller import UsuariosController
            self._usuarios_controller = UsuariosController()
        return self._usuarios_controller
    
    @property
    def instalaciones_controller(self):
        """Obtener controlador de instalaciones (inicialización perezosa)"""
        if self._instalaciones_controller is None:
            from controllers.instalaciones_controller import InstalacionesController
            self._instalaciones_controller = InstalacionesController()
        return self._instalaciones_controller
    
    @property
    def contactos_controller(self):
        """Obtener controlador de contactos (inicialización perezosa)"""
        if self._contactos_controller is None:
            from controllers.contactos_controller import ContactosController
            self._contactos_controller = ContactosController()
        return self._contactos_controller
    
    def cargar_usuarios(self):
        """Cargar usuarios desde el controlador"""
        try:
            # Obtener usuarios del controlador
            usuarios = self.usuarios_controller.get_usuarios()
            
            # Cargar roles para el filtro
            self.cargar_roles_filtro()
            
            # Mostrar usuarios en la tabla
            self.mostrar_usuarios(usuarios)
            
            self.datos_cargados = True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar usuarios: {str(e)}")
    
    def cargar_roles_filtro(self):
        """Cargar roles en el combo de filtro"""
        try:
            roles = self.usuarios_controller.get_roles()
            self.rol_filter_combo.clear()
            self.rol_filter_combo.addItem("Todos los roles")
            
            for rol in roles:
                self.rol_filter_combo.addItem(rol['nombre_rol'])
                
        except Exception as e:
            print(f"Error al cargar roles: {e}")
    
    def mostrar_usuarios(self, usuarios):
        """Mostrar usuarios en la tabla"""
        # Guardar referencia para selección
        self.usuarios_actuales = usuarios
        # Limpiar selección previa
        try:
            self.table.clearSelection()
        except Exception:
            pass
        self.table.setRowCount(len(usuarios))
        
        for row, usuario in enumerate(usuarios):
            # Email
            email_item = QTableWidgetItem(usuario.email_login)
            email_item.setToolTip(usuario.email_login)
            self.table.setItem(row, 0, email_item)
            
            # Nombre completo
            nombre_item = QTableWidgetItem(usuario.nombre_completo or "Sin nombre")
            self.table.setItem(row, 1, nombre_item)
            
            # Rol con color
            rol_item = QTableWidgetItem(usuario.nombre_rol)
            rol_color = self.get_rol_color(usuario.rol_id)
            rol_item.setBackground(QColor(rol_color))
            rol_item.setToolTip(f"Rol: {usuario.nombre_rol}\nID: {usuario.rol_id}")
            self.table.setItem(row, 2, rol_item)
            
            # Cargo
            cargo_item = QTableWidgetItem(usuario.cargo or "-")
            self.table.setItem(row, 3, cargo_item)
            
            # Estado
            estado_text = "🟢 Activo" if usuario.activo else "🔴 Inactivo"
            estado_item = QTableWidgetItem(estado_text)
            self.table.setItem(row, 4, estado_item)
            
            # Última sesión
            ultima_sesion = usuario.ultima_sesion.strftime("%d/%m/%Y %H:%M") if usuario.ultima_sesion else "Nunca"
            ultima_sesion_item = QTableWidgetItem(ultima_sesion)
            self.table.setItem(row, 5, ultima_sesion_item)
            
            # Fecha creación
            fecha_creacion = usuario.fecha_creacion.strftime("%d/%m/%Y") if usuario.fecha_creacion else "N/A"
            fecha_creacion_item = QTableWidgetItem(fecha_creacion)
            self.table.setItem(row, 6, fecha_creacion_item)
            
            # (Columna Acciones eliminada: acciones ahora están en la barra superior)
        
        # Actualizar botones de acciones basados en selección
        self.update_action_buttons()

    def get_selected_usuario(self):
        """Devuelve el usuario actualmente seleccionado o None."""
        selected_indexes = self.table.selectedIndexes()
        if not selected_indexes:
            return None
        row = selected_indexes[0].row()
        if hasattr(self, 'usuarios_actuales') and 0 <= row < len(self.usuarios_actuales):
            return self.usuarios_actuales[row]
        return None

    def update_action_buttons(self):
        """Habilita/deshabilita botones según la selección actual."""
        usuario = self.get_selected_usuario()
        enabled = usuario is not None
        self.btn_editar_sel.setEnabled(enabled)
        self.btn_permisos_sel.setEnabled(enabled)
        # Contactos: solo para CLIENTE
        self.btn_contactos_sel.setEnabled(enabled and getattr(usuario, 'rol_id', None) == 'CLIENTE')
        if hasattr(self, 'btn_eliminar_sel'):
            self.btn_eliminar_sel.setEnabled(enabled)

    # Wrappers de acciones sobre el usuario seleccionado
    def accion_editar_seleccionado(self):
        usuario = self.get_selected_usuario()
        if usuario:
            self.editar_usuario(usuario)

    def accion_permisos_seleccionado(self):
        usuario = self.get_selected_usuario()
        if usuario:
            self.editar_permisos(usuario)

    def accion_contactos_seleccionado(self):
        usuario = self.get_selected_usuario()
        if usuario:
            self.asignar_contactos(usuario)

    def accion_toggle_seleccionado(self):
        usuario = self.get_selected_usuario()
        if usuario:
            self.toggle_usuario(usuario)

    def accion_eliminar_seleccionado(self):
        usuario = self.get_selected_usuario()
        if not usuario:
            return
        confirm = QMessageBox.question(
            self,
            "Eliminar usuario",
            (
                f"¿Eliminar definitivamente a {usuario.email_login}?\n\n"
                "Esto eliminará: Firebase Auth, usuario_instalaciones, usuario_contactos, instalacion_contacto (si aplica), contactos y usuarios_app."
            ),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            result = self.usuarios_controller.delete_usuario(usuario.email_login)
            if result.get('success'):
                self.sincronizar_usuarios()
                QMessageBox.information(self, "Usuario eliminado", f"{usuario.email_login} eliminado correctamente")
            else:
                QMessageBox.warning(self, "Error", result.get('error', 'No se pudo eliminar el usuario'))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al eliminar usuario: {str(e)}")
    def get_rol_color(self, rol_id):
        """Obtener color para rol"""
        colores = {
            'ADMIN_WFSA': COLOR_ADMIN,
            'SUBGERENTE_WFSA': COLOR_SUBGERENTE,
            'JEFE_WFSA': COLOR_JEFE,
            'SUPERVISOR_WFSA': COLOR_SUPERVISOR,
            'GERENTE_WFSA': COLOR_GERENTE,
            'CLIENTE': COLOR_CLIENTE
        }
        return colores.get(rol_id, COLOR_CLIENTE)
    
    def filtrar_usuarios(self, texto=""):
        """Filtrar usuarios por texto y rol"""
        try:
            # Obtener todos los usuarios
            usuarios = self.usuarios_controller.get_usuarios()
            
            # Filtrar por texto
            if texto:
                texto = texto.lower()
                usuarios = [u for u in usuarios if 
                          texto in u.nombre_completo.lower() or 
                          texto in u.email_login.lower() or 
                          texto in u.cliente_rol.lower()]
            
            # Filtrar por rol
            rol_seleccionado = self.rol_filter_combo.currentText()
            if rol_seleccionado != "Todos los roles":
                usuarios = [u for u in usuarios if u.nombre_rol == rol_seleccionado]
            
            self.mostrar_usuarios(usuarios)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al filtrar usuarios: {str(e)}")
    
    def nuevo_usuario(self):
        """Abrir diálogo para crear nuevo usuario"""
        dialog = NuevoUsuarioDialog(self)
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
    
    def toggle_usuario(self, usuario):
        """Activar o desactivar un usuario"""
        try:
            nuevo_estado = not usuario.activo
            result = self.usuarios_controller.toggle_usuario_activo(usuario.email_login, nuevo_estado)
            
            if result['success']:
                estado_text = "activado" if nuevo_estado else "desactivado"
                QMessageBox.information(self, "Éxito", f"Usuario {estado_text} correctamente")
                self.cargar_usuarios()
            else:
                QMessageBox.critical(self, "Error", result.get('error', 'Error desconocido'))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cambiar estado del usuario: {str(e)}")
    
    def limpiar_cache(self):
        """Limpiar cache y recargar usuarios"""
        try:
            # Limpiar cache en servicios y recargar
            try:
                # Limpiar cache en la instancia real usada por el controlador
                self.usuarios_controller.service.bigquery_service.clear_cache()
            except Exception:
                pass
            # Resetear filtros para evitar que oculten resultados
            self.search_input.clear()
            if self.rol_filter_combo.currentIndex() != 0:
                self.rol_filter_combo.setCurrentIndex(0)
            self.cargar_usuarios()
            QMessageBox.information(self, "Cache", "Cache limpiado y datos recargados")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al limpiar cache: {str(e)}")

    def sincronizar_usuarios(self):
        """Forzar recarga desde BigQuery ignorando cache"""
        try:
            try:
                # Limpiar cache en la instancia real usada por el controlador
                self.usuarios_controller.service.bigquery_service.clear_cache()
            except Exception:
                pass
            # Resetear filtros para que la recarga muestre todo
            self.search_input.clear()
            if self.rol_filter_combo.currentIndex() != 0:
                self.rol_filter_combo.setCurrentIndex(0)
            self.cargar_usuarios()
            self.status_message.emit("Lista de usuarios sincronizada", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al sincronizar usuarios: {str(e)}")
    
    def carga_masiva_usuarios(self):
        """Abrir diálogo para carga masiva de usuarios desde Excel"""
        dialog = CargaMasivaDialog(self)
        if dialog.exec() == QDialog.Accepted:
            try:
                from services.bigquery_service import BigQueryService
                BigQueryService().clear_cache()
            except Exception:
                pass
            self.cargar_usuarios()


# Diálogo completo de Nuevo Usuario
class NuevoUsuarioDialog(QDialog):
    """Diálogo completo para crear nuevo usuario"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_tab = parent
        self.setWindowTitle("Nuevo Usuario")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.instalaciones_data = []
        self.roles_data = []
        self.init_ui()
        self.cargar_datos()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Formulario básico
        form_group = QGroupBox("Información del Usuario")
        form_layout = QFormLayout(form_group)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("usuario@empresa.com")
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Nombre completo")
        self.cargo_input = QLineEdit()
        self.cargo_input.setPlaceholderText("Cargo del usuario")
        self.telefono_input = QLineEdit()
        self.telefono_input.setPlaceholderText("+56 9 1234 5678")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Contraseña segura")
        
        # ComboBox para roles
        self.rol_combo = QComboBox()
        self.rol_combo.setPlaceholderText("Seleccionar rol...")

        # Check: Es contacto instalación
        self.es_contacto_check = QCheckBox("Es contacto instalación")
        # Ocultar para rol CLIENTE
        try:
            # En creación, el rol se elige; por defecto ocultamos si rol seleccionado es CLIENTE
            self.rol_combo.currentIndexChanged.connect(lambda _: self._toggle_contacto_visibility())
        except Exception:
            pass
        
        form_layout.addRow("Email *:", self.email_input)
        form_layout.addRow("Nombre completo *:", self.nombre_input)
        form_layout.addRow("Cargo:", self.cargo_input)
        form_layout.addRow("Teléfono:", self.telefono_input)
        form_layout.addRow("Contraseña *:", self.password_input)
        form_layout.addRow("Rol *:", self.rol_combo)
        form_layout.addRow("Contacto:", self.es_contacto_check)
        
        layout.addWidget(form_group)
        
        # Sección de instalaciones
        instalaciones_group = QGroupBox("Selección de Instalaciones")
        instalaciones_layout = QVBoxLayout(instalaciones_group)
        
        # Checkbox para ver todas las instalaciones
        self.ver_todas_check = QCheckBox("Ver todas las instalaciones")
        self.ver_todas_check.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        self.ver_todas_check.toggled.connect(self.toggle_ver_todas)
        instalaciones_layout.addWidget(self.ver_todas_check)
        
        # Filtros
        filtros_layout = QHBoxLayout()
        
        # Filtro por zona
        filtros_layout.addWidget(QLabel("Filtrar por zona:"))
        self.zona_filter = QComboBox()
        self.zona_filter.setPlaceholderText("Todas las zonas")
        self.zona_filter.currentTextChanged.connect(self.filtrar_instalaciones)
        filtros_layout.addWidget(self.zona_filter)
        
        # Filtro por cliente
        filtros_layout.addWidget(QLabel("Filtrar por cliente:"))
        self.cliente_filter = QComboBox()
        self.cliente_filter.setPlaceholderText("Todos los clientes")
        self.cliente_filter.currentTextChanged.connect(self.filtrar_instalaciones)
        filtros_layout.addWidget(self.cliente_filter)
        
        # Botón limpiar filtros
        self.limpiar_filtros_btn = QPushButton("Limpiar Filtros")
        self.limpiar_filtros_btn.clicked.connect(self.limpiar_filtros)
        filtros_layout.addWidget(self.limpiar_filtros_btn)
        
        filtros_layout.addStretch()
        instalaciones_layout.addLayout(filtros_layout)
        
        # Tabla de instalaciones
        self.instalaciones_table = QTableWidget()
        self.instalaciones_table.setMaximumHeight(250)
        self.instalaciones_table.setColumnCount(4)
        self.instalaciones_table.setHorizontalHeaderLabels(["", "Instalación", "Zona", "Cliente"])
        
        # Configurar tabla
        self.instalaciones_table.setAlternatingRowColors(True)
        self.instalaciones_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.instalaciones_table.setSelectionMode(QTableWidget.NoSelection)
        self.instalaciones_table.verticalHeader().setVisible(False)
        
        # Configurar columnas
        header = self.instalaciones_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Instalación
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Zona
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Cliente
        
        self.instalaciones_table.setColumnWidth(0, 30)  # Ancho fijo para checkbox
        
        # Estilo de la tabla
        self.instalaciones_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-right: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        
        instalaciones_layout.addWidget(QLabel("Instalaciones disponibles:"))
        instalaciones_layout.addWidget(self.instalaciones_table)
        
        # Contador de instalaciones seleccionadas
        self.contador_label = QLabel("0 instalaciones seleccionadas")
        self.contador_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        instalaciones_layout.addWidget(self.contador_label)
        
        layout.addWidget(instalaciones_group)
        
        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.crear_usuario)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def cargar_datos(self):
        """Cargar roles e instalaciones desde BigQuery"""
        try:
            # Cargar roles
            if hasattr(self.parent_tab, 'usuarios_controller'):
                self.roles_data = self.parent_tab.usuarios_controller.get_roles()
                self.rol_combo.clear()
                for rol in self.roles_data:
                    self.rol_combo.addItem(rol['nombre_rol'], rol['rol_id'])
                # Ajustar visibilidad del check según rol seleccionado
                self._toggle_contacto_visibility()
            
            # Cargar instalaciones
            if hasattr(self.parent_tab, 'instalaciones_controller'):
                self.instalaciones_data = self.parent_tab.instalaciones_controller.get_instalaciones_con_zonas()
                self.mostrar_instalaciones()
                self.cargar_filtros()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar datos: {str(e)}")

    def _toggle_contacto_visibility(self):
        try:
            rol_id = self.rol_combo.currentData()
            is_cliente = (str(rol_id or '').upper() == 'CLIENTE')
            self.es_contacto_check.setVisible(not is_cliente)
        except Exception:
            pass
    
    def cargar_filtros(self):
        """Cargar opciones para los filtros"""
        # Zonas únicas
        zonas = set()
        clientes = set()
        
        for inst in self.instalaciones_data:
            if hasattr(inst, 'zona') and inst.zona:
                zonas.add(inst.zona)
            if hasattr(inst, 'cliente_rol') and inst.cliente_rol:
                clientes.add(inst.cliente_rol)
        
        self.zona_filter.clear()
        self.zona_filter.addItem("Todas las zonas")
        for zona in sorted(zonas):
            self.zona_filter.addItem(zona)
        
        self.cliente_filter.clear()
        self.cliente_filter.addItem("Todos los clientes")
        for cliente in sorted(clientes):
            self.cliente_filter.addItem(cliente)
    
    def mostrar_instalaciones(self, instalaciones_filtradas=None):
        """Mostrar instalaciones en la tabla"""
        instalaciones = instalaciones_filtradas or self.instalaciones_data
        
        # Configurar número de filas
        self.instalaciones_table.setRowCount(len(instalaciones))
        
        for row, instalacion in enumerate(instalaciones):
            # Checkbox en la primera columna
            checkbox = QCheckBox()
            checkbox.setProperty("instalacion", instalacion)
            checkbox.toggled.connect(self.actualizar_contador)
            self.instalaciones_table.setCellWidget(row, 0, checkbox)
            
            # Instalación
            instalacion_item = QTableWidgetItem(instalacion.instalacion_rol)
            instalacion_item.setToolTip(instalacion.instalacion_rol)
            self.instalaciones_table.setItem(row, 1, instalacion_item)
            
            # Zona
            zona_text = instalacion.zona if hasattr(instalacion, 'zona') and instalacion.zona else "Sin zona"
            zona_item = QTableWidgetItem(zona_text)
            zona_item.setToolTip(zona_text)
            self.instalaciones_table.setItem(row, 2, zona_item)
            
            # Cliente
            cliente_text = instalacion.cliente_rol if hasattr(instalacion, 'cliente_rol') and instalacion.cliente_rol else "Sin cliente"
            cliente_item = QTableWidgetItem(cliente_text)
            cliente_item.setToolTip(cliente_text)
            self.instalaciones_table.setItem(row, 3, cliente_item)
        
        self.actualizar_contador()
    
    def filtrar_instalaciones(self):
        """Filtrar instalaciones por zona y cliente"""
        zona_seleccionada = self.zona_filter.currentText()
        cliente_seleccionado = self.cliente_filter.currentText()
        
        instalaciones_filtradas = []
        
        for inst in self.instalaciones_data:
            # Filtro por zona
            if zona_seleccionada != "Todas las zonas" and zona_seleccionada != "":
                if not (hasattr(inst, 'zona') and inst.zona == zona_seleccionada):
                    continue
            
            # Filtro por cliente
            if cliente_seleccionado != "Todos los clientes" and cliente_seleccionado != "":
                if not (hasattr(inst, 'cliente_rol') and inst.cliente_rol == cliente_seleccionado):
                    continue
            
            instalaciones_filtradas.append(inst)
        
        self.mostrar_instalaciones(instalaciones_filtradas)
    
    def limpiar_filtros(self):
        """Limpiar todos los filtros"""
        self.zona_filter.setCurrentIndex(0)
        self.cliente_filter.setCurrentIndex(0)
        self.mostrar_instalaciones()
    
    def toggle_ver_todas(self, checked):
        """Toggle para ver todas las instalaciones"""
        # Deshabilitar/habilitar la tabla de instalaciones
        self.instalaciones_table.setEnabled(not checked)
        self.zona_filter.setEnabled(not checked)
        self.cliente_filter.setEnabled(not checked)
        self.limpiar_filtros_btn.setEnabled(not checked)
        
        if checked:
            self.contador_label.setText("Verá todas las instalaciones")
        else:
            self.actualizar_contador()
    
    def actualizar_contador(self):
        """Actualizar contador de instalaciones seleccionadas"""
        if self.ver_todas_check.isChecked():
            return
        
        seleccionadas = 0
        for row in range(self.instalaciones_table.rowCount()):
            checkbox = self.instalaciones_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                seleccionadas += 1
        
        self.contador_label.setText(f"{seleccionadas} instalaciones seleccionadas")
    
    def crear_usuario(self):
        """Crear usuario con validaciones"""
        # Validaciones básicas
        if not self.email_input.text().strip():
            QMessageBox.warning(self, "Error", "El email es obligatorio")
            return
        
        if not self.nombre_input.text().strip():
            QMessageBox.warning(self, "Error", "El nombre es obligatorio")
            return
        
        if not self.password_input.text().strip():
            QMessageBox.warning(self, "Error", "La contraseña es obligatoria")
            return
        
        if self.rol_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Error", "Debe seleccionar un rol")
            return
        
        # Validar instalaciones
        if not self.ver_todas_check.isChecked():
            instalaciones_seleccionadas = []
            for row in range(self.instalaciones_table.rowCount()):
                checkbox = self.instalaciones_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    instalaciones_seleccionadas.append(checkbox.property("instalacion"))
            
            if not instalaciones_seleccionadas:
                QMessageBox.warning(self, "Error", "Debe seleccionar al menos una instalación o marcar 'Ver todas las instalaciones'")
                return
        
        # Crear usuario
        try:
            usuario_data = {
                'email_login': self.email_input.text().strip(),
                'nombre_completo': self.nombre_input.text().strip(),
                'cargo': self.cargo_input.text().strip() or None,
                'telefono': self.telefono_input.text().strip() or None,
                'rol_id': self.rol_combo.currentData(),
                'cliente_rol': None,  # Se infiere desde instalaciones seleccionadas si corresponde
                'ver_todas_instalaciones': self.ver_todas_check.isChecked(),
                'activo': True
            }
            password = self.password_input.text().strip()

            # Determinar cliente_rol si hay instalaciones marcadas
            instalaciones_seleccionadas = []
            if not self.ver_todas_check.isChecked():
                for row in range(self.instalaciones_table.rowCount()):
                    checkbox = self.instalaciones_table.cellWidget(row, 0)
                    if checkbox and checkbox.isChecked():
                        inst = checkbox.property("instalacion")
                        instalaciones_seleccionadas.append(inst)
                # Cliente_rol principal: del primer ítem
                if instalaciones_seleccionadas:
                    usuario_data['cliente_rol'] = getattr(instalaciones_seleccionadas[0], 'cliente_rol', None)

            # Crear usuario
            result_create = self.parent_tab.usuarios_controller.create_usuario(usuario_data, password)
            if not result_create.get('success', False):
                QMessageBox.critical(self, "Error", result_create.get('error', 'No se pudo crear el usuario'))
                return

            # Asignar instalaciones si no es "ver todas"
            if not self.ver_todas_check.isChecked() and instalaciones_seleccionadas:
                asignaciones = []
                seen = set()
                for inst in instalaciones_seleccionadas:
                    inst_id = getattr(inst, 'instalacion_rol', None)
                    if not inst_id or inst_id in seen:
                        continue
                    seen.add(inst_id)
                    asignaciones.append({
                        'instalacion_rol': inst_id,
                        'cliente_rol': getattr(inst, 'cliente_rol', None),
                        'puede_ver': True,
                        'requiere_encuesta_individual': False
                    })
                result_perm = self.parent_tab.instalaciones_controller.asignar_instalaciones_usuario(usuario_data['email_login'], asignaciones)
                if not result_perm.get('success', True):
                    QMessageBox.warning(self, "Permisos", result_perm.get('error', 'Error al asignar instalaciones'))

                # Sincronizar como contacto de instalación si corresponde
                if self.es_contacto_check.isChecked():
                    # Asegurar que existe el contacto para este email
                    try:
                        _ = self.parent_tab.contactos_controller.service.ensure_contacto_usuario_app(
                            usuario_data['email_login'], usuario_data['nombre_completo'], usuario_data.get('telefono'), usuario_data.get('cargo')
                        )
                    except Exception:
                        pass
                    mapa_inst_cliente = {a['instalacion_rol']: a['cliente_rol'] for a in asignaciones if a.get('instalacion_rol')}
                    if mapa_inst_cliente:
                        try:
                            res_sync = self.parent_tab.contactos_controller.sincronizar_instalaciones_contacto(usuario_data['email_login'], mapa_inst_cliente)
                            if not res_sync.get('success', True):
                                QMessageBox.warning(self, "Contacto", res_sync.get('error', 'No se pudieron sincronizar contactos'))
                        except Exception as e:
                            QMessageBox.warning(self, "Contacto", f"No se pudieron sincronizar contactos: {e}")

            QMessageBox.information(self, "Éxito", "Usuario creado correctamente")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al crear usuario: {str(e)}")


class EditarUsuarioDialog(QDialog):
    """Diálogo para editar usuario"""
    
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.parent_tab = parent  # Referencia al tab para acceder a controladores
        self.usuario = usuario
        self.roles_data = []
        self.setWindowTitle(f"Editar Usuario - {usuario.email_login}")
        self.setModal(True)
        self.setMinimumSize(560, 520)
        self.init_ui()
        self.cargar_roles()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Datos básicos
        basics_group = QGroupBox("Datos Básicos")
        basics_form = QFormLayout(basics_group)
        
        self.email_input = QLineEdit(self.usuario.email_login)
        self.email_input.setReadOnly(True)
        self.nombre_input = QLineEdit(self.usuario.nombre_completo or "")
        self.cargo_input = QLineEdit(self.usuario.cargo or "")
        self.telefono_input = QLineEdit(self.usuario.telefono or "")
        
        basics_form.addRow("Email:", self.email_input)
        basics_form.addRow("Nombre:", self.nombre_input)
        basics_form.addRow("Cargo:", self.cargo_input)
        basics_form.addRow("Teléfono:", self.telefono_input)
        layout.addWidget(basics_group)
        
        # Rol y estado
        rol_group = QGroupBox("Rol y Estado")
        rol_form = QFormLayout(rol_group)
        
        self.rol_combo = QComboBox()
        self.rol_combo.currentIndexChanged.connect(self.actualizar_resumen_permisos)
        self.activo_check = QCheckBox("Usuario activo")
        self.activo_check.setChecked(bool(self.usuario.activo))

        # Check: Es contacto instalación
        self.es_contacto_check = QCheckBox("Es contacto instalación")
        # Inicial: marcado si ya está en INSTALACION_CONTACTO
        self.was_contacto = False
        try:
            contacto = self.parent_tab.contactos_controller.get_contacto_by_email(self.usuario.email_login)
            if contacto:
                insts = self.parent_tab.contactos_controller.service.get_instalaciones_contacto(contacto.contacto_id)
                if insts:
                    self.es_contacto_check.setChecked(True)
                    self.was_contacto = True
        except Exception:
            pass
        
        rol_form.addRow("Rol:", self.rol_combo)
        rol_form.addRow("Estado:", self.activo_check)
        # Ocultar el check si es CLIENTE
        if (self.usuario.rol_id or '').upper() != 'CLIENTE':
            rol_form.addRow("Contacto:", self.es_contacto_check)
        layout.addWidget(rol_group)
        
        # Resumen permisos del rol
        self.permisos_group = QGroupBox("Permisos del Rol")
        self.permisos_layout = QVBoxLayout(self.permisos_group)
        self.permisos_resumen_label = QLabel("")
        self.permisos_resumen_label.setWordWrap(True)
        self.permisos_layout.addWidget(self.permisos_resumen_label)
        layout.addWidget(self.permisos_group)
        
        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.guardar_usuario)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def cargar_roles(self):
        try:
            self.roles_data = self.parent_tab.usuarios_controller.get_roles()
            self.rol_combo.clear()
            selected_index = 0
            for idx, rol in enumerate(self.roles_data):
                nombre = rol.get('nombre_rol', rol.get('rol_id', ''))
                rol_id = rol.get('rol_id')
                self.rol_combo.addItem(nombre, rol_id)
                # Colorear item según rol
                try:
                    color = self.parent_tab.get_rol_color(rol_id)
                    self.rol_combo.setItemData(idx, QColor(color), Qt.BackgroundRole)
                except Exception:
                    pass
                if self.usuario.rol_id == rol_id:
                    selected_index = idx
            self.rol_combo.setCurrentIndex(selected_index)
            self.actualizar_resumen_permisos()
        except Exception as e:
            QMessageBox.warning(self, "Roles", f"No se pudieron cargar roles: {e}")

    def _build_perm_resumen(self, permisos: dict) -> str:
        verdaderos = [k.replace('_', ' ') for k, v in (permisos or {}).items() if bool(v)]
        if not verdaderos:
            return "Este rol no declara permisos especiales."
        return "Permisos: " + ", ".join(verdaderos)
    
    def guardar_usuario(self):
        try:
            if not self.nombre_input.text().strip():
                QMessageBox.warning(self, "Validación", "El nombre es obligatorio")
                return
            email = self.usuario.email_login
            updates = {
                'nombre_completo': self.nombre_input.text().strip(),
                'cargo': self.cargo_input.text().strip() or None,
                'telefono': self.telefono_input.text().strip() or None,
                'activo': self.activo_check.isChecked(),
            }
            # Actualizar datos básicos
            result_basic = self.parent_tab.usuarios_controller.update_usuario(email, updates)
            if not result_basic.get('success', True):
                QMessageBox.critical(self, "Error", result_basic.get('error', 'Error al actualizar usuario'))
                return
            # Actualizar rol si cambió
            nuevo_rol_id = self.rol_combo.currentData()
            if nuevo_rol_id and nuevo_rol_id != self.usuario.rol_id:
                result_rol = self.parent_tab.usuarios_controller.update_rol_usuario(email, nuevo_rol_id)
                if not result_rol.get('success', True):
                    QMessageBox.critical(self, "Rol", result_rol.get('error', 'Error al actualizar rol'))
                    return

            # Si marcó "Es contacto instalación": sincronizar contactos = instalaciones asignadas
            try:
                if self.es_contacto_check.isChecked():
                    # Asegurar que existe un contacto para este email
                    try:
                        _ = self.parent_tab.contactos_controller.service.ensure_contacto_usuario_app(
                            self.usuario.email_login, self.nombre_input.text().strip(), self.telefono_input.text().strip() or None, self.cargo_input.text().strip() or None
                        )
                    except Exception:
                        pass
                    # Obtener instalaciones actuales del usuario
                    detalle = self.parent_tab.instalaciones_controller.get_instalaciones_usuario_detalle(email) or {}
                    # Necesitamos cliente_rol por instalación; pedir al controller de instalaciones la lista completa y mapear
                    todas = self.parent_tab.instalaciones_controller.get_instalaciones_con_zonas() or []
                    map_inst_cliente = {getattr(i, 'instalacion_rol', None): getattr(i, 'cliente_rol', None) for i in todas}
                    mapa = {inst_id: map_inst_cliente.get(inst_id) for inst_id in detalle.keys() if inst_id}
                    if mapa:
                        res_sync = self.parent_tab.contactos_controller.sincronizar_instalaciones_contacto(email, mapa)
                        if not res_sync.get('success', True):
                            QMessageBox.warning(self, "Contacto", res_sync.get('error', 'No se pudieron sincronizar contactos'))
            except Exception as e:
                QMessageBox.warning(self, "Contacto", f"No se pudieron sincronizar contactos: {e}")
            # Si quitó la condición de contacto, limpiar todas las instalaciones de contacto
            try:
                if not self.es_contacto_check.isChecked() and getattr(self, 'was_contacto', False):
                    clear_res = self.parent_tab.contactos_controller.sincronizar_instalaciones_contacto(email, {})
                    if not clear_res.get('success', True):
                        QMessageBox.warning(self, "Contacto", clear_res.get('error', 'No se pudieron eliminar instalaciones de contacto'))
            except Exception as e:
                QMessageBox.warning(self, "Contacto", f"No se pudieron eliminar instalaciones de contacto: {e}")

            QMessageBox.information(self, "Éxito", "Usuario actualizado correctamente")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar usuario: {e}")

    def actualizar_resumen_permisos(self):
        try:
            idx = self.rol_combo.currentIndex()
            if idx < 0 or idx >= len(self.roles_data):
                self.permisos_resumen_label.setText("")
                return
            permisos = self.roles_data[idx].get('permisos', {})
            self.permisos_resumen_label.setText(self._build_perm_resumen(permisos))
        except Exception:
            pass


class PermisosDialog(QDialog):
    """Diálogo para editar permisos por instalación"""
    
    def __init__(self, usuario, parent):
        super().__init__(parent)
        self.parent_tab = parent
        self.usuario = usuario
        self.setWindowTitle(f"Permisos - {usuario.email_login}")
        self.setModal(True)
        self.setMinimumSize(900, 620)
        self.instalaciones_data = []
        self.asignadas_detalle = {}
        self.init_ui()
        self.cargar_datos()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel(f"Usuario: {self.usuario.email_login}")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)
        
        # Ver todas
        self.ver_todas_check = QCheckBox("Ver todas las instalaciones")
        self.ver_todas_check.setChecked(bool(self.usuario.ver_todas_instalaciones))
        self.ver_todas_check.toggled.connect(self._toggle_ver_todas)
        layout.addWidget(self.ver_todas_check)
        
        # Filtros
        filtros = QHBoxLayout()
        self.zona_filter = QComboBox(); self.zona_filter.addItem("Todas las zonas")
        self.cliente_filter = QComboBox(); self.cliente_filter.addItem("Todos los clientes")
        self.search_input_perm = QLineEdit(); self.search_input_perm.setPlaceholderText("Buscar instalación...")
        for w in (QLabel("Zona:"), self.zona_filter, QLabel("Cliente:"), self.cliente_filter, QLabel("Buscar:"), self.search_input_perm):
            filtros.addWidget(w)
        filtros.addStretch()
        layout.addLayout(filtros)
        
        self.zona_filter.currentTextChanged.connect(self.on_zona_cambiada)
        self.cliente_filter.currentTextChanged.connect(self.aplicar_filtros)
        self.search_input_perm.textChanged.connect(self.aplicar_filtros)
        
        # Tabla de instalaciones
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Ver", "Encuesta", "Instalación", "Zona", "Cliente"])
        header_t = self.table.horizontalHeader()
        header_t.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_t.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_t.setSectionResizeMode(2, QHeaderView.Stretch)
        header_t.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_t.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.guardar_permisos)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def cargar_datos(self):
        try:
            # Cargar instalaciones
            self.instalaciones_data = self.parent_tab.instalaciones_controller.get_instalaciones_con_zonas()
            # Cargar asignaciones actuales con detalle
            self.asignadas_detalle = self.parent_tab.instalaciones_controller.get_instalaciones_usuario_detalle(self.usuario.email_login) or {}
            self._cargar_filtros()
            self._poblar_tabla(self.instalaciones_data)
        except Exception as e:
            QMessageBox.warning(self, "Permisos", f"No se pudieron cargar datos: {e}")
    
    def _cargar_filtros(self):
        zonas, clientes = set(), set()
        for inst in self.instalaciones_data:
            if getattr(inst, 'zona', None):
                zonas.add(inst.zona)
            if getattr(inst, 'cliente_rol', None):
                clientes.add(inst.cliente_rol)
        self.zona_filter.blockSignals(True); self.cliente_filter.blockSignals(True)
        self.zona_filter.clear(); self.zona_filter.addItem("Todas las zonas")
        for z in sorted(zonas): self.zona_filter.addItem(z)
        self.cliente_filter.clear(); self.cliente_filter.addItem("Todos los clientes")
        for c in sorted(clientes): self.cliente_filter.addItem(c)
        self.zona_filter.blockSignals(False); self.cliente_filter.blockSignals(False)
        # Ajustar clientes según zona actual
        self._actualizar_clientes_por_zona()

    def _clientes_para_zona(self, zona_sel: str):
        clientes = set()
        for inst in self.instalaciones_data:
            if zona_sel == "Todas las zonas" or getattr(inst, 'zona', None) == zona_sel:
                c = getattr(inst, 'cliente_rol', None)
                if c:
                    clientes.add(c)
        return sorted(clientes)

    def _actualizar_clientes_por_zona(self):
        zona_sel = self.zona_filter.currentText()
        clientes = self._clientes_para_zona(zona_sel)
        current_cliente = self.cliente_filter.currentText()
        self.cliente_filter.blockSignals(True)
        self.cliente_filter.clear()
        self.cliente_filter.addItem("Todos los clientes")
        for c in clientes:
            self.cliente_filter.addItem(c)
        # Restaurar selección si sigue siendo válida
        if current_cliente and current_cliente != "Todos los clientes" and current_cliente in clientes:
            idx = self.cliente_filter.findText(current_cliente)
            if idx >= 0:
                self.cliente_filter.setCurrentIndex(idx)
        self.cliente_filter.blockSignals(False)

    def on_zona_cambiada(self, _):
        self._actualizar_clientes_por_zona()
        self.aplicar_filtros()
    
    def _poblar_tabla(self, instalaciones):
        self.table.setRowCount(len(instalaciones))
        for row, inst in enumerate(instalaciones):
            inst_id = getattr(inst, 'instalacion_rol', None)
            cliente = getattr(inst, 'cliente_rol', None)
            zona = getattr(inst, 'zona', None)
            detalle = self.asignadas_detalle.get(inst_id, {}) if inst_id else {}
            asignada = bool(detalle)  # si existe en detalle, está asignada
            requiere = bool(detalle.get('requiere_encuesta_individual'))
            
            # Ver
            chk_ver = QCheckBox(); chk_ver.setChecked(asignada)
            # Encuesta
            chk_enc = QCheckBox(); chk_enc.setChecked(requiere); chk_enc.setEnabled(asignada)
            def on_ver_toggled(checked, enc=chk_enc):
                enc.setEnabled(checked)
                if not checked:
                    enc.setChecked(False)
            chk_ver.toggled.connect(on_ver_toggled)
            # Guardar metadata para persistencia
            chk_ver.setProperty('instalacion_rol', inst_id)
            chk_ver.setProperty('cliente_rol', cliente)
            chk_enc.setProperty('instalacion_rol', inst_id)
            
            self.table.setCellWidget(row, 0, chk_ver)
            self.table.setCellWidget(row, 1, chk_enc)
            self.table.setItem(row, 2, QTableWidgetItem(inst_id or ""))
            self.table.setItem(row, 3, QTableWidgetItem(zona or ""))
            self.table.setItem(row, 4, QTableWidgetItem(cliente or ""))
    
    def aplicar_filtros(self):
        zona = self.zona_filter.currentText()
        cliente = self.cliente_filter.currentText()
        q = (self.search_input_perm.text() or "").lower()
        filtradas = []
        for inst in self.instalaciones_data:
            if zona != "Todas las zonas" and getattr(inst, 'zona', None) != zona:
                continue
            if cliente != "Todos los clientes" and getattr(inst, 'cliente_rol', None) != cliente:
                continue
            if q and q not in (getattr(inst, 'instalacion_rol', '') or '').lower():
                continue
            filtradas.append(inst)
        self._poblar_tabla(filtradas)
    
    def _toggle_ver_todas(self, checked: bool):
        self.table.setEnabled(not checked)
        self.zona_filter.setEnabled(not checked)
        self.cliente_filter.setEnabled(not checked)
        self.search_input_perm.setEnabled(not checked)
    
    def guardar_permisos(self):
        try:
            if self.ver_todas_check.isChecked():
                # Marcar ver_todas en usuario y limpiar asignaciones específicas
                asignaciones = []
            else:
                asignaciones = []
                for row in range(self.table.rowCount()):
                    chk_ver = self.table.cellWidget(row, 0)
                    chk_enc = self.table.cellWidget(row, 1)
                    if chk_ver and chk_ver.isChecked():
                        asignaciones.append({
                            'instalacion_rol': chk_ver.property('instalacion_rol'),
                            'cliente_rol': chk_ver.property('cliente_rol'),
                            'puede_ver': True,
                            'requiere_encuesta_individual': bool(chk_enc.isChecked()) if chk_enc else False
                        })
            # Persistir
            result = self.parent_tab.instalaciones_controller.asignar_instalaciones_usuario(self.usuario.email_login, asignaciones)
            if not result.get('success', True):
                QMessageBox.critical(self, "Permisos", result.get('error', 'Error al guardar permisos'))
                return
            # Si el usuario es contacto, sincronizar INSTALACION_CONTACTO con las nuevas instalaciones
            try:
                contacto = self.parent_tab.contactos_controller.get_contacto_by_email(self.usuario.email_login)
                if contacto is not None:
                    mapa = {a['instalacion_rol']: a['cliente_rol'] for a in asignaciones if a.get('instalacion_rol')}
                    sync_res = self.parent_tab.contactos_controller.sincronizar_instalaciones_contacto(self.usuario.email_login, mapa)
                    if not sync_res.get('success', True):
                        QMessageBox.warning(self, "Contacto", sync_res.get('error', 'No se pudieron sincronizar contactos con las nuevas instalaciones'))
            except Exception as e:
                QMessageBox.warning(self, "Contacto", f"No se pudieron sincronizar contactos: {e}")
            QMessageBox.information(self, "Éxito", "Permisos actualizados correctamente")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar permisos: {e}")


class AsignarContactosDialog(QDialog):
    """Diálogo para asignar contactos por instalación (dual list)"""
    
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.parent_tab = parent
        self.usuario = usuario
        self.setWindowTitle(f"Contactos - {usuario.email_login}")
        self.setModal(True)
        self.setMinimumSize(820, 560)
        self.init_ui()
        self.cargar_datos()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Usuario: {self.usuario.email_login}"))
        # Selección de instalación
        inst_layout = QHBoxLayout()
        inst_layout.addWidget(QLabel("Instalación:"))
        self.inst_combo = QComboBox()
        self.inst_combo.currentTextChanged.connect(self.on_inst_changed)
        inst_layout.addWidget(self.inst_combo)
        inst_layout.addStretch()
        layout.addLayout(inst_layout)
        
        # Filtros
        filtros = QHBoxLayout()
        self.search_disp = QLineEdit(); self.search_disp.setPlaceholderText("Buscar disponibles...")
        self.search_asig = QLineEdit(); self.search_asig.setPlaceholderText("Buscar asignados...")
        filtros.addWidget(QLabel("Disponibles:")); filtros.addWidget(self.search_disp)
        filtros.addWidget(QLabel("Asignados:")); filtros.addWidget(self.search_asig)
        layout.addLayout(filtros)
        
        # Listas
        body = QHBoxLayout()
        self.list_disponibles = QListWidget(); self.list_disponibles.setSelectionMode(QListWidget.MultiSelection)
        self.list_asignados = QListWidget(); self.list_asignados.setSelectionMode(QListWidget.MultiSelection)
        
        # Botonera central
        centro = QVBoxLayout()
        btn_add = QPushButton(">")
        btn_add_all = QPushButton(">>")
        btn_rem = QPushButton("<")
        btn_rem_all = QPushButton("<<")
        for b in (btn_add, btn_add_all, btn_rem, btn_rem_all):
            b.setFixedWidth(48)
            centro.addWidget(b)
        centro.addStretch()
        
        body.addWidget(self.list_disponibles)
        body.addLayout(centro)
        body.addWidget(self.list_asignados)
        layout.addLayout(body)
        
        # Acciones asignación
        btn_add.clicked.connect(lambda: self.mover_items(self.list_disponibles, self.list_asignados))
        btn_add_all.clicked.connect(lambda: self.mover_todos(self.list_disponibles, self.list_asignados))
        btn_rem.clicked.connect(lambda: self.mover_items(self.list_asignados, self.list_disponibles))
        btn_rem_all.clicked.connect(lambda: self.mover_todos(self.list_asignados, self.list_disponibles))
        self.search_disp.textChanged.connect(self.filtrar_disponibles)
        self.search_asig.textChanged.connect(self.filtrar_asignados)
        
        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.asignar_contactos)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def cargar_datos(self):
        try:
            instalaciones = self.parent_tab.instalaciones_controller.get_instalaciones_usuario(self.usuario.email_login) or []
            self.inst_combo.blockSignals(True)
            self.inst_combo.clear()
            for inst_id in instalaciones:
                self.inst_combo.addItem(inst_id)
            self.inst_combo.blockSignals(False)
            if self.inst_combo.count() > 0:
                self.on_inst_changed(self.inst_combo.currentText())
        except Exception as e:
            QMessageBox.warning(self, "Contactos", f"No se pudieron cargar contactos: {e}")

    def on_inst_changed(self, inst_id: str):
        try:
            disponibles = self.parent_tab.contactos_controller.get_contactos_por_instalacion(inst_id) or []
            asignados_ids = set(self.parent_tab.contactos_controller.get_contactos_usuario(self.usuario.email_login, inst_id) or [])
            self.list_disponibles.clear(); self.list_asignados.clear()
            for c in disponibles:
                nombre = getattr(c, 'nombre_contacto', None) or c.get('nombre_contacto', '')
                email = getattr(c, 'email', None) or c.get('email', '')
                cid = getattr(c, 'contacto_id', None) or c.get('contacto_id')
                item = QListWidgetItem(f"{nombre} <{email}>")
                item.setData(Qt.UserRole, cid)
                if cid in asignados_ids:
                    self.list_asignados.addItem(item)
                else:
                    self.list_disponibles.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "Contactos", f"No se pudieron cargar contactos para {inst_id}: {e}")
    
    def filtrar_disponibles(self, q: str):
        q = (q or "").lower()
        for i in range(self.list_disponibles.count()):
            it = self.list_disponibles.item(i)
            it.setHidden(q not in it.text().lower())
    
    def filtrar_asignados(self, q: str):
        q = (q or "").lower()
        for i in range(self.list_asignados.count()):
            it = self.list_asignados.item(i)
            it.setHidden(q not in it.text().lower())
    
    def mover_items(self, origen: QListWidget, destino: QListWidget):
        items = origen.selectedItems()
        for it in items:
            origen.takeItem(origen.row(it))
            destino.addItem(it)
    
    def mover_todos(self, origen: QListWidget, destino: QListWidget):
        items = [origen.item(i) for i in range(origen.count())]
        for it in items:
            origen.takeItem(origen.row(it))
            destino.addItem(it)
    
    def asignar_contactos(self):
        try:
            # Solo para clientes (protección adicional)
            if getattr(self.usuario, 'rol_id', None) != 'CLIENTE':
                QMessageBox.warning(self, "Contactos", "Solo disponible para usuarios con rol Cliente")
                return
            inst_id = self.inst_combo.currentText().strip()
            if not inst_id:
                QMessageBox.warning(self, "Contactos", "Selecciona una instalación")
                return
            contactos_ids = []
            for i in range(self.list_asignados.count()):
                it = self.list_asignados.item(i)
                cid = it.data(Qt.UserRole)
                if cid:
                    contactos_ids.append(cid)
            result = self.parent_tab.contactos_controller.asignar_contactos_usuario(self.usuario.email_login, inst_id, contactos_ids)
            if not result.get('success', True):
                QMessageBox.critical(self, "Contactos", result.get('error', 'Error al asignar contactos'))
                return
            QMessageBox.information(self, "Éxito", "Contactos asignados correctamente")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al asignar contactos: {e}")

 
