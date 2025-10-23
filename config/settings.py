"""
Configuración del Panel Admin - WFSA
"""
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

"""Carga de variables de entorno (.env) compatible con ejecución congelada (PyInstaller)."""
# Buscar .env en:
# 1) Directorio del ejecutable (cuando está congelado)
# 2) Directorio actual de trabajo
# 3) BASE_DIR del proyecto
search_paths = []
try:
    import sys as _sys
    if getattr(_sys, 'frozen', False):  # PyInstaller
        exe_dir = Path(_sys.executable).resolve().parent
        search_paths.append(exe_dir / ".env")
except Exception:
    pass
search_paths.append(Path(os.getcwd()) / ".env")
search_paths.append(BASE_DIR / ".env")

env_path = None
for p in search_paths:
    try:
        if p.exists():
            env_path = p
            break
    except Exception:
        continue

if env_path:
    if load_dotenv:
        try:
            load_dotenv(env_path, override=True)
        except Exception:
            pass
    # Fallback manual si python-dotenv no está disponible o no cargó
    if not os.environ.get("FIREBASE_API_KEY"):
        try:
            with open(env_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.lstrip('\ufeff').strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.lstrip('\ufeff').strip()
                    val = val.lstrip('\ufeff').strip().strip('"').strip("'")
                    if key and val and key not in os.environ:
                        os.environ[key] = val
        except Exception:
            pass

 

# BigQuery
PROJECT_ID = "worldwide-470917"
DATASET_REPORTES = "cr_reportes"
DATASET_APP = "app_clientes"

# Firebase (usar variable de entorno; fallback dummy para dev)
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "AIzaSyBvQZvQZvQZvQZvQZvQZvQZvQZvQZvQZvQ")

# Tablas
TABLE_USUARIOS = f"{PROJECT_ID}.{DATASET_APP}.usuarios_app"
TABLE_USUARIO_INST = f"{PROJECT_ID}.{DATASET_APP}.usuario_instalaciones"
TABLE_CONTACTOS = f"{PROJECT_ID}.{DATASET_APP}.contactos"
TABLE_INST_CONTACTO = f"{PROJECT_ID}.{DATASET_APP}.instalacion_contacto"
TABLE_USUARIO_CONTACTOS = f"{PROJECT_ID}.{DATASET_APP}.usuario_contactos"
TABLE_INSTALACIONES = f"{PROJECT_ID}.{DATASET_REPORTES}.cr_info_instalaciones"
TABLE_ZONAS_INSTALACIONES = f"{PROJECT_ID}.mantenedores.zonas_instalaciones"
TABLE_MENSAJES = f"{PROJECT_ID}.{DATASET_APP}.mensajes_whatsapp"
TABLE_AUDITORIA = f"{PROJECT_ID}.{DATASET_APP}.auditoria"
TABLE_ROLES = f"{PROJECT_ID}.{DATASET_APP}.roles"

# Colores del tema WFSA
COLOR_PRIMARY = "#0275AA"  # Azul WFSA
COLOR_SECONDARY = "#F56F10"  # Naranja WFSA
COLOR_SUCCESS = "#4CAF50"
COLOR_WARNING = "#FF9800"
COLOR_ERROR = "#F44336"
COLOR_BACKGROUND = "#FFFFFF"
COLOR_TEXT = "#333333"

# Configuración de la aplicación
APP_NAME = "Panel Admin - WFSA"
APP_VERSION = "2.0.0"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

# Colores para roles (consistentes con la app móvil)
COLOR_ADMIN = "#9C27B0"        # Púrpura para ADMIN_WFSA
COLOR_SUBGERENTE = "#FF5722"   # Naranja profundo para SUBGERENTE_WFSA
COLOR_JEFE = "#F44336"          # Rojo para JEFE_WFSA
COLOR_SUPERVISOR = "#FBC02D"    # Amarillo para SUPERVISOR_WFSA
COLOR_GERENTE = "#4CAF50"       # Verde para GERENTE_WFSA
COLOR_CLIENTE = "#0275AA"       # Azul WFSA para CLIENTE

