import streamlit as st
import pandas as pd
import psycopg2
import os
# 
st.set_page_config(
    layout="wide",
    page_title="Catálogo MUUA - Colección de Antropología"
)

st.title("🏛️ Catálogo MUUA - Colección de Antropología")


def get_db_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    return st.secrets["database"]["url"]


def query_db(sql, params=None):
    conn = psycopg2.connect(get_db_url())
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(rows, columns=cols)
    finally:
        conn.close()


@st.cache_data(ttl=3600)
def get_culturas():
    df = query_db(
        "SELECT DISTINCT cultura FROM museo_piezas "
        "WHERE cultura IS NOT NULL AND cultura <> '' "
        "ORDER BY cultura"
    )
    return df["cultura"].tolist()


@st.cache_data(ttl=3600)
def load_data(registro_filtro="", cultura_filtro=""):
    conditions = []
    params = []

    if registro_filtro:
        conditions.append("numero_de_registro = %s")
        params.append(registro_filtro)

    if cultura_filtro and cultura_filtro != "Todas":
        conditions.append("cultura = %s")
        params.append(cultura_filtro)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            numero_de_registro   AS "Número de Registro",
            fecha_ingreso_anio   AS "Año",
            denominacion_del_objeto AS "Denominación del Objeto",
            cultura              AS "Cultura",
            materiales           AS "Materiales",
            zona_arqueologica    AS "Zona Arqueológica",
            pais                 AS "País"
        FROM museo_piezas
        {where_clause}
        ORDER BY numero_de_registro
        LIMIT 200
    """

    return query_db(sql, params if params else None)


# ----------------------------
# IMÁGENES
# ----------------------------
def get_image(denominacion):
    denominacion = str(denominacion).lower()
    img_folder = "imagenes"
    if "vasija" in denominacion:
        return os.path.join(img_folder, "vasija.jpg")
    if "figura" in denominacion or "estatuilla" in denominacion:
        return os.path.join(img_folder, "figura.jpg")
    return os.path.join(img_folder, "default.jpg")


# ----------------------------
# FILTROS
# ----------------------------
registro = st.text_input("Buscar por Número de Registro:")

try:
    lista_culturas = ["Todas"] + get_culturas()
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

cultura_sel = st.selectbox("Filtrar por Cultura", lista_culturas)

# ----------------------------
# DATA
# ----------------------------
try:
    df_filtrado = load_data(
        registro_filtro=registro.strip(),
        cultura_filtro=cultura_sel,
    )
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

df_filtrado = df_filtrado.reset_index(drop=True)


# ----------------------------
# TABLA
# ----------------------------
st.subheader("Información del Objeto")

if not df_filtrado.empty:

    evento_seleccion = st.dataframe(
        df_filtrado[[
            "Número de Registro",
            "Año",
            "Denominación del Objeto",
            "Cultura",
            "Materiales",
        ]],
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="tabla_museo",
    )

    seleccion = evento_seleccion.selection.rows

    if seleccion:

        indice_fila = seleccion[0]
        datos_objeto = df_filtrado.iloc[indice_fila]

        st.divider()

        col1, col2 = st.columns([1, 2])

        with col1:
            img_path = get_image(datos_objeto["Denominación del Objeto"])
            if os.path.exists(img_path):
                st.image(
                    img_path,
                    caption=datos_objeto["Denominación del Objeto"],
                    use_column_width="always",
                )
            else:
                st.image(
                    "https://via.placeholder.com/300?text=Sin+Imagen",
                    use_column_width="always",
                )

        with col2:
            st.header(f"Ficha Técnica: {datos_objeto['Número de Registro']}")
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Denominación:** {datos_objeto['Denominación del Objeto']}")
                    st.write(f"**Cultura:** {datos_objeto['Cultura']}")
                    st.write(f"**Año:** {datos_objeto['Año']}")
                with c2:
                    st.write(f"**Materiales:** {datos_objeto['Materiales']}")
                    st.write(f"**Zona:** {datos_objeto['Zona Arqueológica']}")
                    st.write(f"**País:** {datos_objeto['País']}")

    else:
        st.info("💡 Haz clic en una fila para ver la ficha técnica.")

else:
    st.warning("No hay objetos que coincidan con los filtros.")
