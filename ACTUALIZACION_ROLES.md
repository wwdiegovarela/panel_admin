# 🔄 ACTUALIZACIÓN DEL PANEL ADMIN - SISTEMA DE ROLES

## 🎯 OBJETIVO
Actualizar el Panel de Administración para soportar el nuevo sistema de roles implementado en BigQuery.

---

## 📋 CAMBIOS NECESARIOS

### **1. Actualizar `bigquery_service.py`** ✅

Necesitamos agregar métodos para:
- Obtener roles disponibles
- Obtener permisos de un rol
- Actualizar rol de un usuario
- Obtener usuarios con sus roles y permisos

### **2. Actualizar `usuarios_tab.py`** ✅

Necesitamos agregar:
- Columna "Rol" en la tabla de usuarios
- Selector de rol al crear/editar usuarios
- Visualización de permisos del rol seleccionado
- Filtro por rol

### **3. Actualizar diálogos de usuario** ✅

Agregar:
- Selector de rol (ComboBox)
- Visualización de permisos (checkboxes deshabilitados)
- Información del rol seleccionado

---

## 🔧 CAMBIOS DETALLADOS

### **ARCHIVO 1: `services/bigquery_service.py`**

#### **Agregar métodos:**

```python
def get_roles(self):
    """Obtiene todos los roles disponibles"""
    query = f"""
        SELECT 
            rol_id,
            nombre_rol,
            descripcion,
            puede_ver_cobertura,
            puede_ver_encuestas,
            puede_enviar_mensajes,
            puede_ver_empresas,
            puede_ver_metricas_globales,
            puede_ver_trabajadores,
            puede_ver_mensajes_recibidos,
            es_admin,
            activo
        FROM `{self.project_id}.{self.dataset_app}.roles`
        WHERE activo = TRUE
        ORDER BY 
            CASE rol_id
                WHEN 'ADMIN_WFSA' THEN 1
                WHEN 'SUPERVISOR_WFSA' THEN 2
                WHEN 'CONTACTO_WFSA' THEN 3
                WHEN 'CLIENTE' THEN 4
                ELSE 5
            END
    """
    
    query_job = self.client.query(query)
    results = query_job.result()
    
    roles = []
    for row in results:
        roles.append({
            'rol_id': row.rol_id,
            'nombre_rol': row.nombre_rol,
            'descripcion': row.descripcion,
            'permisos': {
                'puede_ver_cobertura': row.puede_ver_cobertura,
                'puede_ver_encuestas': row.puede_ver_encuestas,
                'puede_enviar_mensajes': row.puede_enviar_mensajes,
                'puede_ver_empresas': row.puede_ver_empresas,
                'puede_ver_metricas_globales': row.puede_ver_metricas_globales,
                'puede_ver_trabajadores': row.puede_ver_trabajadores,
                'puede_ver_mensajes_recibidos': row.puede_ver_mensajes_recibidos,
                'es_admin': row.es_admin
            },
            'activo': row.activo
        })
    
    return roles


def get_usuarios_con_roles(self):
    """Obtiene usuarios con sus roles y permisos usando la vista"""
    query = f"""
        SELECT 
            email_login,
            nombre_completo,
            cliente_rol,
            cargo,
            telefono,
            rol_id,
            nombre_rol,
            puede_ver_cobertura,
            puede_ver_encuestas,
            puede_enviar_mensajes,
            puede_ver_empresas,
            puede_ver_metricas_globales,
            puede_ver_trabajadores,
            puede_ver_mensajes_recibidos,
            es_admin,
            ver_todas_instalaciones,
            usuario_activo,
            ultima_sesion,
            fecha_creacion
        FROM `{self.project_id}.{self.dataset_app}.v_permisos_usuarios`
        ORDER BY fecha_creacion DESC
    """
    
    query_job = self.client.query(query)
    results = query_job.result()
    
    usuarios = []
    for row in results:
        usuarios.append({
            'email_login': row.email_login,
            'nombre_completo': row.nombre_completo,
            'cliente_rol': row.cliente_rol,
            'cargo': row.cargo,
            'telefono': row.telefono,
            'rol_id': row.rol_id,
            'nombre_rol': row.nombre_rol,
            'permisos': {
                'puede_ver_cobertura': row.puede_ver_cobertura,
                'puede_ver_encuestas': row.puede_ver_encuestas,
                'puede_enviar_mensajes': row.puede_enviar_mensajes,
                'puede_ver_empresas': row.puede_ver_empresas,
                'puede_ver_metricas_globales': row.puede_ver_metricas_globales,
                'puede_ver_trabajadores': row.puede_ver_trabajadores,
                'puede_ver_mensajes_recibidos': row.puede_ver_mensajes_recibidos,
                'es_admin': row.es_admin
            },
            'ver_todas_instalaciones': row.ver_todas_instalaciones,
            'activo': row.usuario_activo,
            'ultima_sesion': row.ultima_sesion.isoformat() if row.ultima_sesion else None,
            'fecha_creacion': row.fecha_creacion.isoformat() if row.fecha_creacion else None
        })
    
    return usuarios


def actualizar_rol_usuario(self, email_login, nuevo_rol_id):
    """Actualiza el rol de un usuario"""
    query = f"""
        UPDATE `{self.project_id}.{self.dataset_app}.usuarios_app`
        SET rol_id = @nuevo_rol_id
        WHERE email_login = @email_login
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("nuevo_rol_id", "STRING", nuevo_rol_id),
            bigquery.ScalarQueryParameter("email_login", "STRING", email_login)
        ]
    )
    
    query_job = self.client.query(query, job_config=job_config)
    query_job.result()
    
    return True
```

