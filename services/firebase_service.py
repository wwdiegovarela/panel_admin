"""
Servicio de Firebase Admin - Gestión de usuarios
"""
import firebase_admin
from firebase_admin import auth, credentials
from typing import Optional, Dict
import os
import requests
import json
from config.settings import FIREBASE_API_KEY, PROJECT_ID


class FirebaseService:
    """Servicio para gestionar usuarios en Firebase Authentication"""
    
    def __init__(self):
        """Inicializar Firebase Admin SDK"""
        try:
            # Intentar inicializar si no está inicializado
            firebase_admin.get_app()
        except ValueError:
            # Si no está inicializado, inicializar
            # Nota: Asegúrate de tener las credenciales en la variable de entorno
            # GOOGLE_APPLICATION_CREDENTIALS
            # Asegurar PROJECT_ID para Admin SDK
            if not os.environ.get('GOOGLE_CLOUD_PROJECT'):
                os.environ['GOOGLE_CLOUD_PROJECT'] = PROJECT_ID
            if not os.environ.get('GCLOUD_PROJECT'):
                os.environ['GCLOUD_PROJECT'] = PROJECT_ID
            # Intentar localizar credenciales de servicio si no están configuradas
            if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                try:
                    candidates = [
                        'worldwide-470917-b0939d44c1ae.json',
                        'service-account.json',
                        'credentials.json'
                    ]
                    for c in candidates:
                        if os.path.exists(c):
                            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(c)
                            break
                except Exception:
                    pass
            cred = credentials.ApplicationDefault()
            # Pasar projectId explícitamente para evitar errores
            firebase_admin.initialize_app(cred, {
                'projectId': PROJECT_ID
            })
    
    def create_user(self, email: str, password: str, display_name: str) -> Dict:
        """
        Crear un nuevo usuario en Firebase Authentication
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            display_name: Nombre completo del usuario
            
        Returns:
            Dict con información del usuario creado
        """
        try:
            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name,
                email_verified=False
            )
            
            return {
                'success': True,
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'message': f'Usuario {email} creado exitosamente'
            }
        except auth.EmailAlreadyExistsError:
            return {
                'success': False,
                'error': 'El email ya está registrado'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error al crear usuario: {str(e)}'
            }
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Obtener información de un usuario por email
        
        Args:
            email: Email del usuario
            
        Returns:
            Dict con información del usuario o None si no existe
        """
        try:
            user = auth.get_user_by_email(email)
            return {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'email_verified': user.email_verified,
                'disabled': user.disabled,
                'creation_timestamp': user.user_metadata.creation_timestamp,
                'last_sign_in_timestamp': user.user_metadata.last_sign_in_timestamp
            }
        except auth.UserNotFoundError:
            return None
        except Exception as e:
            print(f"Error al obtener usuario: {e}")
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """
        Autenticar usuario con email y contraseña usando Firebase REST API
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            
        Returns:
            Dict con información del usuario autenticado o None si falla
        """
        try:
            # Asegurar carga de .env en runtime si no está presente en el entorno
            if not os.getenv('FIREBASE_API_KEY'):
                try:
                    # Cargar usando dotenv si está disponible
                    from dotenv import load_dotenv as _ld
                    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    env_path = os.path.join(project_root, '.env')
                    if os.path.exists(env_path):
                        _ld(env_path, override=True)
                except Exception:
                    # Fallback manual
                    try:
                        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                        env_path = os.path.join(project_root, '.env')
                        if os.path.exists(env_path):
                            with open(env_path, 'r', encoding='utf-8') as fh:
                                for line in fh:
                                    line = line.lstrip('\ufeff').strip()
                                    if not line or line.startswith('#') or '=' not in line:
                                        continue
                                    key, val = line.split('=', 1)
                                    key = key.lstrip('\ufeff').strip()
                                    val = val.lstrip('\ufeff').strip().strip('"').strip("'")
                                    if key and val and key not in os.environ:
                                        os.environ[key] = val
                    except Exception:
                        pass
            # Tomar API key desde entorno en runtime (prioridad) o desde settings
            api_key = os.getenv('FIREBASE_API_KEY', FIREBASE_API_KEY)
            # Verificar si la API key es válida (no es la placeholder)
            if not api_key or api_key == "AIzaSyBvQZvQZvQZvQZvQZvQZvQZvQZvQZvQ":
                # Solo permitir fallback en modo desarrollo explícito
                if os.getenv('AUTH_DEV_MODE') == '1':
                    print(f"[AUTH] API key no configurada, usando autenticación básica (DEV) para {email}")
                    user = auth.get_user_by_email(email)
                    if user and not user.disabled:
                        return {
                            'uid': user.uid,
                            'email': user.email,
                            'display_name': user.display_name,
                            'email_verified': user.email_verified,
                            'disabled': user.disabled
                        }
                    else:
                        print(f"[AUTH] Usuario {email} no encontrado o deshabilitado")
                        return None
                else:
                    print("[AUTH] API key no configurada: se requiere FIREBASE_API_KEY para validar contraseña")
                    return None
            
            # Configuración de Firebase Auth REST API
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
            
            # Datos para la autenticación
            auth_data = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            # Realizar petición de autenticación
            response = requests.post(auth_url, json=auth_data)
            
            if response.status_code == 200:
                auth_result = response.json()
                print(f"[AUTH] Usuario {email} autenticado exitosamente")
                
                return {
                    'uid': auth_result.get('localId'),
                    'email': auth_result.get('email'),
                    'display_name': auth_result.get('displayName'),
                    'email_verified': auth_result.get('emailVerified', False),
                    'id_token': auth_result.get('idToken'),
                    'refresh_token': auth_result.get('refreshToken'),
                    'expires_in': auth_result.get('expiresIn')
                }
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Error desconocido')
                print(f"[AUTH] Error de autenticación: {error_message}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"[AUTH] Error de conexión: {e}")
            return None
        except Exception as e:
            print(f"[AUTH] Error al autenticar usuario: {e}")
            return None
    
    def update_user(self, email: str, **kwargs) -> Dict:
        """
        Actualizar información de un usuario
        
        Args:
            email: Email del usuario
            **kwargs: Campos a actualizar (password, display_name, disabled, etc.)
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            user = auth.get_user_by_email(email)
            auth.update_user(user.uid, **kwargs)
            
            return {
                'success': True,
                'message': f'Usuario {email} actualizado exitosamente'
            }
        except auth.UserNotFoundError:
            return {
                'success': False,
                'error': 'Usuario no encontrado'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error al actualizar usuario: {str(e)}'
            }
    
    def delete_user(self, email: str) -> Dict:
        """
        Eliminar un usuario de Firebase Authentication
        
        Args:
            email: Email del usuario
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            user = auth.get_user_by_email(email)
            auth.delete_user(user.uid)
            
            return {
                'success': True,
                'message': f'Usuario {email} eliminado exitosamente'
            }
        except auth.UserNotFoundError:
            return {
                'success': False,
                'error': 'Usuario no encontrado'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error al eliminar usuario: {str(e)}'
            }
    
    def reset_password(self, email: str, new_password: str) -> Dict:
        """
        Resetear contraseña de un usuario
        
        Args:
            email: Email del usuario
            new_password: Nueva contraseña
            
        Returns:
            Dict con resultado de la operación
        """
        return self.update_user(email, password=new_password)
    
    def disable_user(self, email: str) -> Dict:
        """Desactivar un usuario"""
        return self.update_user(email, disabled=True)
    
    def enable_user(self, email: str) -> Dict:
        """Activar un usuario"""
        return self.update_user(email, disabled=False)

