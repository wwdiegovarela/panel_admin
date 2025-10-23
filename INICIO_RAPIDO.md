# 🚀 INICIO RÁPIDO - Panel Admin WFSA

## ⏱️ 5 MINUTOS PARA EMPEZAR

---

## 📋 PASO 1: INSTALAR DEPENDENCIAS (2 minutos)

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## 🔑 PASO 2: CONFIGURAR CREDENCIALES (1 minuto)

### **Opción A: Variable de entorno (RECOMENDADO)**

1. Descargar archivo JSON de credenciales desde Google Cloud Console
2. Guardar en una ubicación segura (ej: `C:\credenciales\wfsa-credentials.json`)
3. Configurar variable de entorno:

```bash
# Windows (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\credenciales\wfsa-credentials.json"

# Windows (CMD)
set GOOGLE_APPLICATION_CREDENTIALS=C:\credenciales\wfsa-credentials.json
```

### **Opción B: Archivo en el proyecto**

1. Copiar archivo de credenciales a la carpeta del proyecto
2. Renombrar a `credentials.json`
3. Modificar `services/firebase_service.py` y `services/bigquery_service.py` para usar el archivo local

---

## ▶️ PASO 3: EJECUTAR (1 minuto)

```bash
python main.py
```

---

## ✅ VERIFICAR QUE FUNCIONA

1. Se abre la ventana del Panel Admin
2. Click en tab "Usuarios"
3. Deberías ver la lista de usuarios (puede estar vacía si no hay usuarios)
4. Click en "➕ Nuevo Usuario" para crear un usuario de prueba

---

## 🐛 PROBLEMAS COMUNES

### **Error: "No module named 'PySide6'"**
```bash
pip install PySide6
```

### **Error: "Could not find default credentials"**
Asegúrate de configurar la variable de entorno `GOOGLE_APPLICATION_CREDENTIALS`

### **Error: "Permission denied" en BigQuery**
Verifica que las credenciales tengan permisos de:
- `bigquery.dataEditor`
- `bigquery.jobUser`

### **Error: "Firebase Admin SDK not initialized"**
Verifica que las credenciales tengan permisos de Firebase Admin

---

## 📦 COMPILAR A .EXE (OPCIONAL)

```bash
python build.py
```

El archivo .exe se generará en `dist/Panel_Admin_WFSA.exe`

---

## 🎯 PRÓXIMOS PASOS

1. ✅ Crear usuarios de prueba
2. ✅ Asignar permisos a usuarios
3. ✅ Probar login en la app móvil
4. ⏳ Implementar gestión de contactos
5. ⏳ Implementar asignación granular de contactos

---

## 📚 DOCUMENTACIÓN COMPLETA

Ver `README.md` para documentación completa.

---

**¿Listo para empezar?** 🚀

```bash
python main.py
```