---

### **ARCHIVO 2: `ui/usuarios_tab.py`**

#### **Actualizar tabla para incluir columna "Rol":**

```python
# En init_ui(), cambiar:
self.tabla.setColumnCount(8)  # Era 7, ahora 8
self.tabla.setHorizontalHeaderLabels([
    "Email", "Nombre", "Cliente", "Rol", "Cargo", "Activo", "Ver Todas", "Acciones"
])
```

#### **Actualizar método `mostrar_usuarios`:**

```python
def mostrar_usuarios(self, usuarios):
    """Mostrar usuarios en la tabla"""
    self.tabla.setRowCount(len(usuarios))
    
    for i, usuario in enumerate(usuarios):
        # Email
        self.tabla.setItem(i, 0, QTableWidgetItem(usuario['email_login']))
        
        # Nombre
        self.tabla.setItem(i, 1, QTableWidgetItem(usuario['nombre_completo']))
        
        # Cliente
        self.tabla.setItem(i, 2, QTableWidgetItem(usuario['cliente_rol']))
        
        # Rol ← NUEVO
        rol_item = QTableWidgetItem(usuario.get('nombre_rol', 'Cliente'))
        # Color según el rol
        if usuario.get('rol_id') == 'ADMIN_WFSA':
            rol_item.setBackground(Qt.red)
            rol_item.setForeground(Qt.white)
        elif usuario.get('rol_id') == 'SUPERVISOR_WFSA':
            rol_item.setBackground(Qt.blue)
            rol_item.setForeground(Qt.white)
        elif usuario.get('rol_id') == 'CONTACTO_WFSA':
            rol_item.setBackground(Qt.green)
            rol_item.setForeground(Qt.white)
        self.tabla.setItem(i, 3, rol_item)
        
        # Cargo
        self.tabla.setItem(i, 4, QTableWidgetItem(usuario.get('cargo', '')))
        
        # Activo
        activo_item = QTableWidgetItem("✓" if usuario.get('activo', True) else "✗")
        activo_item.setTextAlignment(Qt.AlignCenter)
        self.tabla.setItem(i, 5, activo_item)
        
        # Ver todas instalaciones
        ver_todas_item = QTableWidgetItem("✓" if usuario.get('ver_todas_instalaciones', False) else "✗")
        ver_todas_item.setTextAlignment(Qt.AlignCenter)
        self.tabla.setItem(i, 6, ver_todas_item)
        
        # Botones de acción
        # ... resto del código
```

#### **Actualizar método `cargar_usuarios`:**

```python
def cargar_usuarios(self):
    """Cargar usuarios desde BigQuery"""
    try:
        self.status_message.emit("Cargando usuarios...", 0)
        # Usar el nuevo método que incluye roles
        usuarios = self.bigquery_service.get_usuarios_con_roles()
        self.usuarios_data = usuarios
        self.mostrar_usuarios(usuarios)
        self.status_message.emit(f"{len(usuarios)} usuarios cargados", 3000)
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Error al cargar usuarios: {str(e)}")
        self.status_message.emit("Error al cargar usuarios", 5000)
```

---

### **ARCHIVO 3: Nuevo diálogo `DialogoUsuario` actualizado**

