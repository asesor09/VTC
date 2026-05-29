import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import hashlib

# --- CONFIGURACIÓN DE CONEXIÓN GLOBAL (NEON) ---
DB_URL = "postgresql://neondb_owner:npg_Hw6lhgzCrm0B@ep-winter-mud-aqkidkqi-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def conectar_db():
    return psycopg2.connect(DB_URL)

def inicializar_tablas():
    conn = conectar_db()
    conn.autocommit = True 
    cur = conn.cursor()
    
    # 1. Tablas originales (sin cambios para mantener compatibilidad)
    cur.execute('''CREATE TABLE IF NOT EXISTS vehiculos (id SERIAL PRIMARY KEY, placa TEXT UNIQUE NOT NULL, marca TEXT, modelo TEXT, tipo TEXT, conductor TEXT, km_actual INTEGER DEFAULT 0)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS gastos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), tipo_gasto TEXT, monto NUMERIC, institucion_destino TEXT, fecha DATE, detalle TEXT, kilometraje INTEGER, aplica_concepto TEXT, concepto TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS mantenimientos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), descripcion TEXT, km_proximo_cambio INTEGER, estado TEXT DEFAULT 'Pendiente')''')
    cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)''')
    
    # Crear admin por defecto si no existe
    cur.execute("INSERT INTO usuarios (usuario, password) VALUES ('admin', %s) ON CONFLICT DO NOTHING", (hashlib.sha256('Jacobo2026'.encode()).hexdigest(),))
    
    # Seguridad de columnas
    cols = [("kilometraje", "INTEGER"), ("aplica_concepto", "TEXT"), ("concepto", "TEXT"), ("detalle", "TEXT"), ("tipo_gasto", "TEXT")]
    for col, tipo in cols:
        try: cur.execute(f"ALTER TABLE gastos ADD COLUMN {col} {tipo};")
        except: pass
    conn.close()

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="Transporte Jacobo Pro", layout="wide", page_icon="🚐")
inicializar_tablas()

# --- LOGIN SEGÚN TU ESTRUCTURA ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.sidebar.title("🔐 Acceso")
    u = st.sidebar.text_input("Usuario")
    p = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Ingresar"):
        conn = conectar_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario=%s AND password=%s", (u, hashlib.sha256(p.encode()).hexdigest()))
        if cur.fetchone(): st.session_state['logged_in'] = True; conn.close(); st.rerun()
        else: st.error("Credenciales incorrectas"); conn.close()
    st.stop()

# --- PANEL PRINCIPAL ---
st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({'logged_in': False}))
st.title("🚐 Panel de Control - Acceso Global")
menu = st.sidebar.radio("Navegación", ["🏠 Inicio", "🚚 Gestión de Vehículos", "💸 Registro de Gastos", "🛠️ Mantenimientos", "📊 Reportes Avanzados", "👤 Usuarios"])

# --- LÓGICA DE VENTANAS (Tal cual la tenías) ---
if menu == "🏠 Inicio":
    # ... [Tu lógica de Inicio con gráficas] ...
    pass
elif menu == "🚚 Gestión de Vehículos":
    # ... [Tu lógica de Vehículos] ...
    pass
elif menu == "💸 Registro de Gastos":
    # ... [Tu lógica de Gastos] ...
    pass
# ... (Continúa con el resto de tus bloques tal cual los tenías en tu código original)
    
    # 1. Tabla de Vehículos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vehiculos (
            id SERIAL PRIMARY KEY,
            placa TEXT UNIQUE NOT NULL,
            marca TEXT,
            modelo TEXT,
            tipo TEXT,
            conductor TEXT,
            km_actual INTEGER DEFAULT 0
        )
    ''')
    
    # 2. Tabla de Gastos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY,
            vehiculo_id INTEGER REFERENCES vehiculos(id),
            tipo_gasto TEXT,
            monto NUMERIC,
            institucion_destino TEXT,
            fecha DATE,
            detalle TEXT,
            kilometraje INTEGER,
            aplica_concepto TEXT,
            concepto TEXT
        )
    ''')
    
    # 3. Tabla de Mantenimientos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS mantenimientos (
            id SERIAL PRIMARY KEY,
            vehiculo_id INTEGER REFERENCES vehiculos(id),
            descripcion TEXT,
            km_proximo_cambio INTEGER,
            estado TEXT DEFAULT 'Pendiente'
        )
    ''')
    
    # Seguridad para añadir columnas a gastos si es base antigua
    columnas_extra = [
        ("kilometraje", "INTEGER"),
        ("aplica_concepto", "TEXT"),
        ("concepto", "TEXT"),
        ("detalle", "TEXT"),
        ("tipo_gasto", "TEXT")
    ]
    for col, tipo in columnas_extra:
        try:
            cur.execute(f"ALTER TABLE gastos ADD COLUMN {col} {tipo};")
        except Exception:
            pass
            
    conn.close()

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="Transporte Jacobo Pro", layout="wide", page_icon="🚐")

