import streamlit as st
import psycopg2
import pandas as pd
import hashlib
from datetime import datetime

# --- CONFIGURACIÓN DE CONEXIÓN ---
DB_URL = "postgresql://neondb_owner:npg_Hw6lhgzCrm0B@ep-winter-mud-aqkidkqi-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def conectar_db():
    return psycopg2.connect(DB_URL)

def inicializar_tablas():
    conn = conectar_db(); conn.autocommit = True; cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS vehiculos (id SERIAL PRIMARY KEY, placa TEXT UNIQUE, marca TEXT, modelo TEXT, tipo TEXT, conductor TEXT, km_actual INTEGER DEFAULT 0)')
    cur.execute('CREATE TABLE IF NOT EXISTS gastos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), tipo_gasto TEXT, monto NUMERIC, institucion_destino TEXT, fecha DATE, detalle TEXT, kilometraje INTEGER, aplica_concepto TEXT, concepto TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS mantenimientos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), descripcion TEXT, km_proximo_cambio INTEGER, estado TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)')
    cur.execute("INSERT INTO usuarios (usuario, password) VALUES ('admin', %s) ON CONFLICT DO NOTHING", (hashlib.sha256('Jacobo2026'.encode()).hexdigest(),))
    conn.close()

# --- LOGIN ---
st.set_page_config(page_title="Transporte Jacobo Pro", layout="wide", page_icon="🚐")
inicializar_tablas()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Login de Acceso")
    u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        conn = conectar_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario=%s AND password=%s", (u, hashlib.sha256(p.encode()).hexdigest()))
        if cur.fetchone(): st.session_state['logged_in'] = True; conn.close(); st.rerun()
        else: st.error("Credenciales incorrectas"); conn.close()
    st.stop()

# --- MENÚ ---
st.sidebar.title("👤 Panel de Control")
if st.sidebar.button("Cerrar Sesión"): st.session_state['logged_in'] = False; st.rerun()
menu = st.sidebar.radio("Navegación", ["🏠 Inicio", "🚚 Gestión de Vehículos", "💸 Registro de Gastos", "🛠️ Mantenimientos", "📊 Reportes Avanzados", "👤 Gestión de Usuarios"])

# --- LÓGICA DE VENTANAS ---
if menu == "🏠 Inicio":
    conn = conectar_db()
    st.subheader("Resumen y Análisis")
    df = pd.read_sql("SELECT g.fecha, v.placa, g.monto FROM gastos g JOIN vehiculos v ON g.vehiculo_id = v.id", conn)
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.bar_chart(df.groupby('placa')['monto'].sum())
        c2.line_chart(df.groupby('fecha')['monto'].sum())
    conn.close()

elif menu == "🚚 Gestión de Vehículos":
    with st.form("reg"):
        p = st.text_input("Placa").upper(); m = st.text_input("Marca"); c = st.text_input("Conductor")
        if st.form_submit_button("Guardar"):
            conn = conectar_db(); cur = conn.cursor()
            cur.execute("INSERT INTO vehiculos (placa, marca, conductor) VALUES (%s,%s,%s)", (p, m, c))
            conn.commit(); conn.close(); st.rerun()

elif menu == "💸 Registro de Gastos":
    conn = conectar_db()
    v_data = pd.read_sql("SELECT id, placa FROM vehiculos", conn)
    if not v_data.empty:
        with st.form("gasto"):
            v_sel = st.selectbox("Vehículo", v_data['placa'])
            v_id = int(v_data[v_data['placa'] == v_sel]['id'].values[0])
            monto = st.number_input("Monto", min_value=0.0)
            cats = ["Combustible", "Peaje", "Mantenimiento", "Seguro", "Otros", "➕ Agregar nueva..."]
            tipo_sel = st.selectbox("Categoría", cats)
            tipo = st.text_input("Escribe nueva") if tipo_sel == "➕ Agregar nueva..." else tipo_sel
            if st.form_submit_button("Guardar"):
                cur = conn.cursor()
                cur.execute("INSERT INTO gastos (vehiculo_id, tipo_gasto, monto, fecha) VALUES (%s,%s,%s,%s)", (v_id, tipo, monto, datetime.now()))
                conn.commit(); conn.close(); st.rerun()
    conn.close()

elif menu == "🛠️ Mantenimientos":
    conn = conectar_db()
    df_m = pd.read_sql("SELECT v.placa, m.descripcion, m.estado FROM mantenimientos m JOIN vehiculos v ON m.vehiculo_id = v.id", conn)
    st.dataframe(df_m)
    conn.close()

elif menu == "📊 Reportes Avanzados":
    st.write("Análisis de datos activo.")

elif menu == "👤 Gestión de Usuarios":
    st.subheader("Registrar nuevo usuario")
    with st.form("new_user"):
        u = st.text_input("Nuevo Usuario"); p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Crear"):
            conn = conectar_db(); cur = conn.cursor()
            cur.execute("INSERT INTO usuarios (usuario, password) VALUES (%s, %s)", (u, hashlib.sha256(p.encode()).hexdigest()))
            conn.commit(); conn.close(); st.rerun()
