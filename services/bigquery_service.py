"""
Servicio de BigQuery - CRUD de datos
"""
from google.cloud import bigquery
from typing import List, Dict, Optional
import uuid
import os
from datetime import datetime
from config.settings import *


class BigQueryService:
    """Servicio para gestionar datos en BigQuery"""
    
    def __init__(self):
        """Inicializar servicio de BigQuery"""
        self._client = None
        # Cache en memoria para mejorar rendimiento
        self._roles_cache = None
        self._usuarios_cache = {}  # Cache por cliente_rol
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutos
        self._instalaciones_cache = None
        self._contactos_instalacion_cache = None
    
    @property
    def client(self):
        """Obtener cliente de BigQuery (inicialización perezosa)"""
        if self._client is None:
            try:
                # Configurar credenciales si no están configuradas
                if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                    # Buscar archivo de credenciales en el directorio actual
                    creds_file = 'worldwide-470917-b0939d44c1ae.json'
                    if os.path.exists(creds_file):
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(creds_file)
                        print(f"✅ Credenciales configuradas: {creds_file}")
                    else:
                        print("⚠️ No se encontró archivo de credenciales")
                
                # Configurar codificación UTF-8 para Windows
                import locale
                import sys
                if os.name == 'nt':  # Windows
                    os.environ['PYTHONIOENCODING'] = 'utf-8'
                    # Configurar stdout y stderr para UTF-8
                    sys.stdout.reconfigure(encoding='utf-8')
                    sys.stderr.reconfigure(encoding='utf-8')
                    try:
                        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
                    except locale.Error:
                        # Fallback si no está disponible
                        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                
                self._client = bigquery.Client(project=PROJECT_ID)
                print("✅ Cliente de BigQuery inicializado correctamente")
            except Exception as e:
                print(f"⚠️ Error al conectar con BigQuery: {e}")
                print("💡 Asegúrate de tener las credenciales de Google Cloud configuradas")
                raise e
        return self._client
    
    def _is_cache_valid(self) -> bool:
        """Verificar si el cache es válido"""
        if not self._cache_timestamp:
            return False
        return (datetime.now() - self._cache_timestamp).seconds < self._cache_duration
    
    def clear_cache(self):
        """Limpiar cache manualmente"""
        self._roles_cache = None
        self._usuarios_cache = {}  # Limpiar cache por cliente
        self._instalaciones_cache = None
        self._contactos_instalacion_cache = None
        self._cache_timestamp = None
    
    # ============================================
    # USUARIOS
    # ============================================
    
    def get_usuarios(self, cliente_rol: Optional[str] = None) -> List[Dict]:
        """Obtener lista de usuarios"""
        query = f"""
            SELECT 
                email_login,
                firebase_uid,
                cliente_rol,
                nombre_completo,
                cargo,
                telefono,
                activo,
                ver_todas_instalaciones,
                fecha_creacion,
                ultima_sesion
            FROM `{TABLE_USUARIOS}`
        """
        
        if cliente_rol:
            query += f" WHERE cliente_rol = '{cliente_rol}'"
        
        query += " ORDER BY nombre_completo"
        
        results = self.client.query(query).result()
        return [dict(row) for row in results]
    
    def create_usuario(self, email: str, firebase_uid: str, cliente_rol: str,
                      nombre_completo: str, rol_id: str = "CLIENTE", cargo: str = None, 
                      telefono: str = None, ver_todas_instalaciones: bool = False) -> Dict:
        """Crear un nuevo usuario en BigQuery"""
        query = f"""
            INSERT INTO `{TABLE_USUARIOS}` 
            (email_login, firebase_uid, cliente_rol, nombre_completo, rol_id, cargo, telefono, 
             activo, ver_todas_instalaciones, fecha_creacion)
            VALUES 
            (@email, @firebase_uid, @cliente_rol, @nombre_completo, @rol_id, @cargo, @telefono,
             TRUE, @ver_todas, CURRENT_TIMESTAMP())
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email),
                bigquery.ScalarQueryParameter("firebase_uid", "STRING", firebase_uid),
                bigquery.ScalarQueryParameter("cliente_rol", "STRING", cliente_rol),
                bigquery.ScalarQueryParameter("nombre_completo", "STRING", nombre_completo),
                bigquery.ScalarQueryParameter("rol_id", "STRING", rol_id),
                bigquery.ScalarQueryParameter("cargo", "STRING", cargo),
                bigquery.ScalarQueryParameter("telefono", "STRING", telefono),
                bigquery.ScalarQueryParameter("ver_todas", "BOOL", ver_todas_instalaciones),
            ]
        )
        
        try:
            self.client.query(query, job_config=job_config).result()
            return {'success': True, 'message': 'Usuario creado en BigQuery'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_usuario(self, email: str, **campos) -> Dict:
        """Actualizar un usuario"""
        set_clauses = []
        parameters = [bigquery.ScalarQueryParameter("email", "STRING", email)]
        
        for campo, valor in campos.items():
            set_clauses.append(f"{campo} = @{campo}")
            tipo = "STRING"
            if isinstance(valor, bool):
                tipo = "BOOL"
            elif isinstance(valor, int):
                tipo = "INT64"
            parameters.append(bigquery.ScalarQueryParameter(campo, tipo, valor))
        
        query = f"""
            UPDATE `{TABLE_USUARIOS}`
            SET {', '.join(set_clauses)}
            WHERE email_login = @email
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=parameters)
        
        try:
            self.client.query(query, job_config=job_config).result()
            return {'success': True, 'message': 'Usuario actualizado'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_usuario(self, email: str) -> Dict:
        """Eliminar un usuario (marca como inactivo)"""
        return self.update_usuario(email, activo=False)

    def delete_usuario_total(self, email: str) -> Dict:
        """Eliminar completamente un usuario y sus relaciones en BigQuery.

        Acciones:
        - Borrar filas en `usuario_instalaciones` del email
        - Borrar filas en `usuario_contactos` del email (si existe la tabla)
        - Si existe contacto asociado al email, borrar sus asignaciones en `instalacion_contacto` y el registro en `contactos`
        - Borrar el registro en `usuarios_app`
        """
        errors: list[str] = []

        def exec_dml(query: str, params: list) -> None:
            try:
                job_config = bigquery.QueryJobConfig(query_parameters=params)
                self.client.query(query, job_config=job_config).result()
            except Exception as e:
                errors.append(str(e))

        # 1) usuario_instalaciones
        exec_dml(
            f"""
            DELETE FROM `{TABLE_USUARIO_INST}`
            WHERE email_login = @email
            """,
            [bigquery.ScalarQueryParameter("email", "STRING", email)],
        )

        # 2) usuario_contactos (si existe)
        try:
            exec_dml(
                f"""
                DELETE FROM `{TABLE_USUARIO_CONTACTOS}`
                WHERE email_login = @email
                """,
                [bigquery.ScalarQueryParameter("email", "STRING", email)],
            )
        except Exception as e:
            # Tabla puede no existir, registrar pero continuar
            errors.append(f"usuario_contactos: {e}")

        # 3) contactos e instalacion_contacto
        try:
            contacto = self.get_contacto_por_email(email)
        except Exception:
            contacto = None
        if contacto and contacto.get("contacto_id"):
            contacto_id = contacto["contacto_id"]
            # Borrar asignaciones de instalaciones del contacto
            try:
                exec_dml(
                    f"""
                    DELETE FROM `{TABLE_INST_CONTACTO}`
                    WHERE contacto_id = @contacto_id
                    """,
                    [bigquery.ScalarQueryParameter("contacto_id", "STRING", contacto_id)],
                )
            except Exception as e:
                # Si hay streaming buffer, no bloquear la eliminación total; se limpiará en sincronizaciones futuras
                if 'streaming buffer' not in str(e).lower():
                    errors.append(str(e))
            # Borrar el registro de contacto (si falla por buffer, lo dejamos activo=False como fallback)
            try:
                exec_dml(
                    f"""
                    DELETE FROM `{TABLE_CONTACTOS}`
                    WHERE contacto_id = @contacto_id
                    """,
                    [bigquery.ScalarQueryParameter("contacto_id", "STRING", contacto_id)],
                )
            except Exception as e:
                if 'streaming buffer' in str(e).lower():
                    # Fallback: marcar inactivo
                    try:
                        exec_dml(
                            f"""
                            UPDATE `{TABLE_CONTACTOS}`
                            SET activo = FALSE
                            WHERE contacto_id = @contacto_id
                            """,
                            [bigquery.ScalarQueryParameter("contacto_id", "STRING", contacto_id)],
                        )
                    except Exception as e2:
                        errors.append(str(e2))
                else:
                    errors.append(str(e))

        # 4) usuarios_app
        exec_dml(
            f"""
            DELETE FROM `{TABLE_USUARIOS}`
            WHERE email_login = @email
            """,
            [bigquery.ScalarQueryParameter("email", "STRING", email)],
        )

        if errors:
            return {"success": False, "error": "; ".join(errors)}
        return {"success": True, "message": "Usuario eliminado completamente"}
    
    # ============================================
    # INSTALACIONES
    # ============================================
    
    def get_instalaciones(self, cliente_rol: Optional[str] = None) -> List[Dict]:
        """Obtener lista de instalaciones"""
        query = f"""
            SELECT 
                instalacion_rol,
                cliente_rol,
                comuna,
                direccion,
                geolatitud,
                geolongitud
            FROM `{TABLE_INSTALACIONES}`
        """
        
        if cliente_rol:
            query += f" WHERE cliente_rol = '{cliente_rol}'"
        
        query += " ORDER BY instalacion_rol"
        
        results = self.client.query(query).result()
        return [dict(row) for row in results]
    
    def get_clientes(self) -> List[str]:
        """Obtener lista de clientes únicos desde las instalaciones"""
        query = f"""
            SELECT DISTINCT cliente_rol
            FROM `{TABLE_INSTALACIONES}`
            WHERE cliente_rol IS NOT NULL
            ORDER BY cliente_rol
        """
        
        results = self.client.query(query).result()
        return [row.cliente_rol for row in results]
    
    def get_instalaciones_con_zonas(self, cliente_rol: Optional[str] = None) -> List[Dict]:
        """Obtener lista de instalaciones con sus zonas (optimizado con cache)"""
        # Usar cache si no hay filtro de cliente
        cache_key = f"instalaciones_{cliente_rol or 'all'}"
        if not cliente_rol and hasattr(self, '_instalaciones_cache') and self._instalaciones_cache:
            return self._instalaciones_cache
        
        query = f"""
            SELECT 
                i.instalacion_rol,
                i.cliente_rol,
                i.comuna,
                i.direccion,
                i.geolatitud,
                i.geolongitud,
                z.zona
            FROM `{TABLE_INSTALACIONES}` i
            LEFT JOIN `{TABLE_ZONAS_INSTALACIONES}` z
                ON i.instalacion_rol = z.instalacion
            WHERE i.instalacion_rol IS NOT NULL
        """
        
        if cliente_rol:
            query += f" AND i.cliente_rol = '{cliente_rol}'"
        
        query += " ORDER BY i.instalacion_rol"
        
        # Configuración optimizada para la consulta
        job_config = bigquery.QueryJobConfig(
            use_query_cache=True,
            use_legacy_sql=False,
            maximum_bytes_billed=500000000,  # 500MB
            job_timeout_ms=30000,  # 30 segundos
            dry_run=False
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            instalaciones = [dict(row) for row in results]
            
            # Cachear resultados si no hay filtro de cliente
            if not cliente_rol:
                self._instalaciones_cache = instalaciones
            
            return instalaciones
        except Exception as e:
            print(f"Error al obtener instalaciones: {str(e)}")
            return []
    
    # ============================================
    # CONTACTOS
    # ============================================
    
    def get_contactos(self, cliente_rol: Optional[str] = None) -> List[Dict]:
        """Obtener lista de contactos"""
        query = f"""
            SELECT 
                contacto_id,
                nombre_contacto,
                telefono,
                cargo,
                email,
                activo,
                fecha_creacion
            FROM `{TABLE_CONTACTOS}`
            WHERE activo = TRUE
        """
        
        # Note: cliente_rol removed from SELECT as it doesn't exist in the table
        # Filtering by cliente_rol would need to be done via JOIN with instalacion_contacto
        
        query += " ORDER BY nombre_contacto"
        
        results = self.client.query(query).result()
        return [dict(row) for row in results]
    
    def create_contacto(self, nombre: str, telefono: str,
                       cargo: str = None, email: str = None, es_usuario_app: bool = False) -> Dict:
        """Crear un nuevo contacto"""
        contacto_id = str(uuid.uuid4())
        
        # Si es usuario app, usar email como email_usuario_app
        email_usuario_app = email if es_usuario_app else None
        
        query = f"""
            INSERT INTO `{TABLE_CONTACTOS}`
            (contacto_id, nombre_contacto, telefono, cargo, email, 
             activo, fecha_creacion, es_usuario_app, email_usuario_app)
            VALUES
            (@contacto_id, @nombre, @telefono, @cargo, @email,
             TRUE, CURRENT_TIMESTAMP(), @es_usuario_app, @email_usuario_app)
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("contacto_id", "STRING", contacto_id),
                bigquery.ScalarQueryParameter("nombre", "STRING", nombre),
                bigquery.ScalarQueryParameter("telefono", "STRING", telefono),
                bigquery.ScalarQueryParameter("cargo", "STRING", cargo),
                bigquery.ScalarQueryParameter("email", "STRING", email),
                bigquery.ScalarQueryParameter("es_usuario_app", "BOOL", es_usuario_app),
                bigquery.ScalarQueryParameter("email_usuario_app", "STRING", email_usuario_app),
            ]
        )
        
        try:
            self.client.query(query, job_config=job_config).result()
            return {'success': True, 'contacto_id': contacto_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_contacto(self, contacto_id: str, **campos) -> Dict:
        """Actualizar un contacto"""
        set_clauses = []
        parameters = [bigquery.ScalarQueryParameter("contacto_id", "STRING", contacto_id)]
        
        for campo, valor in campos.items():
            set_clauses.append(f"{campo} = @{campo}")
            tipo = "STRING"
            if isinstance(valor, bool):
                tipo = "BOOL"
            elif isinstance(valor, int):
                tipo = "INT64"
            parameters.append(bigquery.ScalarQueryParameter(campo, tipo, valor))
        
        query = f"""
            UPDATE `{TABLE_CONTACTOS}`
            SET {', '.join(set_clauses)}
            WHERE contacto_id = @contacto_id
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=parameters)
        
        try:
            self.client.query(query, job_config=job_config).result()
            return {'success': True, 'message': 'Contacto actualizado'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_contacto(self, contacto_id: str) -> Dict:
        """Eliminar un contacto (marca como inactivo)"""
        return self.update_contacto(contacto_id, activo=False)
    
    def update_contacto_por_email(self, email: str, **campos) -> Dict:
        """Actualizar contacto usando email_usuario_app"""
        set_clauses = []
        parameters = [bigquery.ScalarQueryParameter("email", "STRING", email)]
        
        for campo, valor in campos.items():
            set_clauses.append(f"{campo} = @{campo}")
            tipo = "STRING"
            if isinstance(valor, bool):
                tipo = "BOOL"
            elif isinstance(valor, int):
                tipo = "INT64"
            parameters.append(bigquery.ScalarQueryParameter(campo, tipo, valor))
        
        query = f"""
            UPDATE `{TABLE_CONTACTOS}`
            SET {', '.join(set_clauses)}
            WHERE email_usuario_app = @email OR email = @email
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=parameters)
        
        try:
            self.client.query(query, job_config=job_config).result()
            return {'success': True, 'message': 'Contacto actualizado'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def asignar_contacto_instalacion(self, contacto_id: str, instalacion_rol: str) -> Dict:
        """Asignar un contacto a una instalación"""
        query = f"""
            INSERT INTO `{TABLE_INST_CONTACTO}`
            (instalacion_rol, contacto_id, fecha_asignacion)
            VALUES
            (@instalacion, @contacto_id, CURRENT_TIMESTAMP())
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("instalacion", "STRING", instalacion_rol),
                bigquery.ScalarQueryParameter("contacto_id", "STRING", contacto_id),
            ]
        )
        
        try:
            self.client.query(query, job_config=job_config).result()
            return {'success': True, 'message': 'Contacto asignado a instalación'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_contacto_por_email(self, email: str) -> Dict:
        """Obtener contacto por email del usuario app"""
        query = f"""
            SELECT contacto_id, nombre_contacto, telefono, cargo, email, 
                   activo, es_usuario_app, email_usuario_app
            FROM `{TABLE_CONTACTOS}`
            WHERE (email_usuario_app = @email OR email = @email)
              AND activo = TRUE
            LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email)
            ]
        )
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            for row in results:
                return dict(row)
            return None
        except Exception as e:
            print(f"Error al obtener contacto: {e}")
            return None
    
    def sincronizar_instalaciones_contacto(self, email_usuario: str, instalaciones_con_cliente: Dict[str, str]) -> Dict:
        """
        Sincronizar instalaciones de usuario con instalaciones de contacto
        
        Args:
            email_usuario: Email del usuario app
            instalaciones_con_cliente: Dict {instalacion_rol: cliente_rol}
        """
        try:
            contacto = self.get_contacto_por_email(email_usuario)
            if not contacto:
                return {'success': False, 'error': 'Usuario no es contacto'}
            contacto_id = contacto['contacto_id']
            
            # Calcular delta: existentes vs deseadas
            existentes = set(self.get_instalaciones_contacto(contacto_id) or [])
            deseadas = set(instalaciones_con_cliente.keys()) if instalaciones_con_cliente else set()
            a_eliminar = list(existentes - deseadas)
            a_insertar = [(inst, instalaciones_con_cliente.get(inst)) for inst in (deseadas - existentes)]

            # Intentar eliminar solo las que sobran (puede fallar si hay streaming buffer)
            if a_eliminar:
                try:
                    delete_query = f"""
                        DELETE FROM `{TABLE_INST_CONTACTO}`
                        WHERE contacto_id = @contacto_id
                            AND instalacion_rol IN UNNEST(@insts)
                    """
                    job_config = bigquery.QueryJobConfig(
                        query_parameters=[
                                bigquery.ScalarQueryParameter("contacto_id", "STRING", contacto_id),
                                bigquery.ArrayQueryParameter("insts", "STRING", a_eliminar),
                        ]
                    )
                    self.client.query(delete_query, job_config=job_config).result()
                except Exception as de:
                    # Si hay buffer de streaming, avisar pero continuar con inserciones
                    if 'streaming buffer' in str(de).lower():
                        print("[CONTACTO] Eliminación diferida por streaming buffer; se intentará más tarde")
                    else:
                        raise

            # Insertar nuevas asignaciones (streaming insert está bien para altas)
            if a_insertar:
                rows_to_insert = []
                for inst, cliente_rol in a_insertar:
                    rows_to_insert.append({
                        'cliente_rol': cliente_rol,
                        'instalacion_rol': inst,
                        'contacto_id': contacto_id,
                        'fecha_asignacion': None
                    })
                table_ref = self.client.get_table(TABLE_INST_CONTACTO)
                errors = self.client.insert_rows_json(table_ref, rows_to_insert)
                if errors:
                    return {'success': False, 'error': f'Error en inserción masiva: {errors}'}

            return {'success': True, 'message': f'{len(deseadas)} instalaciones sincronizadas'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_instalaciones_contacto(self, contacto_id: str) -> List[str]:
        """Obtener instalaciones asignadas a un contacto"""
        query = f"""
            SELECT instalacion_rol
            FROM `{TABLE_INST_CONTACTO}`
            WHERE contacto_id = @contacto_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("contacto_id", "STRING", contacto_id)
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        return [row.instalacion_rol for row in results]
    
    def asignar_instalaciones_contacto(self, contacto_id: str, instalaciones: List[str]) -> Dict:
        """Asignar múltiples instalaciones a un contacto"""
        delete_query = f"""
            DELETE FROM `{TABLE_INST_CONTACTO}`
            WHERE contacto_id = @contacto_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("contacto_id", "STRING", contacto_id)
            ]
        )
        try:
            self.client.query(delete_query, job_config=job_config).result()
            if instalaciones:
                rows_to_insert = []
                for instalacion in instalaciones:
                    rows_to_insert.append({
                        'instalacion_rol': instalacion,
                        'contacto_id': contacto_id,
                        'fecha_asignacion': None
                    })
                table_ref = self.client.get_table(TABLE_INST_CONTACTO)
                errors = self.client.insert_rows_json(table_ref, rows_to_insert)
                if errors:
                    return {'success': False, 'error': f'Error en inserción masiva: {errors}'}
            return {'success': True, 'message': f'{len(instalaciones)} instalaciones asignadas'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ============================================
    # PERMISOS - USUARIO_INSTALACIONES
    # ============================================
    
    def get_instalaciones_usuario(self, email: str) -> List[str]:
        """Obtener instalaciones asignadas a un usuario"""
        query = f"""
            SELECT instalacion_rol
            FROM `{TABLE_USUARIO_INST}`
            WHERE email_login = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email)
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        return [row.instalacion_rol for row in results]
    
    def get_instalaciones_usuario_detalle(self, email: str) -> Dict[str, Dict]:
        """
        Obtener instalaciones asignadas a un usuario con detalles adicionales
        
        Returns:
            Dict {instalacion_rol: {'puede_ver': bool, 'requiere_encuesta_individual': bool}}
        """
        query = f"""
            SELECT 
                instalacion_rol,
                puede_ver,
                COALESCE(requiere_encuesta_individual, FALSE) as requiere_encuesta_individual
            FROM `{TABLE_USUARIO_INST}`
            WHERE email_login = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email)
            ]
        )
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            detalle = {}
            for row in results:
                detalle[row.instalacion_rol] = {
                    'puede_ver': row.puede_ver,
                    'requiere_encuesta_individual': row.requiere_encuesta_individual
                }
            return detalle
        except Exception as e:
            print(f"Error al obtener detalle de instalaciones: {e}")
            return {}
    
    def asignar_instalaciones(self, email: str, cliente_rol: str, instalaciones: List[str]) -> Dict:
        """Asignar instalaciones a un usuario"""
        delete_query = f"""
            DELETE FROM `{TABLE_USUARIO_INST}`
            WHERE email_login = @email
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email)
            ]
        )
        try:
            self.client.query(delete_query, job_config=job_config).result()
            if instalaciones:
                rows_to_insert = []
                for instalacion in instalaciones:
                    rows_to_insert.append({
                        'email_login': email,
                        'cliente_rol': cliente_rol,
                        'instalacion_rol': instalacion,
                        'puede_ver': True,
                        'fecha_asignacion': None
                    })
                table_ref = self.client.get_table(TABLE_USUARIO_INST)
                errors = self.client.insert_rows_json(table_ref, rows_to_insert)
                if errors:
                    return {'success': False, 'error': f'Error en inserción masiva: {errors}'}
            return {'success': True, 'message': f'{len(instalaciones)} instalaciones asignadas'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def asignar_instalaciones_multi_cliente(self, email: str, instalaciones_con_cliente: Dict[str, str], instalaciones_detalle: Dict[str, Dict] = None) -> Dict:
        """
        Asignar instalaciones de múltiples clientes a un usuario
        """
        delete_query = f"""
            DELETE FROM `{TABLE_USUARIO_INST}`
            WHERE email_login = @email
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email)
            ]
        )
        try:
            self.client.query(delete_query, job_config=job_config).result()
            rows_to_insert = []
            if instalaciones_con_cliente:
                seen_pairs = set()
            for instalacion_rol, cliente_rol in instalaciones_con_cliente.items():
                requiere_encuesta = False
                if instalaciones_detalle and instalacion_rol in instalaciones_detalle:
                    requiere_encuesta = instalaciones_detalle[instalacion_rol].get('requiere_encuesta_individual', False)
                    key = (email, instalacion_rol)
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    rows_to_insert.append({
                        'email_login': email,
                        'cliente_rol': cliente_rol,
                        'instalacion_rol': instalacion_rol,
                        'puede_ver': True,
                        'requiere_encuesta_individual': requiere_encuesta,
                        'fecha_asignacion': None
                    })
                if rows_to_insert:
                    table_ref = self.client.get_table(TABLE_USUARIO_INST)
                    errors = self.client.insert_rows_json(table_ref, rows_to_insert)
                    if errors:
                        return {'success': False, 'error': f'Error en inserción masiva: {errors}'}
            return {'success': True, 'message': f'{len(instalaciones_con_cliente)} instalaciones asignadas'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ============================================
    # PERMISOS - USUARIO_CONTACTOS (CONTROL GRANULAR)
    # ============================================
    
    def get_contactos_usuario(self, email: str, instalacion_rol: str) -> List[str]:
        """Obtener contactos asignados a un usuario para una instalación"""
        query = f"""
            SELECT contacto_id
            FROM `{TABLE_USUARIO_CONTACTOS}`
            WHERE email_login = @email
              AND instalacion_rol = @instalacion
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email),
                bigquery.ScalarQueryParameter("instalacion", "STRING", instalacion_rol),
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        return [row.contacto_id for row in results]
    
    def asignar_contactos_usuario(self, email: str, instalacion_rol: str, contactos: List[str], asignado_por: str) -> Dict:
        """Asignar contactos específicos a un usuario para una instalación"""
        delete_query = f"""
            DELETE FROM `{TABLE_USUARIO_CONTACTOS}`
            WHERE email_login = @email
              AND instalacion_rol = @instalacion
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email),
                bigquery.ScalarQueryParameter("instalacion", "STRING", instalacion_rol),
            ]
        )
        try:
            self.client.query(delete_query, job_config=job_config).result()
            if contactos:
                rows_to_insert = []
                for contacto_id in contactos:
                    rows_to_insert.append({
                        'id': str(uuid.uuid4()),
                        'email_login': email,
                        'instalacion_rol': instalacion_rol,
                        'contacto_id': contacto_id,
                        'fecha_asignacion': None,
                        'asignado_por': asignado_por
                    })
                table_ref = self.client.get_table(TABLE_USUARIO_CONTACTOS)
                errors = self.client.insert_rows_json(table_ref, rows_to_insert)
                if errors:
                    return {'success': False, 'error': f'Error en inserción masiva: {errors}'}
            return {'success': True, 'message': f'{len(contactos)} contactos asignados'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_contactos_instalacion(self, instalacion_rol: str) -> List[Dict]:
        """Obtener todos los contactos disponibles para una instalación"""
        query = f"""
            SELECT 
                c.contacto_id,
                c.nombre_contacto,
                c.telefono,
                c.cargo,
                c.email
            FROM `{TABLE_CONTACTOS}` c
            INNER JOIN `{TABLE_INST_CONTACTO}` ic
              ON c.contacto_id = ic.contacto_id
            WHERE ic.instalacion_rol = @instalacion
              AND c.activo = TRUE
            ORDER BY c.nombre_contacto
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("instalacion", "STRING", instalacion_rol)
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        return [dict(row) for row in results]
    
    def get_todos_contactos_por_instalacion(self) -> Dict[str, List[Dict]]:
        """
        Obtener todos los contactos agrupados por instalación en una sola query (con cache)
        
        Returns:
            Dict {instalacion_rol: [contactos]}
        """
        # Usar cache si está disponible
        if hasattr(self, '_contactos_instalacion_cache') and self._contactos_instalacion_cache:
            return self._contactos_instalacion_cache
        
        query = f"""
            SELECT 
                ic.instalacion_rol,
                c.contacto_id,
                c.nombre_contacto,
                c.telefono,
                c.cargo,
                c.email
            FROM `{TABLE_INST_CONTACTO}` ic
            INNER JOIN `{TABLE_CONTACTOS}` c
              ON ic.contacto_id = c.contacto_id
            WHERE c.activo = TRUE
            ORDER BY ic.instalacion_rol, c.nombre_contacto
        """
        
        # Configuración optimizada para la consulta
        job_config = bigquery.QueryJobConfig(
            use_query_cache=True,
            use_legacy_sql=False,
            maximum_bytes_billed=500000000,  # 500MB
            job_timeout_ms=30000,  # 30 segundos
            dry_run=False
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            # Agrupar por instalación evitando duplicados
            contactos_por_instalacion = {}
            contactos_vistos = set()  # Para evitar duplicados
            
            for row in results:
                instalacion = row.instalacion_rol
                contacto_key = f"{instalacion}_{row.contacto_id}"
                
                # Evitar duplicados de forma eficiente
                if contacto_key not in contactos_vistos:
                    contactos_vistos.add(contacto_key)
                    
                if instalacion not in contactos_por_instalacion:
                    contactos_por_instalacion[instalacion] = []
                
                contactos_por_instalacion[instalacion].append({
                    'contacto_id': row.contacto_id,
                    'nombre_contacto': row.nombre_contacto,
                    'telefono': row.telefono,
                    'cargo': row.cargo,
                    'email': row.email
                })
            
            # Cachear resultados
            self._contactos_instalacion_cache = contactos_por_instalacion
            
            return contactos_por_instalacion
        except Exception as e:
            print(f"Error al obtener contactos por instalación: {e}")
            return {}
    
    # ============================================
    # ROLES Y PERMISOS
    # ============================================
    
    def get_roles(self) -> List[Dict]:
        """Obtiene todos los roles disponibles con cache"""
        # Verificar cache
        if self._roles_cache and self._is_cache_valid():
            return self._roles_cache
        
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
            FROM `{TABLE_ROLES}`
            WHERE activo = TRUE
            ORDER BY 
                CASE rol_id
                    WHEN 'ADMIN_WFSA' THEN 1
                    WHEN 'SUBGERENTE_WFSA' THEN 2
                    WHEN 'JEFE_WFSA' THEN 3
                    WHEN 'SUPERVISOR_WFSA' THEN 4
                    WHEN 'GERENTE_WFSA' THEN 5
                    WHEN 'CLIENTE' THEN 6
                    ELSE 7
                END
        """
        
        try:
            # Configurar job para mejor rendimiento
            job_config = bigquery.QueryJobConfig(
                use_query_cache=True,  # Usar cache de consultas de BigQuery
                use_legacy_sql=False,  # Usar SQL estándar
                maximum_bytes_billed=1000000000,  # Límite de 1GB
                dry_run=False,  # Ejecutar realmente
                job_timeout_ms=30000  # Timeout de 30 segundos
            )
            
            query_job = self.client.query(query, job_config=job_config)
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
            
            # Guardar en cache
            self._roles_cache = roles
            self._cache_timestamp = datetime.now()
            
            return roles
        except Exception as e:
            print(f"Error al obtener roles: {str(e)}")
            # Retornar rol por defecto si hay error
            return [{
                'rol_id': 'CLIENTE',
                'nombre_rol': 'Cliente',
                'descripcion': 'Usuario cliente estándar',
                'permisos': {
                    'puede_ver_cobertura': True,
                    'puede_ver_encuestas': True,
                    'puede_enviar_mensajes': True,
                    'puede_ver_empresas': False,
                    'puede_ver_metricas_globales': False,
                    'puede_ver_trabajadores': False,
                    'puede_ver_mensajes_recibidos': False,
                    'es_admin': False
                },
                'activo': True
            }]
    
    def get_usuarios_con_roles(self, cliente_rol: Optional[str] = None) -> List[Dict]:
        """Obtiene usuarios con sus roles y permisos usando JOIN directo con cache"""
        # Verificar cache inteligente por cliente
        cache_key = cliente_rol or 'all'
        if cache_key in self._usuarios_cache and self._is_cache_valid():
            return self._usuarios_cache[cache_key]
        
        try:
            # Primero intentar con JOIN a la tabla de roles
            query = f"""
            SELECT 
                    u.email_login,
                    u.firebase_uid,
                    u.cliente_rol,
                    u.nombre_completo,
                    u.cargo,
                    u.telefono,
                    u.rol_id,
                    r.nombre_rol,
                    r.puede_ver_cobertura,
                    r.puede_ver_encuestas,
                    r.puede_enviar_mensajes,
                    r.puede_ver_empresas,
                    r.puede_ver_metricas_globales,
                    r.puede_ver_trabajadores,
                    r.puede_ver_mensajes_recibidos,
                    r.es_admin,
                    u.ver_todas_instalaciones,
                    u.activo as usuario_activo,
                    u.ultima_sesion,
                    u.fecha_creacion
                FROM `{TABLE_USUARIOS}` u
                LEFT JOIN `{TABLE_ROLES}` r ON u.rol_id = r.rol_id
                WHERE u.activo = TRUE
            """
        
            if cliente_rol:
                query += f" AND u.cliente_rol = '{cliente_rol}'"
            
            query += " ORDER BY u.fecha_creacion DESC"
            
            # Configurar job para mejor rendimiento
            job_config = bigquery.QueryJobConfig(
                use_query_cache=True,  # Usar cache de consultas
                use_legacy_sql=False,  # Usar SQL estándar
                maximum_bytes_billed=1000000000  # Límite de 1GB
            )
            
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            usuarios = []
            for row in results:
                # Manejar valores NULL de forma optimizada
                rol_id = row.rol_id or 'CLIENTE'
                nombre_rol = row.nombre_rol or 'Cliente'
                
                # Manejar codificación de caracteres especiales
                def safe_str(value):
                    if value is None:
                        return None
                    try:
                        # Si ya es string, verificar codificación
                        if isinstance(value, str):
                            # Intentar codificar y decodificar para limpiar
                            return value.encode('utf-8', errors='ignore').decode('utf-8')
                        else:
                            # Convertir a string y limpiar
                            return str(value).encode('utf-8', errors='ignore').decode('utf-8')
                    except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
                        # Fallback: convertir a string y limpiar caracteres problemáticos
                        try:
                            return str(value).encode('ascii', errors='ignore').decode('ascii')
                        except:
                            return str(value)
                
                usuarios.append({
                    'email_login': safe_str(row.email_login),
                    'firebase_uid': safe_str(row.firebase_uid),
                    'cliente_rol': safe_str(row.cliente_rol),
                    'nombre_completo': safe_str(row.nombre_completo),
                    'cargo': safe_str(row.cargo) if row.cargo else None,
                    'telefono': safe_str(row.telefono) if row.telefono else None,
                    'rol_id': safe_str(rol_id),
                    'nombre_rol': safe_str(nombre_rol),
                    'permisos': {
                        'puede_ver_cobertura': row.puede_ver_cobertura or True,
                        'puede_ver_encuestas': row.puede_ver_encuestas or True,
                        'puede_enviar_mensajes': row.puede_enviar_mensajes or True,
                        'puede_ver_empresas': row.puede_ver_empresas or False,
                        'puede_ver_metricas_globales': row.puede_ver_metricas_globales or False,
                        'puede_ver_trabajadores': row.puede_ver_trabajadores or False,
                        'puede_ver_mensajes_recibidos': row.puede_ver_mensajes_recibidos or False,
                        'es_admin': row.es_admin or False
                    },
                    'ver_todas_instalaciones': row.ver_todas_instalaciones,
                    'activo': row.usuario_activo,
                    'ultima_sesion': row.ultima_sesion.isoformat() if row.ultima_sesion else None,
                    'fecha_creacion': row.fecha_creacion.isoformat() if row.fecha_creacion else None
                })
            
            # Guardar en cache inteligente por cliente
            self._usuarios_cache[cache_key] = usuarios
            self._cache_timestamp = datetime.now()
            
            return usuarios
        except Exception as e:
            print(f"Error al obtener usuarios con roles: {str(e)}")
            # Si el error es por codificación, intentar con manejo de caracteres
            if "charmap" in str(e).lower() or "codec" in str(e).lower():
                print("[FALLBACK] Error de codificación, intentando con manejo de caracteres")
                try:
                    # Intentar nuevamente con configuración de codificación
                    import sys
                    if hasattr(sys.stdout, 'reconfigure'):
                        sys.stdout.reconfigure(encoding='utf-8')
                    if hasattr(sys.stderr, 'reconfigure'):
                        sys.stderr.reconfigure(encoding='utf-8')
                    
                    # Reintentar la consulta
                    query_job = self.client.query(query, job_config=job_config)
                    results = query_job.result()
                    
                    usuarios = []
                    for row in results:
                        # Manejar valores NULL de forma optimizada
                        rol_id = row.rol_id or 'CLIENTE'
                        nombre_rol = row.nombre_rol or 'Cliente'
                        
                        # Manejar codificación de caracteres especiales
                        def safe_str(value):
                            if value is None:
                                return None
                            try:
                                # Si ya es string, verificar codificación
                                if isinstance(value, str):
                                    # Intentar codificar y decodificar para limpiar
                                    return value.encode('utf-8', errors='ignore').decode('utf-8')
                                else:
                                    # Convertir a string y limpiar
                                    return str(value).encode('utf-8', errors='ignore').decode('utf-8')
                            except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
                                # Fallback: convertir a string y limpiar caracteres problemáticos
                                try:
                                    return str(value).encode('ascii', errors='ignore').decode('ascii')
                                except:
                                    return str(value)
                        
                        usuarios.append({
                            'email_login': safe_str(row.email_login),
                            'firebase_uid': safe_str(row.firebase_uid),
                            'cliente_rol': safe_str(row.cliente_rol),
                            'nombre_completo': safe_str(row.nombre_completo),
                            'cargo': safe_str(row.cargo) if row.cargo else None,
                            'telefono': safe_str(row.telefono) if row.telefono else None,
                            'rol_id': safe_str(rol_id),
                            'nombre_rol': safe_str(nombre_rol),
                            'permisos': {
                                'puede_ver_cobertura': row.puede_ver_cobertura or True,
                                'puede_ver_encuestas': row.puede_ver_encuestas or True,
                                'puede_enviar_mensajes': row.puede_enviar_mensajes or True,
                                'puede_ver_empresas': row.puede_ver_empresas or False,
                                'puede_ver_metricas_globales': row.puede_ver_metricas_globales or False,
                                'puede_ver_trabajadores': row.puede_ver_trabajadores or False,
                                'puede_ver_mensajes_recibidos': row.puede_ver_mensajes_recibidos or False,
                                'es_admin': row.es_admin or False
                            },
                            'ver_todas_instalaciones': row.ver_todas_instalaciones,
                            'activo': row.usuario_activo,
                            'ultima_sesion': row.ultima_sesion.isoformat() if row.ultima_sesion else None,
                            'fecha_creacion': row.fecha_creacion.isoformat() if row.fecha_creacion else None
                        })
                    
                    # Guardar en cache
                    self._usuarios_cache[cache_key] = usuarios
                    self._cache_timestamp = datetime.now()
                    
                    return usuarios
                except Exception as e3:
                    print(f"Error en reintento con codificación: {str(e3)}")
            
            # Si el error es por tabla de roles no encontrada, usar consulta simple
            if "roles" in str(e).lower() or "not found" in str(e).lower():
                print("[FALLBACK] Tabla de roles no encontrada, usando consulta simple")
                return self._get_usuarios_sin_roles(cliente_rol)
            # Fallback: obtener usuarios básicos y asignar rol por defecto
            try:
                usuarios_basicos = self.get_usuarios(cliente_rol)
                usuarios_con_roles = []
                
                for usuario in usuarios_basicos:
                    # Asignar rol por defecto si no tiene
                    rol_id = usuario.get('rol_id', 'CLIENTE')
                    if not rol_id or rol_id == 'CLIENTE':
                        # Para usuarios sin rol, asignar permisos básicos
                        permisos = {
                            'puede_ver_cobertura': True,
                            'puede_ver_encuestas': True,
                            'puede_enviar_mensajes': True,
                            'puede_ver_empresas': False,
                            'puede_ver_metricas_globales': False,
                            'puede_ver_trabajadores': False,
                            'puede_ver_mensajes_recibidos': False,
                            'es_admin': False
                        }
                    else:
                        # Intentar obtener permisos del rol
                        try:
                            roles = self.get_roles()
                            rol_data = next((r for r in roles if r['rol_id'] == rol_id), None)
                            if rol_data:
                                permisos = rol_data.get('permisos', {})
                            else:
                                permisos = {
                                    'puede_ver_cobertura': True,
                                    'puede_ver_encuestas': True,
                                    'puede_enviar_mensajes': True,
                                    'puede_ver_empresas': False,
                                    'puede_ver_metricas_globales': False,
                                    'puede_ver_trabajadores': False,
                                    'puede_ver_mensajes_recibidos': False,
                                    'es_admin': False
                                }
                        except:
                            permisos = {
                                'puede_ver_cobertura': True,
                                'puede_ver_encuestas': True,
                                'puede_enviar_mensajes': True,
                                'puede_ver_empresas': False,
                                'puede_ver_metricas_globales': False,
                                'puede_ver_trabajadores': False,
                                'puede_ver_mensajes_recibidos': False,
                                'es_admin': False
                            }
                    
                    usuarios_con_roles.append({
                        'email_login': usuario['email_login'],
                        'firebase_uid': usuario.get('firebase_uid'),
                        'cliente_rol': usuario['cliente_rol'],
                        'nombre_completo': usuario['nombre_completo'],
                        'cargo': usuario.get('cargo'),
                        'telefono': usuario.get('telefono'),
                        'rol_id': rol_id,
                        'nombre_rol': 'Cliente' if rol_id == 'CLIENTE' else rol_id,
                        'permisos': permisos,
                        'ver_todas_instalaciones': usuario.get('ver_todas_instalaciones', False),
                        'activo': usuario.get('activo', True),
                        'ultima_sesion': usuario.get('ultima_sesion'),
                        'fecha_creacion': usuario.get('fecha_creacion')
                    })
                
                return usuarios_con_roles
            except Exception as e2:
                print(f"Error en fallback: {str(e2)}")
                return []
    
    def _get_usuarios_sin_roles(self, cliente_rol: Optional[str] = None) -> List[Dict]:
        """Obtener usuarios sin información de roles (fallback cuando la tabla roles no existe)"""
        try:
            query = f"""
            SELECT 
                email_login,
                firebase_uid,
                cliente_rol,
                nombre_completo,
                cargo,
                telefono,
                COALESCE(rol_id, 'CLIENTE') as rol_id,
                ver_todas_instalaciones,
                activo,
                ultima_sesion,
                fecha_creacion
            FROM `{TABLE_USUARIOS}`
                WHERE activo = TRUE
        """
        
            if cliente_rol:
                query += f" AND cliente_rol = '{cliente_rol}'"
            query += " ORDER BY fecha_creacion DESC"
            results = self.client.query(query).result()
            usuarios = []
            for row in results:
                rol_id = row.rol_id or 'CLIENTE'
                nombre_rol = self._get_nombre_rol_basico(rol_id)
                permisos = self._get_permisos_basicos(rol_id)
            
                usuarios.append({
                    'email_login': safe_str(row.email_login),
                    'firebase_uid': safe_str(row.firebase_uid),
                    'cliente_rol': safe_str(row.cliente_rol),
                    'nombre_completo': safe_str(row.nombre_completo),
                    'cargo': row.cargo if row.cargo else None,
                    'telefono': row.telefono if row.telefono else None,
                    'rol_id': rol_id,
                    'nombre_rol': nombre_rol,
                    'permisos': permisos,
                    'ver_todas_instalaciones': row.ver_todas_instalaciones,
                    'activo': row.activo,
                    'ultima_sesion': row.ultima_sesion.isoformat() if row.ultima_sesion else None,
                    'fecha_creacion': row.fecha_creacion.isoformat() if row.fecha_creacion else None
                })
            
            return usuarios
        except Exception as e:
            print(f"Error en fallback sin roles: {str(e)}")
            return []
    
    def _get_nombre_rol_basico(self, rol_id: str) -> str:
        """Obtener nombre de rol básico sin consultar tabla"""
        nombres = {
            'ADMIN_WFSA': 'Administrador',
            'SUBGERENTE_WFSA': 'Subgerente',
            'JEFE_WFSA': 'Jefe',
            'SUPERVISOR_WFSA': 'Supervisor',
            'GERENTE_WFSA': 'Gerente',
            'CLIENTE': 'Cliente'
        }
        return nombres.get(rol_id, 'Cliente')
    
    def _get_permisos_basicos(self, rol_id: str) -> Dict:
        """Obtener permisos básicos sin consultar tabla"""
        if rol_id == 'ADMIN_WFSA':
            return {
                'puede_ver_cobertura': True,
                'puede_ver_encuestas': True,
                'puede_enviar_mensajes': True,
                'puede_ver_empresas': True,
                'puede_ver_metricas_globales': True,
                'puede_ver_trabajadores': True,
                'puede_ver_mensajes_recibidos': True,
                'es_admin': True
            }
        elif rol_id in ['SUBGERENTE_WFSA', 'JEFE_WFSA']:
            return {
                'puede_ver_cobertura': True,
                'puede_ver_encuestas': True,
                'puede_enviar_mensajes': True,
                'puede_ver_empresas': True,
                'puede_ver_metricas_globales': True,
                'puede_ver_trabajadores': True,
                'puede_ver_mensajes_recibidos': True,
                'es_admin': False
            }
        else:  # CLIENTE, SUPERVISOR_WFSA, GERENTE_WFSA
            return {
                'puede_ver_cobertura': True,
                'puede_ver_encuestas': True,
                'puede_enviar_mensajes': True,
                'puede_ver_empresas': False,
                'puede_ver_metricas_globales': False,
                'puede_ver_trabajadores': False,
                'puede_ver_mensajes_recibidos': False,
                'es_admin': False
            }
    
    def actualizar_rol_usuario(self, email_login: str, nuevo_rol_id: str) -> Dict:
        """Actualiza el rol de un usuario"""
        query = f"""
            UPDATE `{TABLE_USUARIOS}`
            SET rol_id = @nuevo_rol_id
            WHERE email_login = @email_login
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("nuevo_rol_id", "STRING", nuevo_rol_id),
                bigquery.ScalarQueryParameter("email_login", "STRING", email_login)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            query_job.result()
            return {'success': True, 'message': 'Rol actualizado correctamente'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

