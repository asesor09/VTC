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
    
    # 3. NUEVA TABLA: Categorías de Gastos
    cur.execute('''CREATE TABLE IF NOT EXISTS categorias_gastos (id SERIAL PRIMARY KEY, nombre TEXT UNIQUE NOT NULL)''')
    
    # Insertar admin por defecto
    cur.execute("INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES ('Jacobo Admin', 'admin', 'Jacobo2026', 'admin') ON CONFLICT DO NOTHING")
    
    # Categorías base por defecto
    categorias_base = ["Combustible", "Peaje", "Mantenimiento", "Seguro", "Otros"]
    for cat in categorias_base:
        cur.execute("INSERT INTO categorias_gastos (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (cat,))
    
    # Actualización segura de columnas
    columnas_extra = [("kilometraje", "INTEGER"), ("aplica_concepto", "TEXT"), ("concepto", "TEXT"), ("detalle", "TEXT"), ("tipo_gasto", "TEXT")]
    for col, tipo in columnas_extra:
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
                        st.error(f"⚠️ Error: La placa '{placa}' ya está registrada en el sistema o hay un problema con los datos.")
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

# --- 🏷️ CATEGORÍAS ---
elif menu == "🏷️ Categorías":
    st.subheader("Gestión de Categorías de Gastos")
    conn = conectar_db()
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("**Agregar Nueva Categoría**")
        with st.form("form_nueva_cat"):
            nueva_cat = st.text_input("Nombre de la categoría")
            if st.form_submit_button("Guardar"):
                if nueva_cat.strip() != "":
                    cur = conn.cursor()
                    try:
                        cur.execute("INSERT INTO categorias_gastos (nombre) VALUES (%s)", (nueva_cat.strip(),))
                        conn.commit(); st.success("✅ Agregada"); st.rerun()
                    except Exception as e:
                        conn.rollback() 
                        st.error("⚠️ Esta categoría ya existe.")
                else:
                    st.warning("El campo no puede estar vacío.")
    
    with c2:
        st.markdown("**Categorías Disponibles**")
        df_cat = pd.read_sql("SELECT id, nombre FROM categorias_gastos ORDER BY nombre", conn)
        st.dataframe(df_cat, use_container_width=True, hide_index=True)
        
    conn.close()

# --- 💸 GASTOS (AHORA CON PESTAÑA PARA EDITAR) ---
elif menu == "💸 Registro de Gastos":
    conn = conectar_db()
    v_data = pd.read_sql("SELECT id, placa, km_actual FROM vehiculos", conn)
    cat_data = pd.read_sql("SELECT nombre FROM categorias_gastos ORDER BY nombre", conn)
    lista_categorias = cat_data['nombre'].tolist()
    
    if not v_data.empty:
        t_reg_gasto, t_edit_gasto, t_ver_gasto = st.tabs(["➕ Registrar Gasto", "✏️ Editar Gasto", "🔍 Historial"])
        
        # PESTAÑA 1: REGISTRAR
        with t_reg_gasto:
            with st.form("form_gasto"):
                st.subheader("Registrar Nuevo Gasto")
                c1, c2 = st.columns(2)
                with c1:
                    v_sel = st.selectbox("Vehículo", v_data['placa'])
                    v_id = int(v_data[v_data['placa'] == v_sel]['id'].values[0])
                    tipo_g = st.selectbox("Categoría Principal", lista_categorias)
                    monto = st.number_input("Monto ($)", min_value=0.0)
                    kilometraje = st.number_input("Kilometraje al momento del gasto", min_value=0)
                with c2:
                    destino = st.text_input("Destino / Institución")
                    fecha = st.date_input("Fecha", datetime.now().date())
                    aplica_concepto = st.radio("¿Ingresar concepto específico?", ["No", "Sí"])
                    concepto_adicional = st.text_input("Escribe el concepto") if aplica_concepto == "Sí" else ""
                detalle = st.text_area("Detalles adicionales")
                
                if st.form_submit_button("Guardar Gasto"):
                    cur = conn.cursor()
                    cur.execute("INSERT INTO gastos (vehiculo_id, tipo_gasto, monto, institucion_destino, fecha, detalle, kilometraje, aplica_concepto, concepto) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (v_id, tipo_g, monto, destino, fecha, detalle, kilometraje, aplica_concepto, concepto_adicional))
                    cur.execute("UPDATE vehiculos SET km_actual = GREATEST(km_actual, %s) WHERE id = %s", (kilometraje, v_id))
                    conn.commit(); st.success("✅ Guardado"); st.rerun()
        
        # PESTAÑA 2: EDITAR (NUEVO)
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
                        n_detalle = st.text_area("Detalles adicionales
