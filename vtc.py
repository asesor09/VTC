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
    
    cur.execute('''CREATE TABLE IF NOT EXISTS vehiculos (id SERIAL PRIMARY KEY, placa TEXT UNIQUE NOT NULL, marca TEXT, modelo TEXT, tipo TEXT, conductor TEXT, km_actual INTEGER DEFAULT 0)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS gastos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), tipo_gasto TEXT, monto NUMERIC, institucion_destino TEXT, fecha DATE, detalle TEXT, kilometraje INTEGER, aplica_concepto TEXT, concepto TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS mantenimientos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), descripcion TEXT, km_proximo_cambio INTEGER, estado TEXT DEFAULT 'Pendiente')''')
    cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nombre TEXT, usuario TEXT UNIQUE, clave TEXT, rol TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS configuracion (id SERIAL PRIMARY KEY, email_remitente TEXT, email_clave TEXT, email_destino TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS categorias_gastos (id SERIAL PRIMARY KEY, nombre TEXT UNIQUE NOT NULL)''')
    
    cur.execute("INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES ('Jacobo Admin', 'admin', 'Jacobo2026', 'admin') ON CONFLICT DO NOTHING")
    
    for cat in ["Combustible", "Peaje", "Mantenimiento", "Seguro", "Otros"]:
        cur.execute("INSERT INTO categorias_gastos (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (cat,))
    
    for col, tipo in [("kilometraje", "INTEGER"), ("aplica_concepto", "TEXT"), ("concepto", "TEXT"), ("detalle", "TEXT"), ("tipo_gasto", "TEXT")]:
        try: cur.execute(f"ALTER TABLE gastos ADD COLUMN {col} {tipo};")
        except Exception: pass
    conn.close()

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="Transporte Jacobo Pro", layout="wide", page_icon="🚐")

if 'db_ready' not in st.session_state:
    try:
        inicializar_tablas()
        st.session_state['db_ready'] = True
    except Exception as e:
        st.error(f"Error conectando a la base de datos. Detalle: {e}")
        st.stop()

# --- LOGIN ---
if 'u_rol' not in st.session_state: st.session_state['u_rol'] = None
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

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
                st.session_state['logged_in'] = True; st.session_state['u_rol'] = resultado[0]
                conn.close(); st.rerun()
            else:
                cur.execute("SELECT rol FROM usuarios WHERE usuario=%s AND clave=%s", (u, hashlib.sha256(p.encode()).hexdigest()))
                res_cifrado = cur.fetchone()
                if res_cifrado:
                    st.session_state['logged_in'] = True; st.session_state['u_rol'] = res_cifrado[0]
                    conn.close(); st.rerun()
                else:
                    st.sidebar.error("Usuario o contraseña incorrectos"); conn.close()
        except Exception as e:
            st.sidebar.error(f"Error de conexión: {e}")
    st.title("🚐 Sistema de Gestión de Transporte")
    st.warning("Por favor, ingrese sus credenciales en la barra lateral.")
    st.stop()

# --- MENÚ ---
st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({'logged_in': False, 'u_rol': None}))
st.title("🚐 Panel de Control - Acceso Global")

opc_menu = ["🏠 Inicio", "🚚 Gestión de Vehículos", "🏷️ Categorías", "💸 Registro de Gastos", "🛠️ Mantenimientos", "🔒 Config. Alertas"]
if st.session_state.u_rol == "admin": opc_menu.append("⚙️ Usuarios")
menu = st.sidebar.radio("Navegación", opc_menu)

# --- 🏠 INICIO ---
if menu == "🏠 Inicio":
    st.subheader("Resumen y Análisis General")
    conn = conectar_db()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Vehículos en Flota", pd.read_sql("SELECT COUNT(*) FROM vehiculos", conn).iloc[0,0])
    c2.metric("Total Inversión", f"${pd.read_sql('SELECT SUM(monto) FROM gastos', conn).iloc[0,0] or 0:,.2f}")
    c3.metric("Mantenimientos Pendientes", pd.read_sql("SELECT COUNT(*) FROM mantenimientos WHERE estado='Pendiente'", conn).iloc[0,0])
    
    st.markdown("---")
    st.subheader("📊 Análisis Interactivo de Gastos")
    df_inicio = pd.read_sql("SELECT g.fecha, v.placa, g.tipo_gasto, g.concepto, g.monto, g.institucion_destino, g.detalle, g.kilometraje FROM gastos g JOIN vehiculos v ON g.vehiculo_id = v.id", conn)
    conn.close()
    
    if not df_inicio.empty:
        df_inicio['fecha'] = pd.to_datetime(df_inicio['fecha']).dt.date
        f1, f2, f3 = st.columns(3)
        with f1:
            placas_unicas = df_inicio['placa'].unique().tolist()
            placas_sel = st.multiselect("Seleccionar Vehículo", placas_unicas, default=placas_unicas)
        with f2: fecha_inicio = st.date_input("Fecha Inicio", df_inicio['fecha'].min())
        with f3: fecha_fin = st.date_input("Fecha Fin", df_inicio['fecha'].max())
            
        mask = (df_inicio['placa'].isin(placas_sel)) & (df_inicio['fecha'] >= fecha_inicio) & (df_inicio['fecha'] <= fecha_fin)
        df_filtrado = df_inicio[mask]
        
        st.markdown("---")
        if not df_filtrado.empty:
            st.metric("Total Gastos Filtrados", f"${df_filtrado['monto'].sum():,.2f}")
            col1, col2 = st.columns(2)
            with col1: st.bar_chart(data=df_filtrado.groupby('placa')['monto'].sum().reset_index(), x='placa', y='monto')
            with col2: st.line_chart(data=df_filtrado.groupby('fecha')['monto'].sum().reset_index().set_index('fecha'))
                
            st.dataframe(df_filtrado, use_container_width=True)
            csv_data = df_filtrado.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button("📥 Descargar Excel", data=csv_data, file_name=f
