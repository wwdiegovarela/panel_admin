"""
Diálogo de Loading con mensajes de progreso
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMovie
from config.settings import COLOR_PRIMARY


class LoadingDialog(QDialog):
    """Diálogo de carga con mensajes de progreso"""
    
    def __init__(self, parent=None, title="Procesando..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 200)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        self.title_label = QLabel("Procesando...")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLOR_PRIMARY};
        """)
        layout.addWidget(self.title_label)
        
        # Barra de progreso indeterminada
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Modo indeterminado (animación continua)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 5px;
                background-color: #e0e0e0;
            }}
            QProgressBar::chunk {{
                border-radius: 5px;
                background-color: {COLOR_PRIMARY};
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Mensaje de estado
        self.status_label = QLabel("Iniciando...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setFixedHeight(60)
        self.status_label.setStyleSheet("""
            font-size: 13px;
            color: #666;
            padding: 10px;
        """)
        layout.addWidget(self.status_label)
        
        # Estilo general
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 10px;
            }
        """)
    
    def set_message(self, message):
        """Actualizar mensaje de estado"""
        self.status_label.setText(message)
        # Forzar actualización de la UI
        QTimer.singleShot(0, lambda: None)
    
    def set_title(self, title):
        """Actualizar título"""
        self.title_label.setText(title)


class ProgressDialog(QDialog):
    """Diálogo con progreso por pasos"""
    
    def __init__(self, parent=None, title="Procesando", total_steps=5):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(450, 220)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        self.total_steps = total_steps
        self.current_step = 0
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        self.title_label = QLabel("Procesando...")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLOR_PRIMARY};
        """)
        layout.addWidget(self.title_label)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.total_steps)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v de %m pasos completados")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #ddd;
                border-radius: 5px;
                background-color: #f0f0f0;
                text-align: center;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {COLOR_PRIMARY};
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Mensaje de estado actual
        self.status_label = QLabel("Iniciando...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setFixedHeight(60)
        self.status_label.setStyleSheet("""
            font-size: 13px;
            color: #666;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 5px;
        """)
        layout.addWidget(self.status_label)
        
        # Estilo general
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 10px;
            }
        """)
    
    def update_progress(self, step, message):
        """Actualizar progreso y mensaje"""
        self.current_step = step
        self.progress_bar.setValue(step)
        self.status_label.setText(message)
        # Procesar eventos para actualizar UI
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
    
    def set_title(self, title):
        """Actualizar título"""
        self.title_label.setText(title)
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

