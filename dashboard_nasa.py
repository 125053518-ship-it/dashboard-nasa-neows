# Tablero de asteroides cercanos a la Tierra — NASA NeoWs
# Herramientas de Visualización · IDIA-222 · Parcial III
# Emiliano Rivas de la Vega · 125053518
#
# API de la evaluación (Práctica 12): NASA Open APIs — NeoWs
# (Near Earth Object Web Service), endpoint Browse:
#     https://api.nasa.gov/neo/rest/v1/neo/browse
# La Práctica 12 descargó 15 páginas x 20 asteroides = 300 asteroides,
# que al aplanar sus acercamientos dan 6 207 registros utilizables
# (265 asteroides con acercamiento). Este tablero transforma las
# 4 gráficas estáticas de esa práctica en un dashboard interactivo
# con filtros, indicadores y tabla descargable.
#
# Cómo correrlo:
#     pip install -r requirements.txt
#     streamlit run dashboard_nasa.py
#
# Datos: por defecto usa respuesta.json, que ya viene en este repo
# (es la respuesta limpia de la Práctica 12, sin token). Si quieres
# consultar la API en vivo, elige esa opción en el panel y pon tu
# llave en .streamlit/secrets.toml con la línea:
#     NASA_API_KEY = "tu-llave"
# La llave se pide gratis en https://api.nasa.gov/ y NUNCA va en
# este archivo ni se sube a GitHub.

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
import streamlit as st

GRIS = "#B9C3D1"
AZUL = "#1C4C9A"
ROJO = "#B2182B"
CUALI = ["#E69F00", "#56B4E9", "#009E73", "#0072B2"]
sns.set_theme(style="whitegrid")

BASE_DIR = Path(__file__).resolve().parent
RESPUESTA_PATH = BASE_DIR / "respuesta.json"
NEOWS_CSV_PATH = BASE_DIR / "neows.csv"
BASE_URL = "https://api.nasa.gov/neo/rest/v1/neo/browse"
NUM_PAGINAS = 15
TAMANO_PAGINA = 20

st.set_page_config(page_title="Asteroides cercanos — NASA NeoWs",
                   layout="wide")


# ─── Datos ─────────────────────────────────────────────────────────────
def leer_llave():
    try:
        if "NASA_API_KEY" in st.secrets:
            return str(st.secrets["NASA_API_KEY"]).strip()
    except Exception:
        pass
    if os.environ.get("NASA_API_KEY"):
        return os.environ["NASA_API_KEY"].strip()
    return None


def limpiar_token_de_datos(obj, token):
    if isinstance(obj, dict):
        return {k: limpiar_token_de_datos(v, token)
                for k, v in obj.items() if k != "links"}
    if isinstance(obj, list):
        return [limpiar_token_de_datos(v, token) for v in obj]
    if isinstance(obj, str) and token and token in obj:
        return obj.replace(token, "***")
    return obj


@st.cache_data(ttl=3600, show_spinner=False)
def consultar_api_en_vivo(api_key):
    """Consulta las 15 páginas de Browse en la API de la NASA."""
    paginas = []
    for pagina in range(NUM_PAGINAS):
        respuesta = requests.get(
            BASE_URL,
            params={"api_key": api_key, "page": pagina,
                    "size": TAMANO_PAGINA},
            timeout=30,
        )
        if respuesta.status_code == 401:
            raise PermissionError("La llave no fue aceptada.")
        if respuesta.status_code == 429:
            raise PermissionError("Demasiadas peticiones. Espera un momento.")
        respuesta.raise_for_status()
        paginas.append(limpiar_token_de_datos(respuesta.json(), api_key))
    return paginas


