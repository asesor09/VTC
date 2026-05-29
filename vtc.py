import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE CONEXIÓN GLOBAL (NEON) ---
DB_URL = "postgresql://neondb_owner:npg_Hw6lhgzCrm0B@ep-winter-mud-aqkidkqi-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def conectar_db():
    return psycopg2.connect(DB_URL)

def inicializar_tablas():
    conn = conectar_db()
    conn.autocommit = True 
    cur = conn.cursor()
    
    # 1. Crear tabla de vehículos
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
    
    # 2. Crear tabla de gastos (con todos los campos originales y nuevos)
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
    
    # 3. Bloque de seguridad para añadir columnas sin borrar nada
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
            pass # Si la columna ya existe, simplemente continúa
            
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

# Inicializar base de datos
try:
    inicializar_tablas()
except Exception as e:
    st.sidebar.error(f"Error de conexión: {e}")

st.title("🚐 Panel de Control - Acceso Global")
# Menú limpio, sin la ventana de ventas
menu = st.sidebar.radio("Navegación", ["🏠 Inicio", "🚚 Gestión de Vehículos", "💸 Registro de Gastos"])

# --- 🏠 INICIO ---
if menu == "🏠 Inicio":
    conn = conectar_db()
    v = pd.read_sql("SELECT COUNT(*) FROM vehiculos", conn).iloc[0,0]
    g = pd.read_sql("SELECT SUM(monto) FROM gastos", conn).iloc[0,0] or 0
    conn.close()
    c1, c2 = st.columns(2)
    c1.metric("Vehículos en la Nube", v)
    c2.metric("Total Inversión", f"${g:,.2f}")

# --- 🚚 VEHÍCULOS ---
elif menu == "🚚 Gestión de Vehículos":
    t_reg, t_edit, t_ver = st.tabs(["➕ Registrar", "✏️ Editar", "🔍 Ver Flota"])
    
    with t_reg:
        with st.form("reg"):
            c1, c2 = st.columns(2)
            placa = c1.text_input("Placa").upper()
            marca = c1.text_input("Marca")
            modelo = c1.text_input("Modelo")
            cond = c2.text_input("Conductor")
            tipo = c2.selectbox("Tipo", ["Ambulancia", "Van", "Particular", "Microbús"])
            km = c2.number_input("KM Inicial", min_value=0)
            if st.form_submit_button("Guardar"):
                conn = conectar_db(); cur = conn.cursor()
                cur.execute("INSERT INTO vehiculos (placa, marca, modelo, tipo, conductor, km_actual) VALUES (%s,%s,%s,%s,%s,%s)", (placa, marca, modelo, tipo, cond, km))
                conn.commit(); conn.close()
                st.success("Registrado en la nube."); st.rerun()

    with t_edit:
        conn = conectar_db()
        df_v = pd.read_sql("SELECT * FROM vehiculos", conn)
        conn.close()
        if not df_v.empty:
            sel = st.selectbox("Elegir Placa", df_v['placa'])
            d = df_v[df_v['placa'] == sel].iloc[0]
            with st.form("edit"):
                n_cond = st.text_input("Conductor", value=d['conductor'])
                n_tipo = st.selectbox("Tipo", ["Ambulancia", "Van", "Particular", "Microbús"], index=["Ambulancia", "Van", "Particular", "Microbús"].index(d['tipo']))
                n_km = st.number_input("KM Actual", value=int(d['km_actual']))
                if st.form_submit_button("Actualizar"):
                    conn = conectar_db(); cur = conn.cursor()
                    cur.execute("UPDATE vehiculos SET conductor=%s, tipo=%s, km_actual=%s WHERE placa=%s", (n_cond, n_tipo, n_km, sel))
                    conn.commit(); conn.close()
                    st.success("Actualizado"); st.rerun()

    with t_ver:
        conn = conectar_db()
        st.dataframe(pd.read_sql("SELECT placa, marca, modelo, tipo, conductor, km_actual FROM vehiculos", conn), use_container_width=True)
        conn.close()

# --- 💸 GASTOS ---
elif menu == "💸 Registro de Gastos":
    conn = conectar_db()
    v_data = pd.read_sql("SELECT id, placa FROM vehiculos", conn)
    
    if not v_data.empty:
        with st.form("gasto_form"):
            st.subheader("Registrar Nuevo Gasto")
            
            c1, c2 = st.columns(2)
            with c1:
                v_sel = st.selectbox("Vehículo", v_data['placa'])
                v_id = int(v_data[v_data['placa'] == v_sel]['id'].values[0])
                # Restaurado el campo original que te había quitado
                tipo_g = st.selectbox("Categoría Principal", ["Combustible", "Peaje", "Mantenimiento", "Seguro", "Otros"])
                monto = st.number_input("Monto ($)", min_value=0.0)
                kilometraje = st.number_input("Kilometraje actual", min_value=0)
                
            with c2:
                destino = st.text_input("Destino / Institución")
                fecha = st.date_input("Fecha", datetime.now().date())
                
                # Nuevos campos solicitados: Selector Sí/No y el campo condicionado
                aplica_concepto = st.radio("¿Ingresar un concepto específico?", ["No", "Sí"])
                concepto_adicional = ""
                if aplica_concepto == "Sí":
                    concepto_adicional = st.text_input("Escribe el concepto")
            
            # Restaurado el campo de detalle
            detalle = st.text_area("Detalles adicionales")
            
            if st.form_submit_button("Guardar Gasto"):
                cur = conn.cursor()
                # Insertando todos los campos requeridos
                cur.execute("""
                    INSERT INTO gastos (vehiculo_id, tipo_gasto, monto, institucion_destino, fecha, detalle, kilometraje, aplica_concepto, concepto) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (v_id, tipo_g, monto, destino, fecha, detalle, kilometraje, aplica_concepto, concepto_adicional))
                
                # Actualizar kilometraje del vehículo si el ingresado es mayor
                cur.execute("UPDATE vehiculos SET km_actual = GREATEST(km_actual, %s) WHERE id = %s", (kilometraje, v_id))
                
                conn.commit(); st.success("✅ Gasto guardado correctamente"); st.rerun()
        
        st.markdown("---")
        st.subheader("Historial de Gastos Mensual")
        df_g = pd.read_sql("SELECT g.*, v.placa FROM gastos g JOIN vehiculos v ON g.vehiculo_id = v.id", conn)
        conn.close()
        
        if not df_g.empty:
            df_g['mes'] = pd.to_datetime(df_g['fecha']).dt.strftime('%Y-%m')
            mes_sel = st.selectbox("Ver Mes", sorted(df_g['mes'].unique(), reverse=True))
            
            df_mostrar = df_g[df_g['mes'] == mes_sel][['fecha', 'placa', 'tipo_gasto', 'monto', 'kilometraje', 'aplica_concepto', 'concepto', 'institucion_destino', 'detalle']]
            st.dataframe(df_mostrar, use_container_width=True)
    else:
        st.warning("⚠️ No hay vehículos registrados en la nube. Por favor, ve a la pestaña '🚚 Gestión de Vehículos' y registra al menos uno.")
        conn.close()
