"""
Tab de gestión de contactos
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QDialog,
    QFormLayout, QDialogButtonBox, QMessageBox, QHeaderView,
    QListWidget, QListWidgetItem, QCheckBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from config.settings import COLOR_PRIMARY, COLOR_SECONDARY
from services.bigquery_service import BigQueryService


class ContactosTab(QWidget):
    """Tab para gestionar contactos"""
    
    status_message = Signal(str, int)
    
    def __init__(self):
        super().__init__()
        self.bq_service = BigQueryService()
        self.contactos = []
        self.instalaciones = []
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
        title = QLabel("Visualizador de Contactos")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_PRIMARY};")
        header_layout.addWidget(title)
        
        # Subtítulo
        subtitle = QLabel("Todos los contactos se gestionan desde la pestaña de Usuarios")
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
        
        # Barra de búsqueda
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Buscar:")
        search_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, teléfono, cargo o email...")
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
        self.search_input.textChanged.connect(self.filtrar_contactos)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Tabla de contactos
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "Nombre", "Teléfono", "Cargo", "Email", "Es Usuario App", "Email Usuario", "Instalaciones"
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
        
        # Ajustar columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Nombre
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Teléfono
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Cargo
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Email
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Es Usuario App
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Email Usuario
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Instalaciones
        
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
        """Cargar contactos desde BigQuery"""
        try:
            self.status_message.emit("Cargando contactos...", 0)
            self.contactos = self.bq_service.get_contactos()
            self.instalaciones = self.bq_service.get_instalaciones()
            self.actualizar_tabla()
            self.status_message.emit(f"✅ {len(self.contactos)} contactos cargados", 3000)
        except Exception as e:
            self.status_message.emit(f"❌ Error al cargar contactos: {str(e)}", 5000)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los contactos:\n{str(e)}")
    
    def actualizar_tabla(self, contactos_filtrados=None):
        """Actualizar la tabla con los contactos"""
        contactos = contactos_filtrados if contactos_filtrados is not None else self.contactos
        
        self.tabla.setRowCount(0)
        
        for contacto in contactos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            
            # Nombre
            nombre_item = QTableWidgetItem(contacto.get('nombre_contacto', ''))
            # Si es usuario app, ponerlo en negrita
            if contacto.get('es_usuario_app', False):
                font = nombre_item.font()
                font.setBold(True)
                nombre_item.setFont(font)
                nombre_item.setForeground(Qt.GlobalColor.blue)
            self.tabla.setItem(row, 0, nombre_item)
            
            # Teléfono
            self.tabla.setItem(row, 1, QTableWidgetItem(contacto.get('telefono', '')))
            
            # Cargo
            self.tabla.setItem(row, 2, QTableWidgetItem(contacto.get('cargo', '') or '-'))
            
            # Email
            self.tabla.setItem(row, 3, QTableWidgetItem(contacto.get('email', '') or '-'))
            
            # Es Usuario App
            es_usuario = "✓ Sí" if contacto.get('es_usuario_app', False) else "✗ No"
            es_usuario_item = QTableWidgetItem(es_usuario)
            es_usuario_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if contacto.get('es_usuario_app', False):
                es_usuario_item.setForeground(Qt.GlobalColor.darkGreen)
            self.tabla.setItem(row, 4, es_usuario_item)
            
            # Email Usuario App
            email_usuario = contacto.get('email_usuario_app', '') or '-'
            self.tabla.setItem(row, 5, QTableWidgetItem(email_usuario))
            
            # Instalaciones asignadas
            contacto_id = contacto.get('contacto_id')
            instalaciones_asignadas = self.bq_service.get_instalaciones_contacto(contacto_id)
            if instalaciones_asignadas:
                item_inst = QTableWidgetItem(f"{len(instalaciones_asignadas)}")
                item_inst.setToolTip("\n".join(instalaciones_asignadas))
            else:
                item_inst = QTableWidgetItem("0")
            item_inst.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(row, 6, item_inst)
    
    def filtrar_contactos(self, texto):
        """Filtrar contactos por texto de búsqueda"""
        texto = texto.lower()
        if not texto:
            self.actualizar_tabla()
            return
        
        contactos_filtrados = [
            c for c in self.contactos
            if texto in c.get('nombre_contacto', '').lower()
            or texto in c.get('telefono', '').lower()
            or texto in (c.get('cargo', '') or '').lower()
            or texto in (c.get('email', '') or '').lower()
            or texto in c.get('cliente_rol', '').lower()
        ]
        
        self.actualizar_tabla(contactos_filtrados)
