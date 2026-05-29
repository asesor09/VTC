import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import hashlib

# --- CONFIGURACIÓN DE CONEXIÓN GLOBAL (NEON) ---
DB_URL = "postgresql://neondb_owner:npg_Hw6lhgzCrm0B@ep-winter-mud-aqkidkqi-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require&connect_timeout=10"

def conectar_db():
    return psycopg2.connect(DB_URL)

def inicializar_tablas():
    conn = conectar_db()
    conn.autocommit = True 
    cur = conn.cursor()
    
    # 1. Tablas Originales
    cur.execute('''CREATE TABLE IF NOT EXISTS vehiculos (id SERIAL PRIMARY KEY, placa TEXT UNIQUE NOT NULL, marca TEXT, modelo TEXT, tipo TEXT, conductor TEXT, km_actual INTEGER DEFAULT 0)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS gastos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), tipo_gasto TEXT, monto NUMERIC, institucion_destino TEXT, fecha DATE, detalle TEXT, kilometraje INTEGER, aplica_concepto TEXT, concepto TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS mantenimientos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), descripcion TEXT, km_proximo_cambio INTEGER, estado TEXT DEFAULT 'Pendiente')''')
    
    # 2. Tablas de Usuarios y Configuración
    cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nombre TEXT, usuario TEXT UNIQUE, clave TEXT, rol TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS configuracion (id SERIAL PRIMARY KEY, email_remitente TEXT, email_clave TEXT, email_destino TEXT)''')
    
    # 3. Tabla de Categorías Mejorada (Con precio predeterminado)
    cur.execute('''CREATE TABLE IF NOT EXISTS categorias_gastos (id SERIAL PRIMARY KEY, nombre TEXT UNIQUE NOT NULL, precio_predeterminado NUMERIC DEFAULT 0.0)''')
    
    # Insertar admin por defecto
    cur.execute("INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES ('Jacobo Admin', 'admin', 'Jacobo2026', 'admin') ON CONFLICT DO NOTHING")
    
    # Categorías base por defecto
    categorias_base = ["Combustible", "Peaje", "Mantenimiento", "Seguro", "Otros"]
    for cat in categorias_base:
        cur.execute("INSERT INTO categorias_gastos (nombre, precio_predeterminado) VALUES (%s, 0.0) ON CONFLICT DO NOTHING", (cat,))
    
    # Actualización segura de columnas (Para la tabla gastos y la nueva columna en categorías)
    try: cur.execute("ALTER TABLE categorias_gastos ADD COLUMN precio_predeterminado NUMERIC DEFAULT 0.0;")
    except Exception: pass

    columnas_extra_gastos = [("kilometraje", "INTEGER"), ("aplica_concepto", "TEXT"), ("concepto", "TEXT"), ("detalle", "TEXT"), ("tipo_gasto", "TEXT")]
    for col, tipo in columnas_extra_gastos:
        try: cur.execute(f"ALTER TABLE gastos ADD COLUMN {col} {tipo};")
        except Exception: pass
            
    conn.close()

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="Transporte Jacobo Pro", layout="wide", page_icon="🚐")

# --- SISTEMA ANTI-ATASCOS ---
if 'db_ready' not in st.session_state:
    try:
        inicializar_tablas()
        st.session_state['db_ready'] = True
    except Exception as e:
        st.error(f"Error conectando a la base de datos. Detalle: {e}")
        st.stop()

# --- LOGIN ---
if 'u_rol' not in st.session_state:
    st.session_state['u_rol'] = None
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.sidebar.title("🔐 Acceso")
    u = st.sidebar.text_input("Usuario")
    p = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Ingresar"):
        try:
            conn = conectar_db(); cur = conn.cursor()
            cur.execute("SELECT rol FROM usuarios WHERE usuario=%s AND clave=%s", (u, p))
            resultado = cur.fetchone()
            if resultado:
                st.session_state['logged_in'] = True
                st.session_state['u_rol'] = resultado[0]
                conn.close(); st.rerun()
            else:
                cur.execute("SELECT rol FROM usuarios WHERE usuario=%s AND clave=%s", (u, hashlib.sha256(p.encode()).hexdigest()))
                res_cifrado = cur.fetchone()
                if res_cifrado:
                    st.session_state['logged_in'] = True
                    st.session_state['u_rol'] = res_cifrado[0]
                    conn.close(); st.rerun()
                else:
                    st.sidebar.error("Usuario o contraseña incorrectos")
                    conn.close()
        except Exception as e:
            st.sidebar.error(f"Error de conexión: {e}")
    st.title("🚐 Sistema de Gestión de Transporte")
    st.warning("Por favor, ingrese sus credenciales en la barra lateral.")
    st.stop()

# --- MENÚ ---
st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({'logged_in': False, 'u_rol': None}))
st.title("🚐 Panel de Control - Acceso Global")

opciones_menu = ["🏠 Inicio", "🚚 Gestión de Vehículos", "🏷️ Categorías", "💸 Registro de Gastos", "🛠️ Mantenimientos", "🔒 Config. Alertas"]
if st.session_state.u_rol == "admin":
    opciones_menu.append("⚙️ Usuarios")

menu = st.sidebar.radio("Navegación", opciones_menu)

# --- 🏠 INICIO (CON FILTROS Y EXCEL) ---
if menu == "🏠 Inicio":
    st.subheader("Resumen y Análisis General")
    conn = conectar_db()
    
    v = pd.read_sql("SELECT COUNT(*) FROM vehiculos", conn).iloc[0,0]
    g = pd.read_sql("SELECT SUM(monto) FROM gastos", conn).iloc[0,0] or 0
    m = pd.read_sql("SELECT COUNT(*) FROM mantenimientos WHERE estado='Pendiente'", conn).iloc[0,0]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Vehículos en la Flota", v)
    c2.metric("Total Inversión (Gastos)", f"${g:,.2f}")
    c3.metric("Mantenimientos Pendientes", m)
    
    st.markdown("---")
    st.subheader("📊 Análisis Interactivo de Gastos")
    
    df_inicio = pd.read_sql("SELECT g.fecha, v.placa, g.tipo_gasto, g.concepto, g.monto, g.institucion_destino, g.detalle, g.kilometraje FROM gastos g JOIN vehiculos v ON g.vehiculo_id = v.id", conn)
    conn.close()
    
    if not df_inicio.empty:
        df_inicio['fecha'] = pd.to_datetime(df_inicio['fecha']).dt.date
        
        st.markdown("### 🔍 Filtrar Información")
        f1, f2, f3 = st.columns(3)
        with f1:
            placas_unicas = df_inicio['placa'].unique().tolist()
            placas_sel = st.multiselect("Seleccionar Vehículo (Placa)", placas_unicas, default=placas_unicas)
        with f2:
            fecha_inicio = st.date_input("Fecha Inicio", df_inicio['fecha'].min())
        with f3:
            fecha_fin = st.date_input("Fecha Fin", df_inicio['fecha'].max())
            
        mask = (df_inicio['placa'].isin(placas_sel)) & (df_inicio['fecha'] >= fecha_inicio) & (df_inicio['fecha'] <= fecha_fin)
        df_filtrado = df_inicio[mask]
        
        st.markdown("---")
        if not df_filtrado.empty:
            st.metric("Total Gastos (Según filtros aplicados)", f"${df_filtrado['monto'].sum():,.2f}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Gastos por Vehículo")
                st.bar_chart(data=df_filtrado.groupby('placa')['monto'].sum().reset_index(), x='placa', y='monto')
            with col2:
                st.markdown("#### Evolución por Fechas")
                gastos_fecha = df_filtrado.groupby('fecha')['monto'].sum().reset_index()
                st.line_chart(data=gastos_fecha.set_index('fecha'))
                
            st.markdown("#### Detalle de Registros")
            st.dataframe(df_filtrado, use_container_width=True)
            
            csv_data = df_filtrado.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button(label="📥 Descargar Reporte a Excel", data=csv_data, file_name=f"reporte_inicio_{fecha_inicio}_a_{fecha_fin}.csv", mime="text/csv")
        else:
            st.warning("No se encontraron registros para los filtros seleccionados.")
    else:
        st.info("Aún no hay registros de gastos en el sistema.")

# --- 🚚 VEHÍCULOS ---
elif menu == "🚚 Gestión de Vehículos":
    t_reg, t_edit, t_ver = st.tabs(["➕ Registrar", "✏️ Editar", "🔍 Ver Flota"])
    with t_reg:
        with st.form("reg_vehiculo"):
            c1, c2 = st.columns(2)
            placa = c1.text_input("Placa").upper(); marca = c1.text_input("Marca")
            modelo = c1.text_input("Modelo"); cond = c2.text_input("Conductor")
            tipo = c2.selectbox("Tipo", ["Ambulancia", "Van", "Particular", "Microbús"])
            km = c2.number_input("KM Inicial", min_value=0)
            if st.form_submit_button("Guardar Vehículo"):
                if placa.strip() == "":
                    st.warning("La placa no puede estar vacía.")
                else:
                    conn = conectar_db(); cur = conn.cursor()
                    try:
                        cur.execute("INSERT INTO vehiculos (placa, marca, modelo, tipo, conductor, km_actual) VALUES (%s,%s,%s,%s,%s,%s)", (placa, marca, modelo, tipo, cond, km))
                        conn.commit(); st.success("✅ Registrado con éxito"); st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"⚠️ Error: La placa '{placa}' ya está registrada en el sistema.")
                    finally:
                        conn.close()

    with t_edit:
        conn = conectar_db(); df_v = pd.read_sql("SELECT * FROM vehiculos", conn); conn.close()
        if not df_v.empty:
            sel = st.selectbox("Elegir Vehículo a Editar", df_v['placa'])
            d = df_v[df_v['placa'] == sel].iloc[0]
            with st.form("edit_vehiculo"):
                n_cond = st.text_input("Conductor", value=d['conductor'])
                n_tipo = st.selectbox("Tipo", ["Ambulancia", "Van", "Particular", "Microbús"], index=["Ambulancia", "Van", "Particular", "Microbús"].index(d['tipo']))
                n_km = st.number_input("KM Actual", value=int(d['km_actual']))
                if st.form_submit_button("Actualizar Vehículo"):
                    conn = conectar_db(); cur = conn.cursor()
                    cur.execute("UPDATE vehiculos SET conductor=%s, tipo=%s, km_actual=%s WHERE placa=%s", (n_cond, n_tipo, n_km, sel))
                    conn.commit(); conn.close(); st.success("✅ Actualizado"); st.rerun()

    with t_ver:
        conn = conectar_db()
        st.dataframe(pd.read_sql("SELECT placa, marca, modelo, tipo, conductor, km_actual FROM vehiculos", conn), use_container_width=True)
        conn.close()

# --- 🏷️ CATEGORÍAS (AHORA CON OPCIÓN DE EDITAR PRECIOS) ---
elif menu == "🏷️ Categorías":
    st.subheader("Gestión de Categorías de Gastos")
    conn = conectar_db()
    
    t_cat_reg, t_cat_edit, t_cat_ver = st.tabs(["➕ Nueva Categoría", "✏️ Editar Categoría", "🔍 Ver Categorías"])
    
    with t_cat_reg:
        with st.form("form_nueva_cat"):
            c1, c2 = st.columns(2)
            nueva_cat = c1.text_input("Nombre de la categoría")
            precio_base = c2.number_input("Precio predeterminado ($)", min_value=0.0, value=0.0, step=100.0)
            if st.form_submit_button("Guardar Categoría"):
                if nueva_cat.strip() != "":
                    cur = conn.cursor()
                    try:
                        cur.execute("INSERT INTO categorias_gastos (nombre, precio_predeterminado) VALUES (%s, %s)", (nueva_cat.strip(), precio_base))
                        conn.commit(); st.success("✅ Categoría agregada"); st.rerun()
                    except Exception as e:
                        conn.rollback(); st.error("⚠️ Esta categoría ya existe.")
                else:
                    st.warning("El nombre no puede estar vacío.")
                    
    with t_cat_edit:
        df_cat_edit = pd.read_sql("SELECT id, nombre, precio_predeterminado FROM categorias_gastos ORDER BY nombre", conn)
        if not df_cat_edit.empty:
            cat_sel = st.selectbox("Seleccione la categoría a editar", df_cat_edit['nombre'])
            datos_cat = df_cat_edit[df_cat_edit['nombre'] == cat_sel].iloc[0]
            
            with st.form("form_edit_cat"):
                n_nom_cat = st.text_input("Nombre", value=datos_cat['nombre'])
                n_precio_cat = st.number_input("Precio predeterminado ($)", min_value=0.0, value=float(datos_cat['precio_predeterminado']), step=100.0)
                if st.form_submit_button("Actualizar Categoría"):
                    cur = conn.cursor()
                    try:
                        cur.execute("UPDATE categorias_gastos SET nombre=%s, precio_predeterminado=%s WHERE id=%s", (n_nom_cat, n_precio_cat, int(datos_cat['id'])))
                        conn.commit(); st.success("✅ Actualizado"); st.rerun()
                    except Exception as e:
                        conn.rollback(); st.error("⚠️ Error: Ya existe otra categoría con ese nombre.")
        else:
            st.info("No hay categorías registradas.")
            
    with t_cat_ver:
        df_cat_ver = pd.read_sql("SELECT nombre AS Categoría, precio_predeterminado AS Precio_Base FROM categorias_gastos ORDER BY nombre", conn)
        st.dataframe(df_cat_ver, use_container_width=True, hide_index=True)
        
    conn.close()

# --- 💸 GASTOS (REGISTRO DINÁMICO DE PRECIOS Y EDICIÓN) ---
elif menu == "💸 Registro de Gastos":
    conn = conectar_db()
    v_data = pd.read_sql("SELECT id, placa, km_actual FROM vehiculos", conn)
    
    # Extraemos categorías y sus precios en un diccionario para uso rápido
    cat_data = pd.read_sql("SELECT nombre, precio_predeterminado FROM categorias_gastos ORDER BY nombre", conn)
    cat_dict = dict(zip(cat_data['nombre'], cat_data['precio_predeterminado']))
    lista_categorias = list(cat_dict.keys())
    
    if not v_data.empty:
        t_reg_gasto, t_edit_gasto, t_ver_gasto = st.tabs(["➕ Registrar Gasto", "✏️ Editar Gasto", "🔍 Historial"])
        
        # PESTAÑA 1: REGISTRAR (Sin st.form para que el precio cambie dinámicamente)
        with t_reg_gasto:
            st.subheader("Registrar Nuevo Gasto")
            c1, c2 = st.columns(2)
            with c1:
                v_sel = st.selectbox("Vehículo", v_data['placa'])
                v_id = int(v_data[v_data['placa'] == v_sel]['id'].values[0])
                
                tipo_g = st.selectbox("Categoría Principal", lista_categorias)
                # Al cambiar la categoría, se actualiza el monto por defecto automáticamente
                precio_defecto = float(cat_dict.get(tipo_g, 0.0))
                
                monto = st.number_input("Monto ($)", min_value=0.0, value=precio_defecto, step=100.0)
                kilometraje = st.number_input("Kilometraje al momento del gasto", min_value=0)
            with c2:
                destino = st.text_input("Destino / Institución")
                fecha = st.date_input("Fecha", datetime.now().date())
                aplica_concepto = st.radio("¿Ingresar concepto específico?", ["No", "Sí"])
                concepto_adicional = st.text_input("Escribe el concepto") if aplica_concepto == "Sí" else ""
            detalle = st.text_area("Detalles adicionales")
            
            if st.button("Guardar Gasto (Registrar)", type="primary"):
                cur = conn.cursor()
                cur.execute("INSERT INTO gastos (vehiculo_id, tipo_gasto, monto, institucion_destino, fecha, detalle, kilometraje, aplica_concepto, concepto) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (v_id, tipo_g, monto, destino, fecha, detalle, kilometraje, aplica_concepto, concepto_adicional))
                cur.execute("UPDATE vehiculos SET km_actual = GREATEST(km_actual, %s) WHERE id = %s", (kilometraje, v_id))
                conn.commit(); st.success("✅ Guardado exitosamente"); st.rerun()
        
        # PESTAÑA 2: EDITAR
        with t_edit_gasto:
            df_edit = pd.read_sql("SELECT g.id, g.fecha, v.placa, g.tipo_gasto, g.monto, g.institucion_destino, g.detalle, g.kilometraje, g.aplica_concepto, g.concepto, g.vehiculo_id FROM gastos g JOIN vehiculos v ON g.vehiculo_id = v.id ORDER BY g.fecha DESC", conn)
            
            if not df_edit.empty:
                df_edit['display'] = df_edit['fecha'].astype(str) + " | Vehículo: " + df_edit['placa'] + " | " + df_edit['tipo_gasto'] + " | $" + df_edit['monto'].astype(str)
                sel_gasto = st.selectbox("Seleccione el gasto a editar", df_edit['display'])
                
                if sel_gasto:
                    g_data = df_edit[df_edit['display'] == sel_gasto].iloc[0]
                    with st.form("form_edit_gasto"):
                        st.subheader("Actualizar Datos del Gasto")
                        c1, c2 = st.columns(2)
                        with c1:
                            idx_vehiculo = int(v_data[v_data['placa'] == g_data['placa']].index[0])
                            n_v_sel = st.selectbox("Vehículo", v_data['placa'], index=idx_vehiculo)
                            n_v_id = int(v_data[v_data['placa'] == n_v_sel]['id'].values[0])
                            
                            idx_cat = lista_categorias.index(g_data['tipo_gasto']) if g_data['tipo_gasto'] in lista_categorias else 0
                            n_tipo_g = st.selectbox("Categoría Principal", lista_categorias, index=idx_cat)
                            
                            n_monto = st.number_input("Monto ($)", min_value=0.0, value=float(g_data['monto']))
                            val_km = int(g_data['kilometraje']) if pd.notna(g_data['kilometraje']) else 0
                            n_km = st.number_input("Kilometraje", min_value=0, value=val_km)
                        
                        with c2:
                            val_destino = "" if pd.isna(g_data['institucion_destino']) else str(g_data['institucion_destino'])
                            n_destino = st.text_input("Destino / Institución", value=val_destino)
                            n_fecha = st.date_input("Fecha", pd.to_datetime(g_data['fecha']).date())
                            
                            n_aplica = st.radio("¿Ingresar concepto específico? (Edición)", ["No", "Sí"], index=1 if g_data['aplica_concepto'] == "Sí" else 0)
                            val_concepto = "" if pd.isna(g_data['concepto']) else str(g_data['concepto'])
                            n_concepto = st.text_input("Escribe el concepto", value=val_concepto) if n_aplica == "Sí" else ""
                            
                        val_detalle = "" if pd.isna(g_data['detalle']) else str(g_data['detalle'])
                        n_detalle = st.text_area("Detalles adicionales", value=val_detalle)
                        
                        if st.form_submit_button("Actualizar Gasto"):
                            cur = conn.cursor()
                            cur.execute("UPDATE gastos SET vehiculo_id=%s, tipo_gasto=%s, monto=%s, institucion_destino=%s, fecha=%s, detalle=%s, kilometraje=%s, aplica_concepto=%s, concepto=%s WHERE id=%s", 
                                        (n_v_id, n_tipo_g, n_monto, n_destino, n_fecha, n_detalle, n_km, n_aplica, n_concepto, int(g_data['id'])))
                            cur.execute("UPDATE vehiculos SET km_actual = GREATEST(km_actual, %s) WHERE id = %s", (n_km, n_v_id))
                            conn.commit(); st.success("✅ Gasto actualizado correctamente"); st.rerun()
            else:
                st.info("No hay gastos registrados en el sistema para editar.")
                
        # PESTAÑA 3: VER / HISTORIAL
        with t_ver_gasto:
            df_g = pd.read_sql("SELECT g.*, v.placa FROM gastos g JOIN vehiculos v ON g.vehiculo_id = v.id", conn)
            if not df_g.empty:
                df_g['mes'] = pd.to_datetime(df_g['fecha']).dt.strftime('%Y-%m')
                mes_sel = st.selectbox("Filtrar historial por Mes", sorted(df_g['mes'].unique(), reverse=True))
                st.dataframe(df_g[df_g['mes'] == mes_sel][['fecha', 'placa', 'tipo_gasto', 'monto', 'kilometraje', 'concepto', 'institucion_destino']], use_container_width=True)
            else:
                st.info("No hay historial de gastos.")
                
    else: 
        st.warning("⚠️ Registra un vehículo primero.")
    conn.close()

# --- 🛠️ MANTENIMIENTOS ---
elif menu == "🛠️ Mantenimientos":
    conn = conectar_db(); v_data = pd.read_sql("SELECT id, placa, km_actual FROM vehiculos", conn)
    if not v_data.empty:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("form_mant"):
                v_sel = st.selectbox("Vehículo", v_data['placa'])
                v_id = int(v_data[v_data['placa'] == v_sel]['id'].values[0])
                desc = st.text_area("Descripción")
                km_prox = st.number_input("Kilometraje para próximo cambio", min_value=0)
                if st.form_submit_button("Programar"):
                    cur = conn.cursor()
                    cur.execute("INSERT INTO mantenimientos (vehiculo_id, descripcion, km_proximo_cambio, estado) VALUES (%s, %s, %s, 'Pendiente')", (v_id, desc, km_prox))
                    conn.commit(); st.success("✅ Programado"); st.rerun()
        with c2:
            st.dataframe(v_data[['placa', 'km_actual']], use_container_width=True)
            
        df_m = pd.read_sql("SELECT m.id, v.placa, m.descripcion, m.km_proximo_cambio, m.estado FROM mantenimientos m JOIN vehiculos v ON m.vehiculo_id = v.id", conn)
        if not df_m.empty:
            pendientes = df_m[df_m['estado'] == 'Pendiente']
            if not pendientes.empty:
                st.dataframe(pendientes[['placa', 'descripcion', 'km_proximo_cambio']], use_container_width=True)
                with st.form("actualizar_mant"):
                    mant_id = st.selectbox("ID a cerrar", pendientes['id'])
                    if st.form_submit_button("Marcar como Realizado"):
                        cur = conn.cursor(); cur.execute("UPDATE mantenimientos SET estado = 'Realizado' WHERE id = %s", (int(mant_id),))
                        conn.commit(); st.success("✅ Cerrado"); st.rerun()
    conn.close()

# --- ⚙️ USUARIOS ---
elif menu == "⚙️ Usuarios" and st.session_state.u_rol == "admin":
    st.title("⚙️ Usuarios")
    conn = conectar_db()
    with st.form("fu"):
        nom = st.text_input("Nombre"); usr = st.text_input("Usuario"); clv = st.text_input("Clave")
        rol = st.selectbox("Rol", ["vendedor", "admin"])
        if st.form_submit_button("👤 Crear"):
            if usr.strip() == "":
                st.warning("El usuario no puede estar vacío.")
            else:
                cur = conn.cursor()
                try:
                    cur.execute("INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES (%s,%s,%s,%s)", (nom, usr, hashlib.sha256(clv.encode()).hexdigest(), rol))
                    conn.commit(); st.success("✅ Usuario creado"); st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error("⚠️ Error: Este nombre de usuario ya existe en el sistema.")
    
    st.dataframe(pd.read_sql("SELECT nombre, usuario, rol FROM usuarios", conn), use_container_width=True)
    conn.close()

# --- 🔒 CONFIG. ALERTAS ---
elif menu == "🔒 Config. Alertas":
    st.title("🔒 Configuración Segura")
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM configuracion WHERE id = 1"); act = cur.fetchone()
    with st.form("f_conf"):
        rem = st.text_input("Gmail Remitente", value=act[1] if act else "")
        cla = st.text_input("Clave Gmail (16 letras)", type="password", value=act[2] if act else "")
        des = st.text_input("Correo Destino", value=act[3] if act else "")
        if st.form_submit_button("💾 Guardar"):
            cur.execute('''INSERT INTO configuracion (id, email_remitente, email_clave, email_destino)
                           VALUES (1, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET email_remitente=EXCLUDED.email_remitente, email_clave=EXCLUDED.email_clave, email_destino=EXCLUDED.email_destino''', (rem, cla, des))
            conn.commit(); st.success("✅ Guardado."); st.rerun()
    conn.close()