# Seguridad
st.sidebar.title("🔐 Acceso")
password = st.sidebar.text_input("Contraseña", type="password")
if password != "Jacobo2026":
    st.title("🚐 Sistema de Gestión de Transporte")
    st.warning("Por favor, ingrese la contraseña en la barra lateral.")
    st.stop()

try:
    inicializar_tablas()
except Exception as e:
    st.sidebar.error(f"Error de conexión: {e}")


    
    
    
    # Recuperamos la información uniendo gastos y vehículos
    df_inicio = pd.read_sql("SELECT g.fecha, v.placa, g.monto FROM gastos g JOIN vehiculos v ON g.vehiculo_id = v.id", conn)
    conn.close()
    
    if not df_inicio.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Gastos por Carro")
            gastos_carro = df_inicio.groupby('placa')['monto'].sum().reset_index()
            gastos_carro = gastos_carro.sort_values('monto', ascending=False)
            st.dataframe(gastos_carro, use_container_width=True)
            st.bar_chart(data=gastos_carro.set_index('placa'))
            
        with col2:
            st.markdown("#### Gastos por Fechas")
            df_inicio['fecha'] = pd.to_datetime(df_inicio['fecha']).dt.date
            gastos_fecha = df_inicio.groupby('fecha')['monto'].sum().reset_index()
            st.dataframe(gastos_fecha, use_container_width=True)
            st.line_chart(data=gastos_fecha.set_index('fecha'))
    else:
        st.info("Aún no hay registros de gastos para generar este análisis.")

# --- 🚚 VEHÍCULOS ---
elif menu == "🚚 Gestión de Vehículos":
    t_reg, t_edit, t_ver = st.tabs(["➕ Registrar", "✏️ Editar", "🔍 Ver Flota"])
    
    with t_reg:
        with st.form("reg_vehiculo"):
            c1, c2 = st.columns(2)
            placa = c1.text_input("Placa").upper()
            marca = c1.text_input("Marca")
            modelo = c1.text_input("Modelo")
            cond = c2.text_input("Conductor")
            tipo = c2.selectbox("Tipo", ["Ambulancia", "Van", "Particular", "Microbús"])
            km = c2.number_input("KM Inicial", min_value=0)
            if st.form_submit_button("Guardar Vehículo"):
                conn = conectar_db(); cur = conn.cursor()
                cur.execute("INSERT INTO vehiculos (placa, marca, modelo, tipo, conductor, km_actual) VALUES (%s,%s,%s,%s,%s,%s)", (placa, marca, modelo, tipo, cond, km))
                conn.commit(); conn.close()
                st.success("✅ Registrado con éxito"); st.rerun()

    with t_edit:
        conn = conectar_db()
        df_v = pd.read_sql("SELECT * FROM vehiculos", conn)
        conn.close()
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
                    conn.commit(); conn.close()
                    st.success("✅ Actualizado"); st.rerun()

    with t_ver:
        conn = conectar_db()
        st.dataframe(pd.read_sql("SELECT placa, marca, modelo, tipo, conductor, km_actual FROM vehiculos", conn), use_container_width=True)
        conn.close()

