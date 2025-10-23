# 🎯 Panel de Administración - WFSA

Panel de escritorio para gestionar usuarios, contactos e instalaciones de la app WFSA.

---

## 📦 Características

- ✅ Gestión de usuarios (crear, editar, permisos)
- ✅ Integración con Firebase Authentication
- ✅ Integración con BigQuery
- ✅ Control granular de permisos por instalación
- ✅ Asignación de contactos por usuario
- ✅ UI moderna con PySide6
- ✅ Compilable a .exe

---

## 🚀 Instalación

### **1. Crear entorno virtual:**

```bash
cd Panel_Admin
python -m venv venv
```

### **2. Activar entorno virtual:**

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### **3. Instalar dependencias:**

```bash
pip install -r requirements.txt
```

### **4. Configurar credenciales de Google Cloud:**

1. Descargar archivo JSON de credenciales desde Google Cloud Console
2. Configurar variable de entorno:

**Windows:**
```bash
set GOOGLE_APPLICATION_CREDENTIALS=C:\ruta\al\archivo\credenciales.json
```

**Linux/Mac:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/ruta/al/archivo/credenciales.json
```

---

## ▶️ Ejecutar la aplicación

```bash
python main.py
```

---

## 📦 Compilar a .EXE

### **1. Instalar PyInstaller (ya incluido en requirements.txt):**

```bash
pip install pyinstaller
```

### **2. Compilar:**

```bash
pyinstaller --name="Panel_Admin_WFSA" ^
            --onefile ^
            --windowed ^
            --icon=assets/icon.ico ^
            --add-data="config;config" ^
            main.py
```

El archivo .exe se generará en la carpeta `dist/`

---

## 📁 Estructura del Proyecto

```
Panel_Admin/
├── main.py                 # Punto de entrada
├── requirements.txt        # Dependencias
├── README.md              # Este archivo
│
├── config/                # Configuración
│   ├── __init__.py
│   └── settings.py        # Variables de configuración
│
├── services/              # Servicios
│   ├── __init__.py
│   ├── firebase_service.py    # Firebase Admin SDK
│   └── bigquery_service.py    # BigQuery Client
│
├── ui/                    # Interfaz de usuario
│   ├── __init__.py
│   ├── main_window.py     # Ventana principal
│   ├── usuarios_tab.py    # Tab de usuarios
│   ├── contactos_tab.py   # Tab de contactos
│   └── instalaciones_tab.py # Tab de instalaciones
│
└── assets/                # Recursos (iconos, imágenes)
```

---

## 🎨 Funcionalidades

### **Tab de Usuarios:**
- ✅ Listar todos los usuarios
- ✅ Buscar usuarios por email o nombre
- ✅ Crear nuevo usuario (Firebase + BigQuery)
- ✅ Editar permisos de usuario
- ✅ Asignar instalaciones permitidas
- ✅ Toggle "Ver todas las instalaciones"
- ⏳ Asignar contactos específicos por instalación (próximamente)

### **Tab de Contactos:**
- ⏳ Listar contactos
- ⏳ Crear nuevo contacto
- ⏳ Editar contacto
- ⏳ Asignar a instalaciones

### **Tab de Instalaciones:**
- ⏳ Listar instalaciones
- ⏳ Ver metadata
- ⏳ Editar información

---

## 🔧 Configuración

Edita `config/settings.py` para cambiar:

- Colores del tema
- Tamaño de ventana
- IDs de proyecto y dataset de BigQuery
- Nombres de tablas

---

## 🐛 Troubleshooting

### **Error: "No module named 'PySide6'"**
```bash
pip install PySide6
```

### **Error: "Could not find default credentials"**
Configura la variable de entorno `GOOGLE_APPLICATION_CREDENTIALS`

### **Error al crear usuario en Firebase**
Verifica que el archivo de credenciales tenga permisos de Firebase Admin

---

## 📚 Dependencias Principales

- **PySide6** - Framework de UI (Qt6 para Python)
- **firebase-admin** - SDK de Firebase Admin
- **google-cloud-bigquery** - Cliente de BigQuery
- **pyinstaller** - Para compilar a .exe

---

## 🎯 Próximas Funcionalidades

- [ ] Asignación granular de contactos por usuario/instalación
- [ ] Gestión completa de contactos
- [ ] Gestión de instalaciones
- [ ] Tab de logs y auditoría
- [ ] Exportar datos a Excel
- [ ] Importar usuarios desde CSV
- [ ] Dashboard con estadísticas
- [ ] Notificaciones en tiempo real

---

## 📞 Soporte

Para problemas o sugerencias, contacta al equipo de desarrollo.

---

**Versión:** 1.0.0  
**Fecha:** 2025-10-09  
**Estado:** ✅ Funcional (usuarios básicos)