```python
class DialogoUsuario(QDialog):
    """Diálogo para crear/editar usuario"""
    
    def __init__(self, parent=None, usuario=None, firebase_service=None, bigquery_service=None):
        super().__init__(parent)
        self.usuario = usuario
        self.firebase_service = firebase_service
        self.bigquery_service = bigquery_service
        self.roles_disponibles = []
        self.init_ui()
        
        if usuario:
            self.cargar_datos_usuario()
    
    def init_ui(self):
        """Inicializar interfaz"""
        self.setWindowTitle("Nuevo Usuario" if not self.usuario else "Editar Usuario")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        
        # Formulario
        form_layout = QFormLayout()
        
        # Email
        self.email_input = QLineEdit()
        self.email_input.setEnabled(not self.usuario)  # No editable si es edición
        form_layout.addRow("Email:", self.email_input)
        
        # Contraseña (solo para nuevo usuario)
        if not self.usuario:
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.Password)
            form_layout.addRow("Contraseña:", self.password_input)
        
        # Nombre completo
        self.nombre_input = QLineEdit()
        form_layout.addRow("Nombre Completo:", self.nombre_input)
        
        # Cliente
        self.cliente_input = QLineEdit()
        form_layout.addRow("Cliente ROL:", self.cliente_input)
        
        # Rol ← NUEVO
        self.rol_combo = QComboBox()
        self.cargar_roles()
        self.rol_combo.currentIndexChanged.connect(self.on_rol_changed)
        form_layout.addRow("Rol:", self.rol_combo)
        
        # Descripción del rol ← NUEVO
        self.rol_descripcion = QLabel()
        self.rol_descripcion.setWordWrap(True)
        self.rol_descripcion.setStyleSheet("color: gray; font-style: italic;")
        form_layout.addRow("", self.rol_descripcion)
        
        # Cargo
        self.cargo_input = QLineEdit()
        form_layout.addRow("Cargo:", self.cargo_input)
        
        # Teléfono
        self.telefono_input = QLineEdit()
        form_layout.addRow("Teléfono:", self.telefono_input)
        
        # Ver todas instalaciones
        self.ver_todas_check = QCheckBox("Puede ver todas las instalaciones")
        form_layout.addRow("", self.ver_todas_check)
        
        layout.addLayout(form_layout)
        
        # Grupo de permisos ← NUEVO
        permisos_group = QGroupBox("Permisos del Rol")
        permisos_layout = QVBoxLayout()
        
        self.permisos_checks = {
            'puede_ver_cobertura': QCheckBox("Ver Cobertura"),
            'puede_ver_encuestas': QCheckBox("Ver Encuestas"),
            'puede_enviar_mensajes': QCheckBox("Enviar Mensajes"),
            'puede_ver_empresas': QCheckBox("Ver Empresas"),
            'puede_ver_metricas_globales': QCheckBox("Ver Métricas Globales"),
            'puede_ver_trabajadores': QCheckBox("Ver Trabajadores"),
            'puede_ver_mensajes_recibidos': QCheckBox("Ver Mensajes Recibidos"),
            'es_admin': QCheckBox("Administrador")
        }
        
        for check in self.permisos_checks.values():
            check.setEnabled(False)  # Solo lectura
            permisos_layout.addWidget(check)
        
        permisos_group.setLayout(permisos_layout)
        layout.addWidget(permisos_group)
        
        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
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
    
    def on_rol_changed(self, index):
        """Actualizar permisos cuando cambia el rol"""
        if index < 0 or index >= len(self.roles_disponibles):
            return
        
        rol = self.roles_disponibles[index]
        
        # Actualizar descripción
        self.rol_descripcion.setText(rol.get('descripcion', ''))
        
        # Actualizar checkboxes de permisos
        permisos = rol.get('permisos', {})
        for key, check in self.permisos_checks.items():
            check.setChecked(permisos.get(key, False))
    
    def cargar_datos_usuario(self):
        """Cargar datos del usuario para edición"""
        self.email_input.setText(self.usuario['email_login'])
        self.nombre_input.setText(self.usuario['nombre_completo'])
        self.cliente_input.setText(self.usuario['cliente_rol'])
        self.cargo_input.setText(self.usuario.get('cargo', ''))
        self.telefono_input.setText(self.usuario.get('telefono', ''))
        self.ver_todas_check.setChecked(self.usuario.get('ver_todas_instalaciones', False))
        
        # Seleccionar rol actual
        rol_id = self.usuario.get('rol_id', 'CLIENTE')
        index = self.rol_combo.findData(rol_id)
        if index >= 0:
            self.rol_combo.setCurrentIndex(index)
    
    def get_datos(self):
        """Obtener datos del formulario"""
        datos = {
            'email': self.email_input.text().strip(),
            'nombre_completo': self.nombre_input.text().strip(),
            'cliente_rol': self.cliente_input.text().strip(),
            'rol_id': self.rol_combo.currentData(),
            'cargo': self.cargo_input.text().strip(),
            'telefono': self.telefono_input.text().strip(),
            'ver_todas_instalaciones': self.ver_todas_check.isChecked()
        }
        
        if not self.usuario:
            datos['password'] = self.password_input.text()
        
        return datos
```

---

## 📊 RESUMEN DE CAMBIOS

| Archivo | Cambios | Líneas aprox. |
|---------|---------|---------------|
| `bigquery_service.py` | +3 métodos (get_roles, get_usuarios_con_roles, actualizar_rol_usuario) | +150 |
| `usuarios_tab.py` | Actualizar tabla (+1 columna), actualizar métodos | +50 |
| `DialogoUsuario` | +Selector de rol, +Visualización de permisos | +100 |

---

## ✅ CHECKLIST

- [ ] Actualizar `bigquery_service.py` con nuevos métodos
- [ ] Actualizar `usuarios_tab.py` para mostrar roles
- [ ] Actualizar `DialogoUsuario` con selector de rol
- [ ] Agregar visualización de permisos
- [ ] Agregar filtro por rol (opcional)
- [ ] Testing de creación de usuarios con diferentes roles
- [ ] Testing de edición de rol de usuarios existentes

---

## 🚀 PRÓXIMOS PASOS

1. ✅ Actualizar archivos del Panel Admin
2. ⏳ Probar creación de usuarios con diferentes roles
3. ⏳ Probar edición de roles
4. ⏳ Compilar a .exe
5. ⏳ Distribuir a administradores

---

**¿Quieres que actualice los archivos del Panel Admin con estos cambios?** 🚀

