import streamlit as st
import psycopg2
import pandas as pd
import hashlib
from datetime import datetime

# --- CONFIGURACIÓN ---
DB_URL = "postgresql://neondb_owner:npg_Hw6lhgzCrm0B@ep-winter-mud-aqkidkqi-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def conectar_db():
    return psycopg2.connect(DB_URL)

def inicializar_tablas():
    conn = conectar_db()
    conn.autocommit = True 
    cur = conn.cursor()
    # Crear tablas
    cur.execute('CREATE TABLE IF NOT EXISTS vehiculos (id SERIAL PRIMARY KEY, placa TEXT UNIQUE, marca TEXT, modelo TEXT, tipo TEXT, conductor TEXT, km_actual INTEGER DEFAULT 0)')
    cur.execute('CREATE TABLE IF NOT EXISTS gastos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), tipo_gasto TEXT, monto NUMERIC, institucion_destino TEXT, fecha DATE, detalle TEXT, kilometraje INTEGER, aplica_concepto TEXT, concepto TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS mantenimientos (id SERIAL PRIMARY KEY, vehiculo_id INTEGER REFERENCES vehiculos(id), descripcion TEXT, km_proximo_cambio INTEGER, estado TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)')
    # Crear admin inicial
    cur.execute("INSERT INTO usuarios (usuario, password) VALUES ('admin', %s) ON CONFLICT DO NOTHING", (hashlib.sha256('Jacobo2026'.encode()).hexdigest(),))
    conn.close()

# --- INICIO DE APLICACIÓN ---
st.set_page_config(page_title="Transporte Jacobo Pro", layout="wide", page_icon="🚐")
inicializar_tablas() # Inicializar siempre al cargar

# Control de Sesión
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Login de Acceso")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        conn = conectar_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario=%s AND password=%s", (u, hashlib.sha256(p.encode()).hexdigest()))
        if cur.fetchone():
            st.session_state['logged_in'] = True
            conn.close(); st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
            conn.close()
    st.stop()

# --- MENÚ PRINCIPAL ---
st.sidebar.title(f"👤 Admin")
if st.sidebar.button("Cerrar Sesión"): st.session_state['logged_in'] = False; st.rerun()
menu = st.sidebar.radio("Navegación", ["🏠 Inicio", "🚚 Vehículos", "💸 Gastos", "🛠️ Mantenimientos", "👤 Usuarios"])

# --- (AQUÍ PEGA TU LÓGICA DE VENTANAS: INICIO, VEHÍCULOS, GASTOS, MANTENIMIENTOS Y USUARIOS) ---
# He dejado el bloque de Usuarios abajo para que lo puedas completar:
if menu == "👤 Usuarios":
    st.subheader("Registrar nuevo usuario")
    with st.form("new_user"):
        n_user = st.text_input("Nuevo Usuario")
        n_pass = st.text_input("Nueva Contraseña", type="password")
        if st.form_submit_button("Guardar"):
            conn = conectar_db(); cur = conn.cursor()
            cur.execute("INSERT INTO usuarios (usuario, password) VALUES (%s, %s)", (n_user, hashlib.sha256(n_pass.encode()).hexdigest()))
            conn.commit(); conn.close(); st.success("Creado"); st.rerun()