# --- 💸 GASTOS ---
elif menu == "💸 Registro de Gastos":
    conn = conectar_db()
    v_data = pd.read_sql("SELECT id, placa, km_actual FROM vehiculos", conn)
    
    # Extraer categorías existentes de la base de datos para que el sistema "aprenda"
    try:
        cat_data = pd.read_sql("SELECT DISTINCT tipo_gasto FROM gastos WHERE tipo_gasto IS NOT NULL", conn)
        categorias_existentes = cat_data['tipo_gasto'].dropna().tolist()
    except Exception:
        categorias_existentes = []
        
    categorias_base = ["Combustible", "Peaje", "Mantenimiento", "Seguro", "Otros"]
    
    # Unir las listas y eliminar duplicados
    lista_categorias = list(set(categorias_base + categorias_existentes))
    lista_categorias.sort()
    # Agregar la opción de crear una nueva al final
    lista_categorias.append("➕ Agregar nueva...")
    
    if not v_data.empty:
        with st.form("form_gasto"):
            st.subheader("Registrar Nuevo Gasto")
            c1, c2 = st.columns(2)
            with c1:
                v_sel = st.selectbox("Vehículo", v_data['placa'])
                v_id = int(v_data[v_data['placa'] == v_sel]['id'].values[0])
                
                # --- SISTEMA DINÁMICO DE CATEGORÍAS ---
                tipo_g_sel = st.selectbox("Categoría Principal", lista_categorias)
                if tipo_g_sel == "➕ Agregar nueva...":
                    tipo_g = st.text_input("Escribe la nueva categoría principal")
                else:
                    tipo_g = tipo_g_sel
                # --------------------------------------
                
                monto = st.number_input("Monto ($)", min_value=0.0)
                kilometraje = st.number_input("Kilometraje al momento del gasto", min_value=0)
                
            with c2:
                destino = st.text_input("Destino / Institución")
                fecha = st.date_input("Fecha", datetime.now().date())
                aplica_concepto = st.radio("¿Ingresar un concepto específico?", ["No", "Sí"])
                concepto_adicional = ""
                if aplica_concepto == "Sí":
                    concepto_adicional = st.text_input("Escribe el concepto")
            
            detalle = st.text_area("Detalles adicionales")
            
            if st.form_submit_button("Guardar Gasto"):
                # Evitar que se guarde una categoría en blanco
                if tipo_g_sel == "➕ Agregar nueva..." and tipo_g.strip() == "":
                    tipo_g = "Otros"
                    
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO gastos (vehiculo_id, tipo_gasto, monto, institucion_destino, fecha, detalle, kilometraje, aplica_concepto, concepto) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (v_id, tipo_g, monto, destino, fecha, detalle, kilometraje, aplica_concepto, concepto_adicional))
                cur.execute("UPDATE vehiculos SET km_actual = GREATEST(km_actual, %s) WHERE id = %s", (kilometraje, v_id))
                conn.commit(); st.success("✅ Gasto guardado correctamente"); st.rerun()
        
        st.markdown("---")
        st.subheader("Historial de Gastos")
        df_g = pd.read_sql("SELECT g.*, v.placa FROM gastos g JOIN vehiculos v ON g.vehiculo_id = v.id", conn)
        conn.close()
        
        if not df_g.empty:
            df_g['mes'] = pd.to_datetime(df_g['fecha']).dt.strftime('%Y-%m')
            mes_sel = st.selectbox("Filtrar por Mes", sorted(df_g['mes'].unique(), reverse=True))
            df_mostrar = df_g[df_g['mes'] == mes_sel][['fecha', 'placa', 'tipo_gasto', 'monto', 'kilometraje', 'concepto', 'institucion_destino']]
            st.dataframe(df_mostrar, use_container_width=True)
    else:
        st.warning("⚠️ Debes registrar al menos un vehículo primero.")
        conn.close()