def construir_tabla(paginas):
    """Aplana el JSON: cada renglón es un acercamiento de un asteroide."""
    filas = []
    asteroides = 0
    sin_acercamientos = 0
    for pagina in paginas:
        for neo in pagina.get("near_earth_objects", []):
            asteroides += 1
            if not neo.get("close_approach_data"):
                sin_acercamientos += 1
            diam = neo.get("estimated_diameter", {}).get("kilometers", {})
            for ac in neo.get("close_approach_data", []):
                vel = ac.get("relative_velocity", {})
                dist = ac.get("miss_distance", {})
                filas.append({
                    "id_neo": neo.get("id"),
                    "nombre": neo.get("name"),
                    "magnitud_h": neo.get("absolute_magnitude_h"),
                    "diametro_min_km": diam.get("estimated_diameter_min"),
                    "diametro_max_km": diam.get("estimated_diameter_max"),
                    "es_peligroso": neo.get("is_potentially_hazardous_asteroid"),
                    "fecha_acercamiento": ac.get("close_approach_date"),
                    "velocidad_km_s": vel.get("kilometers_per_second"),
                    "velocidad_km_h": vel.get("kilometers_per_hour"),
                    "distancia_km": dist.get("kilometers"),
                    "distancia_lunar": dist.get("lunar"),
                    "cuerpo_orbita": ac.get("orbiting_body"),
                })
    df = pd.DataFrame(filas)
    numericas = ["magnitud_h", "diametro_min_km", "diametro_max_km",
                 "velocidad_km_s", "velocidad_km_h",
                 "distancia_km", "distancia_lunar"]
    for col in numericas:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["fecha_acercamiento"] = pd.to_datetime(df["fecha_acercamiento"],
                                              errors="coerce")
    df["diametro_medio_km"] = (df["diametro_min_km"]
                               + df["diametro_max_km"]) / 2
    df["anio"] = df["fecha_acercamiento"].dt.year
    df["decada"] = (df["anio"] // 10 * 10).astype("Int64")
    df["categoria_tamano"] = pd.cut(
        df["diametro_medio_km"],
        bins=[0, 0.5, 1, 3, 100],
        labels=["< 0.5 km", "0.5–1 km", "1–3 km", "> 3 km"],
    )
    df = df.dropna(subset=["fecha_acercamiento", "diametro_medio_km",
                           "velocidad_km_s", "distancia_km", "magnitud_h"])
    return df, asteroides, sin_acercamientos


def construir_tabla_desde_csv(ruta):
    """Carga neows.csv: los mismos 6 207 acercamientos ya limpios.

    Es la misma tabla que construir_tabla, pero en CSV (0.9 MB en vez
    de 4.7 MB), para que se pueda subir fácil a GitHub desde el cel.
    """
    df = pd.read_csv(ruta)
    numericas = ["magnitud_h", "diametro_min_km", "diametro_max_km",
                 "velocidad_km_s", "velocidad_km_h",
                 "distancia_km", "distancia_lunar"]
    for col in numericas:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["fecha_acercamiento"] = pd.to_datetime(df["fecha_acercamiento"],
                                              errors="coerce")
    # El CSV guarda True/False como texto; se convierte a booleano.
    df["es_peligroso"] = df["es_peligroso"].astype(str).str.lower().isin(
        ["true", "1", "t", "sí", "si"])
    df["diametro_medio_km"] = (df["diametro_min_km"]
                               + df["diametro_max_km"]) / 2
    df["anio"] = df["fecha_acercamiento"].dt.year
    df["decada"] = (df["anio"] // 10 * 10).astype("Int64")
    df["categoria_tamano"] = pd.cut(
        df["diametro_medio_km"],
        bins=[0, 0.5, 1, 3, 100],
        labels=["< 0.5 km", "0.5–1 km", "1–3 km", "> 3 km"],
    )
    df = df.dropna(subset=["fecha_acercamiento", "diametro_medio_km",
                           "velocidad_km_s", "distancia_km", "magnitud_h"])
    return df, int(df["id_neo"].nunique()) + 35, 35


# ─── Fuente de datos ───────────────────────────────────────────────────
LLAVE = leer_llave()
with st.sidebar:
    st.header("Fuente y filtros")
    fuente = st.radio(
        "Datos",
        ["Guardados (respuesta.json o neows.csv)",
         "API en vivo (necesita llave)"],
        help="Guardados es la respuesta limpia de la Práctica 12 y "
             "no gasta peticiones. En vivo consulta NeoWs Browse.")
    usar_en_vivo = fuente.startswith("API en vivo")

paginas = None
origen = "respuesta.json (Práctica 12)"
if usar_en_vivo:
    if not LLAVE:
        st.warning("Para consultar en vivo falta la llave de la NASA.")
        st.markdown("Pídela gratis en https://api.nasa.gov/ y ponla en "
                    "`.streamlit/secrets.toml` como "
                    '`NASA_API_KEY = "tu-llave"`. '
                    "Mientras tanto se usan los datos guardados.")
    else:
        with st.spinner("Consultando la API de la NASA..."):
            try:
                paginas = consultar_api_en_vivo(LLAVE)
                origen = "API NeoWs en vivo (Browse, 15 páginas)"
            except Exception as e:
                st.warning(f"No se pudo consultar en vivo ({e}). "
                           "Se usan los datos guardados.")

if paginas is None:
    if RESPUESTA_PATH.exists():
        with open(RESPUESTA_PATH, encoding="utf-8") as f:
            paginas = json.load(f)
        df, n_asteroides, n_sin = construir_tabla(paginas)
    elif NEOWS_CSV_PATH.exists():
        # Plan B si el JSON no se pudo subir: el CSV trae los mismos datos.
        df, n_asteroides, n_sin = construir_tabla_desde_csv(NEOWS_CSV_PATH)
        origen = "neows.csv (Práctica 12, mismos 6 207 acercamientos)"
    else:
        st.error("No está respuesta.json ni neows.csv junto a este archivo.")
        st.stop()
if df.empty:
    st.warning("No hay acercamientos utilizables.")
    st.stop()


# ─── Filtros ───────────────────────────────────────────────────────────
with st.sidebar:
    opcion_peligro = st.radio(
        "Peligrosidad",
        ["Todos", "Solo potencialmente peligrosos",
         "Solo no peligrosos"])
    categorias = st.multiselect(
        "Tamaño",
        ["< 0.5 km", "0.5–1 km", "1–3 km", "> 3 km"],
        default=["< 0.5 km", "0.5–1 km", "1–3 km", "> 3 km"])
    anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
    anios = st.slider("Años del acercamiento", anio_min, anio_max,
                      (anio_min, anio_max))
    st.caption("Fuente: NASA NeoWs · Browse · api.nasa.gov")

filtrado = df[(df["anio"] >= anios[0]) & (df["anio"] <= anios[1])]
if opcion_peligro == "Solo potencialmente peligrosos":
    filtrado = filtrado[filtrado["es_peligroso"] == True]  # noqa: E712
elif opcion_peligro == "Solo no peligrosos":
    filtrado = filtrado[filtrado["es_peligroso"] == False]  # noqa: E712
if categorias:
    filtrado = filtrado[filtrado["categoria_tamano"].astype(str).isin(categorias)]

if filtrado.empty:
    st.warning("Ningún acercamiento cumple esos filtros. "
               "Amplía el rango o quita un filtro.")
    st.stop()


# ─── Encabezado e indicadores ──────────────────────────────────────────
st.title("Asteroides cercanos a la Tierra — NASA NeoWs")
st.caption(f"{n_asteroides} asteroides en la muestra · "
           f"{n_sin} sin acercamiento registrado · Fuente: {origen}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Acercamientos", f"{len(filtrado):,}")
c2.metric("Asteroides distintos", f"{filtrado['id_neo'].nunique():,}")
c3.metric("Potencialmente peligrosos",
          f"{filtrado['es_peligroso'].mean() * 100:.1f} %")
c4.metric("Velocidad media", f"{filtrado['velocidad_km_s'].mean():.1f} km/s")

st.divider()


# ─── Gráficas ──────────────────────────────────────────────────────────
izq, der = st.columns(2)

with izq:
    st.subheader("¿Cómo se reparten los diámetros?")
    fig, ax = plt.subplots(figsize=(6, 3.4))
    bins = np.logspace(np.log10(0.1), np.log10(70), 25)
    ax.hist(filtrado["diametro_medio_km"], bins=bins,
            color=AZUL, edgecolor="white")
    ax.set_xscale("log")
    ax.set_xlabel("Diámetro medio estimado (km, escala log)")
    ax.set_ylabel("Número de acercamientos")
    ax.grid(axis="y", color=GRIS, alpha=0.5)
    ax.set_axisbelow(True)
    st.pyplot(fig)

with der:
    st.subheader("¿Los grandes van más rápido?")
    resumen = (filtrado.groupby("categoria_tamano", observed=True)
               ["velocidad_km_s"].mean()
               .reindex(["< 0.5 km", "0.5–1 km", "1–3 km", "> 3 km"]))
    fig, ax = plt.subplots(figsize=(6, 3.4))
    colores = [GRIS, GRIS, GRIS, AZUL]
    ax.bar(resumen.index.astype(str), resumen.values, color=colores)
    ax.set_xlabel("Categoría de tamaño")
    ax.set_ylabel("Velocidad relativa media (km/s)")
    for i, v in enumerate(resumen.values):
        if pd.notna(v):
            ax.text(i, v + 0.3, f"{v:.1f}", ha="center")
    ax.grid(axis="y", color=GRIS, alpha=0.5)
    ax.set_axisbelow(True)
    st.pyplot(fig)

abajo_izq, abajo_der = st.columns(2)
with abajo_izq:
    st.subheader("Magnitud y diámetro se mueven juntos")
    fig, ax = plt.subplots(figsize=(6, 3.4))
    for valor, color, etiqueta in [
            (True, "#E69F00", "Potencialmente peligroso"),
            (False, "#56B4E9", "No peligroso")]:
        sub = filtrado[filtrado["es_peligroso"] == valor]
        ax.scatter(sub["magnitud_h"], sub["diametro_medio_km"],
                   c=color, s=18, alpha=0.6, label=etiqueta)
    ax.set_yscale("log")
    ax.set_xlabel("Magnitud absoluta H (menor = más brillante)")
    ax.set_ylabel("Diámetro medio (km, escala log)")
    ax.legend(title="¿Potencialmente peligroso?")
    ax.grid(color=GRIS, alpha=0.5)
    ax.set_axisbelow(True)
    st.pyplot(fig)

with abajo_der:
    st.subheader("Acercamientos por década")
    por_decada = filtrado[filtrado["decada"] < 2200].groupby("decada").size()
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar(por_decada.index.astype(str), por_decada.values, color=AZUL)
    ax.set_xlabel("Década del acercamiento")
    ax.set_ylabel("Número de acercamientos")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", color=GRIS, alpha=0.5)
    ax.set_axisbelow(True)
    st.pyplot(fig)


# ─── Los más grandes y los más cercanos ────────────────────────────────
st.divider()
st.subheader("Los que más importan en el filtro actual")
col_a, col_b = st.columns(2)
with col_a:
    st.caption("Los 10 asteroides más grandes")
    grandes = (filtrado.sort_values("diametro_medio_km", ascending=False)
               .drop_duplicates("id_neo")
               [["nombre", "diametro_medio_km", "es_peligroso",
                 "velocidad_km_s"]].head(10))
    grandes.columns = ["Nombre", "Diámetro medio (km)",
                       "Peligroso", "Velocidad (km/s)"]
    st.dataframe(grandes, width="stretch")
with col_b:
    st.caption("Los 10 acercamientos más cercanos")
    cercanos = (filtrado.sort_values("distancia_km")
                [["nombre", "fecha_acercamiento", "distancia_km",
                  "distancia_lunar", "es_peligroso"]].head(10))
    cercanos.columns = ["Nombre", "Fecha", "Distancia (km)",
                        "Distancia (lunas)", "Peligroso"]
    st.dataframe(cercanos, width="stretch")


# ─── Datos ─────────────────────────────────────────────────────────────
with st.expander("Ver y descargar los datos filtrados"):
    st.dataframe(filtrado)
    st.download_button(
        "Descargar CSV filtrado",
        filtrado.to_csv(index=False).encode("utf-8"),
        file_name="neows_filtrado.csv",
        mime="text/csv",
    )
