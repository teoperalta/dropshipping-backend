import pandas as pd
import requests
import streamlit as st

URL_BASE = "http://127.0.0.1:8000"
TIMEOUT = 10

st.set_page_config(page_title="Dashboard Dropshipping", layout="wide")

st.title("Dashboard Dropshipping")
st.divider()

st.subheader("Resumen Financiero")

try:
    respuesta_stats = requests.get(f"{URL_BASE}/estadisticas", timeout=TIMEOUT)
    respuesta_stats.raise_for_status()
    stats = respuesta_stats.json()

    ingresos_totales: float = float(stats.get("ingresos_totales", 0.0))
    articulos_vendidos: int = int(stats.get("articulos_vendidos", 0))

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="💰 Ingresos Totales",
            value=f"${ingresos_totales:,.2f}",
        )

    with col2:
        st.metric(
            label="📦 Artículos Vendidos",
            value=f"{articulos_vendidos:,}",
        )

except requests.exceptions.ConnectionError:
    st.error("No se pudo conectar a la API. ¿Está el servidor activo en `http://127.0.0.1:8000`?")
except requests.exceptions.Timeout:
    st.error("La petición a `/estadisticas` agotó el tiempo de espera.")
except requests.exceptions.HTTPError as exc:
    st.error(f"Error HTTP {exc.response.status_code} al obtener estadísticas: {exc.response.text[:300]}")
except requests.exceptions.RequestException as exc:
    st.error(f"Error inesperado al obtener estadísticas: {exc}")

st.divider()

st.subheader("Inventario por Producto")

try:
    respuesta_productos = requests.get(f"{URL_BASE}/productos", timeout=TIMEOUT)
    respuesta_productos.raise_for_status()
    productos_json = respuesta_productos.json()

    if not productos_json:
        st.info("No hay productos registrados en el catálogo.")
    else:
        df = pd.DataFrame(productos_json)

        df_chart = df.set_index("titulo")[["inventario"]]

        st.bar_chart(
            df_chart,
            y="inventario",
            color="#4F8BF9",
            use_container_width=True,
        )

        st.divider()
        st.subheader("Catálogo Completo")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", format="%d"),
                "titulo": st.column_config.TextColumn("Título"),
                "descripcion": st.column_config.TextColumn("Descripción", width="large"),
                "precio": st.column_config.NumberColumn("Precio", format="$%.2f"),
                "precio_comparacion": st.column_config.NumberColumn("Precio Comparación", format="$%.2f"),
                "inventario": st.column_config.ProgressColumn(
                    "Inventario",
                    min_value=0,
                    max_value=int(df["inventario"].max()) if not df.empty else 100,
                    format="%d uds.",
                ),
            },
        )

except requests.exceptions.ConnectionError:
    st.error("No se pudo conectar a la API para obtener los productos.")
except requests.exceptions.Timeout:
    st.error("La petición a `/productos` agotó el tiempo de espera.")
except requests.exceptions.HTTPError as exc:
    st.error(f"Error HTTP {exc.response.status_code} al obtener productos: {exc.response.text[:300]}")
except requests.exceptions.RequestException as exc:
    st.error(f"Error inesperado al obtener productos: {exc}")
except (KeyError, ValueError) as exc:
    st.error(f"Error al procesar los datos de productos: {exc}")