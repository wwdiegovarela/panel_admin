"""
Tab de gestión de instalaciones - Versión refactorizada
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
from controllers.instalaciones_controller import InstalacionesController
from controllers.contactos_controller import ContactosController
from models.instalacion_model import Instalacion
from config.settings import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ERROR, COLOR_SECONDARY
from ui.loading_dialog import ProgressDialog
from datetime import datetime


class InstalacionesTab(QWidget):
    """Tab para gestionar instalaciones - Versión refactorizada"""
    
    status_message = Signal(str, int)
    
    def __init__(self):
        super().__init__()
        # Inicialización perezosa de controladores
        self._instalaciones_controller = None
        self._contactos_controller = None
        
        self.datos_cargados = False
        self.contactos_por_instalacion = {}
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz de usuario"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        title = QLabel("Gestión de Instalaciones")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLOR_PRIMARY};")
        layout.addWidget(title)
        
        # Barra de herramientas
        toolbar = QHBoxLayout()
        
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
        self.sincronizar_btn.clicked.connect(self.sincronizar_instalaciones)
        toolbar.addWidget(self.sincronizar_btn)
        
        # Campo de búsqueda
        toolbar.addWidget(QLabel("🔍 Buscar:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, cliente o zona...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        self.search_input.textChanged.connect(self.filtrar_instalaciones)
        toolbar.addWidget(self.search_input)
        
        # Filtro por cliente
        toolbar.addWidget(QLabel("Cliente:"))
        self.cliente_filter_combo = QComboBox()
        self.cliente_filter_combo.addItem("Todos los clientes")
        self.cliente_filter_combo.currentTextChanged.connect(self.filtrar_instalaciones)
        toolbar.addWidget(self.cliente_filter_combo)
        
        # Filtro por zona
        toolbar.addWidget(QLabel("Zona:"))
        self.zona_filter_combo = QComboBox()
        self.zona_filter_combo.addItem("Todas las zonas")
        self.zona_filter_combo.currentTextChanged.connect(self.filtrar_instalaciones)
        toolbar.addWidget(self.zona_filter_combo)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Tabla de instalaciones
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Instalación", "Cliente", "Zona", "Estado", "Contactos"
        ])
        
        # Configurar tabla
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)          # Instalación
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Cliente
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Zona
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Estado
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Contactos
        
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
            self.cargar_instalaciones()

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
    
    def cargar_instalaciones(self):
        """Cargar instalaciones desde el controlador"""
        try:
            # Obtener instalaciones del controlador
            instalaciones = self.instalaciones_controller.get_instalaciones()
            
            # Prefetch de contactos por instalación (una sola query)
            try:
                self.contactos_por_instalacion = self.contactos_controller.get_todos_contactos_por_instalacion() or {}
            except Exception:
                self.contactos_por_instalacion = {}
            
            # Cargar filtros
            self.cargar_filtros()
            
            # Asegurar que no haya filtro de texto activo por defecto
            self.search_input.clear()
            
            # Mostrar instalaciones en la tabla
            self.mostrar_instalaciones(instalaciones)
            
            self.datos_cargados = True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar instalaciones: {str(e)}")
    
    def cargar_filtros(self):
        """Cargar opciones de filtros"""
        try:
            # Cargar clientes
            instalaciones = self.instalaciones_controller.get_instalaciones()
            clientes = sorted(set(inst.cliente_rol for inst in instalaciones))
            
            self.cliente_filter_combo.clear()
            self.cliente_filter_combo.addItem("Todos los clientes")
            for cliente in clientes:
                self.cliente_filter_combo.addItem(cliente)
            
            # Cargar zonas
            zonas = self.instalaciones_controller.get_zonas()
            self.zona_filter_combo.clear()
            self.zona_filter_combo.addItem("Todas las zonas")
            for zona in zonas:
                self.zona_filter_combo.addItem(zona)
                
        except Exception as e:
            print(f"Error al cargar filtros: {e}")
    
    def mostrar_instalaciones(self, instalaciones):
        """Mostrar instalaciones en la tabla"""
        self.table.setRowCount(len(instalaciones))
        
        for row, instalacion in enumerate(instalaciones):
            # Instalación
            inst_item = QTableWidgetItem(instalacion.instalacion_rol)
            inst_item.setToolTip(instalacion.instalacion_rol)
            self.table.setItem(row, 0, inst_item)
            
            # Cliente
            cliente_item = QTableWidgetItem(instalacion.cliente_rol)
            self.table.setItem(row, 1, cliente_item)
            
            # Zona
            zona_item = QTableWidgetItem(instalacion.zona or "Sin zona")
            self.table.setItem(row, 2, zona_item)
            
            # Estado
            estado_text = "🟢 Activa" if instalacion.activo else "🔴 Inactiva"
            estado_item = QTableWidgetItem(estado_text)
            self.table.setItem(row, 3, estado_item)
            
            # Contactos (contar) usando cache precargado
            contactos_count = len(self.contactos_por_instalacion.get(instalacion.instalacion_rol, []))
            contactos_item = QTableWidgetItem(f"👥 {contactos_count}")
            self.table.setItem(row, 4, contactos_item)
            
            # Sin columna de acciones (vista solo lectura)
    
    def filtrar_instalaciones(self):
        """Filtrar instalaciones por criterios"""
        try:
            # Obtener todos los instalaciones
            instalaciones = self.instalaciones_controller.get_instalaciones()
            
            # Filtrar por texto
            texto = self.search_input.text().lower()
            if texto:
                instalaciones = [inst for inst in instalaciones if 
                               texto in inst.instalacion_rol.lower() or 
                               texto in inst.cliente_rol.lower() or 
                               (inst.zona and texto in inst.zona.lower())]
            
            # Filtrar por cliente
            cliente_seleccionado = self.cliente_filter_combo.currentText()
            if cliente_seleccionado != "Todos los clientes":
                instalaciones = [inst for inst in instalaciones if inst.cliente_rol == cliente_seleccionado]
            
            # Filtrar por zona
            zona_seleccionada = self.zona_filter_combo.currentText()
            if zona_seleccionada != "Todas las zonas":
                instalaciones = [inst for inst in instalaciones if inst.zona == zona_seleccionada]
            
            self.mostrar_instalaciones(instalaciones)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al filtrar instalaciones: {str(e)}")
    
    def nueva_instalacion(self):
        """Crear nueva instalación"""
        # TODO: Implementar diálogo de nueva instalación
        QMessageBox.information(self, "Nueva Instalación", "Funcionalidad en desarrollo")
    
    def editar_instalacion(self, instalacion):
        """Editar instalación existente"""
        # TODO: Implementar diálogo de edición
        QMessageBox.information(self, "Editar Instalación", f"Editando: {instalacion.instalacion_rol}")
    
    def eliminar_instalacion(self, instalacion):
        """Eliminar instalación"""
        reply = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Estás seguro de eliminar la instalación '{instalacion.instalacion_rol}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # TODO: Implementar eliminación
            QMessageBox.information(self, "Eliminar", f"Eliminando: {instalacion.instalacion_rol}")
    
    def ver_contactos(self, instalacion):
        """Ver contactos de una instalación"""
        # TODO: Implementar visualizador de contactos
        contactos = self.contactos_controller.get_contactos_por_instalacion(instalacion.instalacion_rol)
        QMessageBox.information(self, "Contactos", f"Instalación: {instalacion.instalacion_rol}\nContactos: {len(contactos)}")
    
    def sincronizar_instalaciones(self):
        """Forzar recarga desde BigQuery ignorando cache"""
        try:
            try:
                from services.bigquery_service import BigQueryService
                BigQueryService().clear_cache()
            except Exception:
                pass
            self.cargar_instalaciones()
            self.status_message.emit("Instalaciones sincronizadas", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al sincronizar instalaciones: {str(e)}")
