"""
Tab de gestión de contactos - Versión refactorizada
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
    QDialog, QFormLayout, QComboBox, QCheckBox, QMessageBox,
    QHeaderView, QListWidget, QListWidgetItem, QDialogButtonBox, QGroupBox,
    QScrollArea, QFrame, QApplication, QFileDialog, QTextEdit
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QColor
from controllers.contactos_controller import ContactosController
from controllers.instalaciones_controller import InstalacionesController
from models.contacto_model import Contacto
from config.settings import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ERROR, COLOR_SECONDARY
from ui.loading_dialog import ProgressDialog
from datetime import datetime


class ContactosTab(QWidget):
    """Tab para gestionar contactos - Versión refactorizada"""
    
    status_message = Signal(str, int)
    
    def __init__(self):
        super().__init__()
        # Inicialización perezosa de controladores
        self._contactos_controller = None
        self._instalaciones_controller = None
        
        self.datos_cargados = False
        self.contacto_inst_count = {}
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz de usuario"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        title = QLabel("Gestión de Contactos")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLOR_PRIMARY};")
        layout.addWidget(title)
        
        # Barra de herramientas
        toolbar = QHBoxLayout()
        
        # Botón nuevo contacto
        self.nuevo_btn = QPushButton("➕ Nuevo Contacto")
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
        self.nuevo_btn.clicked.connect(self.nuevo_contacto)
        toolbar.addWidget(self.nuevo_btn)
        
        # Botón sincronizar
        self.sincronizar_btn = QPushButton("🔄 Sincronizar")
        self.sincronizar_btn.setStyleSheet(f"""
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
        self.sincronizar_btn.clicked.connect(self.sincronizar_contactos)
        toolbar.addWidget(self.sincronizar_btn)
        
        # Campo de búsqueda
        toolbar.addWidget(QLabel("🔍 Buscar:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, teléfono o email...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        self.search_input.textChanged.connect(self.filtrar_contactos)
        toolbar.addWidget(self.search_input)
        
        # Filtro por instalación
        toolbar.addWidget(QLabel("Instalación:"))
        self.instalacion_filter_combo = QComboBox()
        self.instalacion_filter_combo.addItem("Todas las instalaciones")
        self.instalacion_filter_combo.currentTextChanged.connect(self.filtrar_contactos)
        toolbar.addWidget(self.instalacion_filter_combo)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Tabla de contactos (solo lectura)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Teléfono", "Email", "Cargo", "Instalaciones"
        ])
        
        # Configurar tabla
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Nombre
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Teléfono
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Email
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Cargo
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Instalaciones
        
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
            }
        """)
        
        layout.addWidget(self.table)
        
        # Carga diferida al mostrar el tab
        # Se ejecuta en showEvent
    
    def showEvent(self, event):
        """Cargar datos la primera vez que se muestra el tab"""
        super().showEvent(event)
        if not self.datos_cargados:
            self.cargar_contactos()

    @property
    def contactos_controller(self):
        """Obtener controlador de contactos (inicialización perezosa)"""
        if self._contactos_controller is None:
            from controllers.contactos_controller import ContactosController
            self._contactos_controller = ContactosController()
        return self._contactos_controller
    
    @property
    def instalaciones_controller(self):
        """Obtener controlador de instalaciones (inicialización perezosa)"""
        if self._instalaciones_controller is None:
            from controllers.instalaciones_controller import InstalacionesController
            self._instalaciones_controller = InstalacionesController()
        return self._instalaciones_controller
    
    def cargar_contactos(self):
        """Cargar contactos desde el controlador"""
        try:
            # Obtener contactos del controlador
            contactos = self.contactos_controller.get_contactos()
            
            # Cargar filtros
            self.cargar_filtros()
            
            # Asegurar que no haya filtro de texto activo por defecto
            self.search_input.clear()
            
            # Prefetch: obtener todas las relaciones instalación->contactos y calcular conteo por contacto
            try:
                inst_map = self.contactos_controller.get_todos_contactos_por_instalacion() or {}
                counts = {}
                for _inst, lista in inst_map.items():
                    for c in lista:
                        cid = getattr(c, 'contacto_id', None) if hasattr(c, 'contacto_id') else (c.get('contacto_id') if isinstance(c, dict) else None)
                        if cid:
                            counts[cid] = counts.get(cid, 0) + 1
                self.contacto_inst_count = counts
            except Exception:
                self.contacto_inst_count = {}
            
            # Mostrar contactos en la tabla
            self.mostrar_contactos(contactos)
            
            self.datos_cargados = True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar contactos: {str(e)}")
    
    def cargar_filtros(self):
        """Cargar opciones de filtros"""
        try:
            # Cargar instalaciones
            instalaciones = self.instalaciones_controller.get_instalaciones()
            
            self.instalacion_filter_combo.clear()
            self.instalacion_filter_combo.addItem("Todas las instalaciones")
            for instalacion in instalaciones:
                self.instalacion_filter_combo.addItem(instalacion.instalacion_rol)
                
        except Exception as e:
            print(f"Error al cargar filtros: {e}")
    
    def mostrar_contactos(self, contactos):
        """Mostrar contactos en la tabla"""
        self.table.setRowCount(len(contactos))
        
        for row, contacto in enumerate(contactos):
            # ID
            id_item = QTableWidgetItem(contacto.contacto_id)
            self.table.setItem(row, 0, id_item)
            
            # Nombre
            nombre_item = QTableWidgetItem(contacto.nombre_contacto)
            self.table.setItem(row, 1, nombre_item)
            
            # Teléfono
            telefono_item = QTableWidgetItem(contacto.telefono or "Sin teléfono")
            self.table.setItem(row, 2, telefono_item)
            
            # Email
            email_item = QTableWidgetItem(contacto.email or "Sin email")
            self.table.setItem(row, 3, email_item)
            
            # Cargo
            cargo_item = QTableWidgetItem(contacto.cargo or "Sin cargo")
            self.table.setItem(row, 4, cargo_item)
            
            # Instalaciones (contar) usando prefetch
            instalaciones_count = int(self.contacto_inst_count.get(contacto.contacto_id, 0))
            instalaciones_item = QTableWidgetItem(f"🏭 {instalaciones_count}")
            self.table.setItem(row, 5, instalaciones_item)
            
            # Sin acciones (solo lectura)
    
    def filtrar_contactos(self):
        """Filtrar contactos por criterios"""
        try:
            # Obtener todos los contactos
            contactos = self.contactos_controller.get_contactos()
            
            # Filtrar por texto
            texto = self.search_input.text().lower()
            if texto:
                contactos = [cont for cont in contactos if 
                           texto in cont.nombre_contacto.lower() or 
                           (cont.telefono and texto in cont.telefono.lower()) or 
                           (cont.email and texto in cont.email.lower())]
            
            # Filtrar por instalación
            instalacion_seleccionada = self.instalacion_filter_combo.currentText()
            if instalacion_seleccionada != "Todas las instalaciones":
                # TODO: Implementar filtro por instalación
                pass
            
            self.mostrar_contactos(contactos)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al filtrar contactos: {str(e)}")
    
    def nuevo_contacto(self):
        """Crear nuevo contacto"""
        # TODO: Implementar diálogo de nuevo contacto
        QMessageBox.information(self, "Nuevo Contacto", "Funcionalidad en desarrollo")
    
    def editar_contacto(self, contacto):
        """Editar contacto existente"""
        # TODO: Implementar diálogo de edición
        QMessageBox.information(self, "Editar Contacto", f"Editando: {contacto.nombre_contacto}")
    
    def eliminar_contacto(self, contacto):
        """Eliminar contacto"""
        reply = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Estás seguro de eliminar el contacto '{contacto.nombre_contacto}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # TODO: Implementar eliminación
            QMessageBox.information(self, "Eliminar", f"Eliminando: {contacto.nombre_contacto}")
    
    def ver_instalaciones(self, contacto):
        """Ver instalaciones de un contacto"""
        # TODO: Implementar visualizador de instalaciones
        QMessageBox.information(self, "Instalaciones", f"Contacto: {contacto.nombre_contacto}")
    
    def sincronizar_contactos(self):
        """Forzar recarga desde BigQuery ignorando cache"""
        try:
            try:
                from services.bigquery_service import BigQueryService
                BigQueryService().clear_cache()
            except Exception:
                pass
            self.cargar_contactos()
            self.status_message.emit("Contactos sincronizados", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al sincronizar contactos: {str(e)}")
