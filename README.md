# Tablero de asteroides cercanos a la Tierra — NASA NeoWs

Emiliano Rivas de la Vega · IDIA-223 · 125053518
Herramientas de Visualización · Parcial III

Transformación a dashboard en Streamlit de la API de la evaluación,
la Práctica 12: NASA Open APIs — NeoWs (Near Earth Object Web Service),
endpoint Browse `https://api.nasa.gov/neo/rest/v1/neo/browse`.

## Qué hace

Las 4 gráficas estáticas de la Práctica 12 ahora son un tablero
interactivo, con filtros en el panel de la izquierda (peligrosidad,
tamaño y años), indicadores arriba y tablas de los 10 asteroides
más grandes y los 10 acercamientos más cercanos. También se puede
descargar en CSV justo los datos que se están viendo.

Datos: 15 páginas x 20 asteroides = 300 asteroides, 6 207 acercamientos
utilizables (265 asteroides con acercamiento).

## Cómo correrlo

```bash
pip install -r requirements.txt
streamlit run dashboard_nasa.py
```

Por defecto usa `respuesta.json`, la respuesta limpia de la Práctica 12
que ya viene en este repo, así que no gasta peticiones ni necesita llave.
Si el JSON no se puede subir a GitHub, sube `neows.csv` en su lugar:
trae los mismos 6 207 acercamientos ya limpios, pero pesa 0.9 MB
en vez de 4.7 MB, y el tablero lo lee igual.

Para consultar la API en vivo, elige esa opción en el panel y pon tu
llave en `.streamlit/secrets.toml` con la línea:
`NASA_API_KEY = "tu-llave"`
La llave se pide gratis en https://api.nasa.gov/ y nunca va en el código
ni se sube a GitHub.

## Archivos

- `dashboard_nasa.py` — el tablero en Streamlit
- `respuesta.json` — datos guardados de la Práctica 12 (sin token)
- `neows.csv` — los mismos datos en CSV, por si el JSON no sube
- `requirements.txt` — lo que hay que instalar
- `README.md` — este archivo