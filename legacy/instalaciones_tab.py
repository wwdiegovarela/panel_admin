"""
Tab de visualización de instalaciones
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QHeaderView, QMessageBox, QComboBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from config.settings import COLOR_PRIMARY
from services.bigquery_service import BigQueryService


class InstalacionesTab(QWidget):
    """Tab para visualizar instalaciones"""
    
    status_message = Signal(str, int)
    
    def __init__(self):
        super().__init__()
        self.bq_service = BigQueryService()
        self.instalaciones = []
        self.contactos_por_instalacion = {}  # Cache de contactos
        self.datos_cargados = False
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz de usuario"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Título
        title = QLabel("Visualizador de Instalaciones")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_PRIMARY};")
        header_layout.addWidget(title)
        
        # Subtítulo
        subtitle = QLabel("Vista de todas las instalaciones con sus clientes y contactos")
        subtitle.setStyleSheet("color: #666; font-size: 12px; font-style: italic; margin-left: 20px;")
        header_layout.addWidget(subtitle)
        
        header_layout.addStretch()
        
        # Botón Refrescar
        btn_refrescar = QPushButton("🔄 Refrescar")
        btn_refrescar.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        btn_refrescar.clicked.connect(self.cargar_datos)
        header_layout.addWidget(btn_refrescar)
        
        layout.addLayout(header_layout)
        
        # Filtros
        filtros_layout = QHBoxLayout()
        
        # Filtro por Cliente
        cliente_label = QLabel("Cliente:")
        cliente_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        filtros_layout.addWidget(cliente_label)
        
        self.filtro_cliente = QComboBox()
        self.filtro_cliente.setMinimumWidth(200)
        self.filtro_cliente.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 13px;
                background-color: white;
            }
            QComboBox:focus {
                border-color: #0275AA;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.filtro_cliente.currentTextChanged.connect(self.aplicar_filtros)
        filtros_layout.addWidget(self.filtro_cliente)
        
        filtros_layout.addSpacing(20)
        
        # Filtro por Zona (Comuna)
        zona_label = QLabel("Zona:")
        zona_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        filtros_layout.addWidget(zona_label)
        
        self.filtro_zona = QComboBox()
        self.filtro_zona.setMinimumWidth(200)
        self.filtro_zona.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 13px;
                background-color: white;
            }
            QComboBox:focus {
                border-color: #0275AA;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.filtro_zona.currentTextChanged.connect(self.aplicar_filtros)
        filtros_layout.addWidget(self.filtro_zona)
        
        filtros_layout.addStretch()
        
        # Botón limpiar filtros
        btn_limpiar = QPushButton("✗ Limpiar Filtros")
        btn_limpiar.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_limpiar.clicked.connect(self.limpiar_filtros)
        filtros_layout.addWidget(btn_limpiar)
        
        layout.addLayout(filtros_layout)
        
        # Barra de búsqueda
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Buscar:")
        search_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por instalación o dirección...")
        self.search_input.setStyleSheet("""
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
        self.search_input.textChanged.connect(self.aplicar_filtros)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Tabla de instalaciones
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "Instalación", "Cliente", "Zona", "Comuna", "Dirección", "# Contactos", "Contactos"
        ])
        
        # Configurar tabla
        self.tabla.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #0275AA;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: black;
            }
        """)
        
        # Ajustar columnas - Todas ajustables manualmente
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # Todas ajustables
        
        # Establecer anchos iniciales
        self.tabla.setColumnWidth(0, 200)  # Instalación
        self.tabla.setColumnWidth(1, 150)  # Cliente
        self.tabla.setColumnWidth(2, 100)  # Zona
        self.tabla.setColumnWidth(3, 120)  # Comuna
        self.tabla.setColumnWidth(4, 250)  # Dirección
        self.tabla.setColumnWidth(5, 100)  # # Contactos
        self.tabla.setColumnWidth(6, 300)  # Contactos
        
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.tabla)
    
    def showEvent(self, event):
        """Evento cuando se muestra la pestaña - lazy loading"""
        super().showEvent(event)
        if not self.datos_cargados:
            self.cargar_datos()
            self.datos_cargados = True
    
    def cargar_datos(self):
        """Cargar instalaciones desde BigQuery"""
        try:
            self.status_message.emit("Cargando instalaciones...", 0)
            
            # Cargar instalaciones
            self.instalaciones = self.bq_service.get_instalaciones_con_zonas()
            
            # Cargar TODOS los contactos en una sola query (OPTIMIZACIÓN)
            self.status_message.emit("Cargando contactos...", 0)
            self.contactos_por_instalacion = self.bq_service.get_todos_contactos_por_instalacion()
            
            # Cargar opciones de filtros
            self.cargar_filtros()
            
            self.actualizar_tabla()
            self.status_message.emit(f"✅ {len(self.instalaciones)} instalaciones cargadas", 3000)
        except Exception as e:
            self.status_message.emit(f"❌ Error al cargar instalaciones: {str(e)}", 5000)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las instalaciones:\n{str(e)}")
    
    def cargar_filtros(self):
        """Cargar opciones de los filtros"""
        # Bloquear señales temporalmente
        self.filtro_cliente.blockSignals(True)
        self.filtro_zona.blockSignals(True)
        
        # Limpiar filtros
        self.filtro_cliente.clear()
        self.filtro_zona.clear()
        
        # Agregar opción "Todos"
        self.filtro_cliente.addItem("Todos los clientes")
        self.filtro_zona.addItem("Todas las zonas")
        
        # Obtener clientes únicos
        clientes = sorted(set(inst.get('cliente_rol', '') for inst in self.instalaciones if inst.get('cliente_rol')))
        for cliente in clientes:
            self.filtro_cliente.addItem(cliente)
        
        # Obtener zonas únicas (desde la columna zona, no comuna)
        zonas = sorted(set(inst.get('zona', '') for inst in self.instalaciones if inst.get('zona')))
        for zona in zonas:
            self.filtro_zona.addItem(zona)
        
        # Restaurar señales
        self.filtro_cliente.blockSignals(False)
        self.filtro_zona.blockSignals(False)
    
    def actualizar_tabla(self, instalaciones_filtradas=None):
        """Actualizar la tabla con las instalaciones"""
        instalaciones = instalaciones_filtradas if instalaciones_filtradas is not None else self.instalaciones
        
        self.tabla.setRowCount(0)
        
        for inst in instalaciones:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            
            instalacion_rol = inst.get('instalacion_rol', '')
            
            # Instalación
            inst_item = QTableWidgetItem(instalacion_rol)
            inst_item.setFont(QFont("", -1, QFont.Bold))
            self.tabla.setItem(row, 0, inst_item)
            
            # Cliente
            self.tabla.setItem(row, 1, QTableWidgetItem(inst.get('cliente_rol', '')))
            
            # Zona
            zona_item = QTableWidgetItem(inst.get('zona', '') or '-')
            if inst.get('zona'):
                zona_item.setForeground(Qt.GlobalColor.darkBlue)
            self.tabla.setItem(row, 2, zona_item)
            
            # Comuna
            self.tabla.setItem(row, 3, QTableWidgetItem(inst.get('comuna', '') or '-'))
            
            # Dirección
            self.tabla.setItem(row, 4, QTableWidgetItem(inst.get('direccion', '') or '-'))
            
            # Obtener contactos de esta instalación desde el cache
            contactos = self.contactos_por_instalacion.get(instalacion_rol, [])
            
            # # Contactos
            num_contactos_item = QTableWidgetItem(str(len(contactos)))
            num_contactos_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if len(contactos) > 0:
                num_contactos_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                num_contactos_item.setForeground(Qt.GlobalColor.gray)
            self.tabla.setItem(row, 5, num_contactos_item)
            
            # Lista de contactos
            if contactos:
                nombres_contactos = [c.get('nombre_contacto', '') for c in contactos]
                contactos_texto = ", ".join(nombres_contactos[:3])  # Primeros 3
                if len(contactos) > 3:
                    contactos_texto += f" (+{len(contactos) - 3} más)"
                
                contactos_item = QTableWidgetItem(contactos_texto)
                # Tooltip con todos los contactos
                tooltip = "\n".join([
                    f"• {c.get('nombre_contacto', '')} - {c.get('telefono', '')}" 
                    for c in contactos
                ])
                contactos_item.setToolTip(tooltip)
            else:
                contactos_item = QTableWidgetItem("Sin contactos asignados")
                contactos_item.setForeground(Qt.GlobalColor.gray)
            
            self.tabla.setItem(row, 6, contactos_item)
    
    def aplicar_filtros(self):
        """Aplicar todos los filtros activos"""
        instalaciones_filtradas = self.instalaciones
        
        # Filtro por Cliente
        cliente_seleccionado = self.filtro_cliente.currentText()
        if cliente_seleccionado and cliente_seleccionado != "Todos los clientes":
            instalaciones_filtradas = [
                inst for inst in instalaciones_filtradas
                if inst.get('cliente_rol', '') == cliente_seleccionado
            ]
        
        # Filtro por Zona
        zona_seleccionada = self.filtro_zona.currentText()
        if zona_seleccionada and zona_seleccionada != "Todas las zonas":
            instalaciones_filtradas = [
                inst for inst in instalaciones_filtradas
                if inst.get('zona', '') == zona_seleccionada
            ]
        
        # Filtro por texto de búsqueda
        texto_busqueda = self.search_input.text().strip().lower()
        if texto_busqueda:
            instalaciones_filtradas = [
                inst for inst in instalaciones_filtradas
                if texto_busqueda in inst.get('instalacion_rol', '').lower()
                or texto_busqueda in (inst.get('direccion', '') or '').lower()
            ]
        
        # Actualizar contador en barra de estado
        if len(instalaciones_filtradas) != len(self.instalaciones):
            self.status_message.emit(
                f"Mostrando {len(instalaciones_filtradas)} de {len(self.instalaciones)} instalaciones",
                0
            )
        
        self.actualizar_tabla(instalaciones_filtradas)
    
    def limpiar_filtros(self):
        """Limpiar todos los filtros"""
        self.filtro_cliente.setCurrentIndex(0)
        self.filtro_zona.setCurrentIndex(0)
        self.search_input.clear()
        self.status_message.emit(f"✅ {len(self.instalaciones)} instalaciones cargadas", 3000)
        self.actualizar_tabla()

