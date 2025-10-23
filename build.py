"""
Script para compilar el Panel Admin a .exe
"""
import os
import sys
import subprocess
from pathlib import Path

# Directorio base
BASE_DIR = Path(__file__).resolve().parent

# Nombre de la aplicación
APP_NAME = "Panel_Admin_WFSA"

# Comando de PyInstaller
cmd = [
    sys.executable,
    "-m", "PyInstaller",
    "--name", APP_NAME,
    "--onefile",                    # Un solo archivo .exe
    "--windowed",                   # SIN consola (interfaz limpia)
    "--clean",                      # Limpiar cache
    "--noconfirm",                  # No pedir confirmación
    
    # Agregar carpetas de datos
    "--add-data", f"config{os.pathsep}config",
    
    # Opciones adicionales
    "--hidden-import", "PySide6",
    "--hidden-import", "firebase_admin",
    "--hidden-import", "google.cloud.bigquery",
    
    # Excluir paquetes innecesarios (reduce tamaño ~400MB)
    "--exclude-module", "pandas",
    "--exclude-module", "numpy",
    "--exclude-module", "scipy",
    "--exclude-module", "matplotlib",
    "--exclude-module", "seaborn",
    "--exclude-module", "statsmodels",
    "--exclude-module", "pyarrow",
    "--exclude-module", "IPython",
    "--exclude-module", "ipykernel",
    "--exclude-module", "jupyter",
    "--exclude-module", "jupyter_client",
    "--exclude-module", "jupyter_core",
    "--exclude-module", "fastapi",
    "--exclude-module", "starlette",
    "--exclude-module", "uvicorn",
    "--exclude-module", "PyPDF2",
    "--exclude-module", "psycopg2",
    "--exclude-module", "patsy",
    "--exclude-module", "_tkinter",
    "--exclude-module", "tkinter",
]

# Agregar icono si existe
icon_path = BASE_DIR / "assets" / "icon.ico"
if icon_path.exists():
    cmd.extend(["--icon", str(icon_path)])
    
# Agregar archivo principal (versión refactorizada)
cmd.append("main_refactored.py")

print("=" * 60)
print(f"Compilando {APP_NAME} a .exe...")
print("=" * 60)
print()
print("Comando:", " ".join(cmd))
print()

try:
    # Ejecutar PyInstaller
    result = subprocess.run(cmd, check=True, cwd=BASE_DIR)
    
    print()
    print("=" * 60)
    print("[EXITO] Compilacion exitosa!")
    print("=" * 60)
    print()
    print(f"Archivo generado: dist/{APP_NAME}.exe")
    print()
    
    # Preparar carpeta de distribución
    dist_folder = BASE_DIR / "dist"
    credenciales_source = BASE_DIR / "worldwide-470917-b0939d44c1ae.json"
    
    # Copiar archivo de credenciales si existe
    if credenciales_source.exists():
        import shutil
        credenciales_dest = dist_folder / "worldwide-470917-b0939d44c1ae.json"
        shutil.copy(credenciales_source, credenciales_dest)
        print("[OK] Archivo de credenciales copiado a dist/")
    else:
        print("[ADVERTENCIA] No se encontro el archivo de credenciales")
        print("              Debes copiar manualmente 'worldwide-470917-b0939d44c1ae.json' a la carpeta dist/")
    
    # Crear archivo README.txt con instrucciones
    readme_content = """
╔══════════════════════════════════════════════════════════╗
║        PANEL DE ADMINISTRACIÓN - WFSA                    ║
║        Gestión de Usuarios, Contactos e Instalaciones    ║
╚══════════════════════════════════════════════════════════╝

📋 INSTRUCCIONES DE USO:

1. Asegúrate de que el archivo de credenciales esté en esta carpeta:
   📁 worldwide-470917-b0939d44c1ae.json

2. Ejecuta el archivo:
   🚀 Panel_Admin_WFSA.exe

3. La aplicación se conectará automáticamente a Firebase y BigQuery

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  IMPORTANTE - SEGURIDAD:

• NO compartir el archivo de credenciales públicamente
• NO subir este archivo a repositorios públicos
• Mantener este archivo en un lugar seguro
• Solo personal autorizado debe tener acceso

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 CONTENIDO DE ESTA CARPETA:

Panel_Admin_WFSA.exe              ← Aplicación principal
worldwide-470917-b0939d44c1ae.json ← Credenciales (REQUERIDO)
README.txt                         ← Este archivo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 FUNCIONALIDADES:

✅ Gestión completa de usuarios
✅ Asignación de permisos por instalación
✅ Creación de usuarios como contactos de WhatsApp
✅ Selección múltiple de clientes
✅ Control granular de instalaciones

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💻 REQUISITOS DEL SISTEMA:

• Windows 10 o superior
• Conexión a Internet (para acceder a Google Cloud)
• 4GB RAM mínimo
• 100MB de espacio en disco

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆘 SOLUCIÓN DE PROBLEMAS:

Problema: "No se encontró el archivo de credenciales"
Solución: Verifica que 'worldwide-470917-b0939d44c1ae.json' 
          esté en la misma carpeta que el .exe

Problema: "Error de conexión a BigQuery"
Solución: Verifica tu conexión a Internet y que las 
          credenciales sean válidas

Problema: "Permission denied"
Solución: Contacta al administrador para verificar permisos
          de la cuenta de servicio en Google Cloud

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 SOPORTE:

Para problemas técnicos o dudas, contacta al equipo de desarrollo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Versión: 1.0.0
Fecha: 2025-10-14
Estado: ✅ Producción

"""
    
    readme_path = dist_folder / "README.txt"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("[OK] Archivo README.txt creado en dist/")
    print()
    print("=" * 60)
    print("[LISTO PARA DISTRIBUIR]")
    print("=" * 60)
    print()
    print("Contenido de la carpeta dist/:")
    print(f"  - {APP_NAME}.exe")
    print(f"  - worldwide-470917-b0939d44c1ae.json")
    print(f"  - README.txt")
    print()
    print("[IMPORTANTE] Recuerda: NO subir el archivo de credenciales a Git!")
    print()
    
except subprocess.CalledProcessError as e:
    print()
    print("=" * 60)
    print("[ERROR] Error en la compilacion")
    print("=" * 60)
    print(f"Error: {e}")
    sys.exit(1)