# --- 🛠️ MANTENIMIENTOS ---
elif menu == "🛠️ Mantenimientos":
    conn = conectar_db()
    v_data = pd.read_sql("SELECT id, placa, km_actual FROM vehiculos", conn)
    
    if not v_data.empty:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("form_mant"):
                st.subheader("Programar Mantenimiento")
                v_sel = st.selectbox("Vehículo", v_data['placa'])
                v_id = int(v_data[v_data['placa'] == v_sel]['id'].values[0])
                desc = st.text_area("Descripción (Ej: Cambio de aceite, Frenos)")
                km_prox = st.number_input("Kilometraje para próximo cambio", min_value=0)
                if st.form_submit_button("Programar"):
                    cur = conn.cursor()
                    cur.execute("INSERT INTO mantenimientos (vehiculo_id, descripcion, km_proximo_cambio, estado) VALUES (%s, %s, %s, 'Pendiente')", (v_id, desc, km_prox))
                    conn.commit(); st.success("✅ Programado con éxito"); st.rerun()
        
        with c2:
            st.subheader("Estado de la Flota")
            st.dataframe(v_data[['placa', 'km_actual']], use_container_width=True)
            
        st.markdown("---")
        st.subheader("Mantenimientos Pendientes")
        df_m = pd.read_sql("SELECT m.id, v.placa, m.descripcion, m.km_proximo_cambio, m.estado FROM mantenimientos m JOIN vehiculos v ON m.vehiculo_id = v.id", conn)
        conn.close()
        
        if not df_m.empty:
            pendientes = df_m[df_m['estado'] == 'Pendiente']
            if not pendientes.empty:
                st.dataframe(pendientes[['placa', 'descripcion', 'km_proximo_cambio']], use_container_width=True)
                
                with st.form("actualizar_mant"):
                    mant_id = st.selectbox("Seleccione el ID del mantenimiento a cerrar", pendientes['id'])
                    if st.form_submit_button("Marcar como Realizado"):
                        conn = conectar_db(); cur = conn.cursor()
                        cur.execute("UPDATE mantenimientos SET estado = 'Realizado' WHERE id = %s", (int(mant_id),))
                        conn.commit(); conn.close()
                        st.success("✅ Mantenimiento cerrado"); st.rerun()
            else:
                st.info("No hay mantenimientos pendientes en este momento.")
    else:
        st.warning("⚠️ Registra un vehículo primero.")
        conn.close()

# --- 📊 REPORTES AVANZADOS ---
elif menu == "📊 Reportes Avanzados":
    conn = conectar_db()
    df_g = pd.read_sql("SELECT g.*, v.placa FROM gastos g JOIN vehiculos v ON g.vehiculo_id = v.id", conn)
    conn.close()
    
    st.subheader("Resumen General de Operaciones")
    if not df_g.empty:
        df_g['fecha'] = pd.to_datetime(df_g['fecha'])
        df_g['mes'] = df_g['fecha'].dt.strftime('%Y-%m')
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Gastos por Categoría")
            gastos_cat = df_g.groupby('tipo_gasto')['monto'].sum().reset_index()
            st.bar_chart(data=gastos_cat, x='tipo_gasto', y='monto')
            
        with c2:
            st.markdown("#### Gasto Total por Vehículo")
            gastos_vehiculo = df_g.groupby('placa')['monto'].sum().reset_index()
            st.bar_chart(data=gastos_vehiculo, x='placa', y='monto')
    else:
        st.info("No hay suficientes datos registrados para generar los reportes.")
