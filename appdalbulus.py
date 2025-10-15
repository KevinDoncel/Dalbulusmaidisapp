import folium
from folium.plugins import LocateControl
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import numpy as np
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from matplotlib.colors import LinearSegmentedColormap

# ===========================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ===========================================
st.set_page_config(page_title="Monitoreo Dalbulus maidis", layout="wide")

# ===========================================
# ESTILOS RESPONSIVE
# ===========================================
st.markdown("""
<style>
body, html {
    margin: 0;
    padding: 0;
    font-family: 'Helvetica', sans-serif;
}
h1 {
    font-size: 2.2vw;
}
@media (max-width: 900px) {
    h1 { font-size: 5vw; text-align: center; }
    img { width: 80px !important; margin-bottom: 10px; }
}
p {
    font-size: 1vw;
}
@media (max-width: 900px) {
    p { font-size: 3.5vw; }
}
iframe {
    width: 100% !important;
    height: 75vh !important;
}
.leaflet-control-layers {
    z-index: 9999 !important;
    position: absolute !important;
    top: 10px !important;
    right: 10px !important;
}
.header-container {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    text-align: center;
}

/* 📱 Ajustes gráficos responsivos */
@media (max-width: 900px) {
    .stPlotlyChart, .stAltairChart, .stVegaLiteChart, .stpyplot, .stImage {
        width: 100% !important;
        height: auto !important;
        display: block !important;
        margin: 0 auto !important;
    }
    .stpyplot > div, .stImage > div {
        min-height: 250px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ===========================================
# ENCABEZADO CON LOGO Y TÍTULO
# ===========================================
st.markdown("""
<div class='header-container'>
    <img src='https://fenalce.co/wp-content/uploads/2021/10/Logo_Fenalce_N-FNC-FNL-FNS_1-1-1.png' width='120' style='margin-right:20px;'>
    <div>
        <h1 style='color:#2E7D32; margin-bottom:0;'>🌽 Monitoreo geoespacial y temporal<br><i>Dalbulus maidis</i></h1>
        <p style='color:gray; margin-top:5px;'>Herramienta digital para visualizar datos espacio-temporales del complejo del achaparramiento del maíz</p>
    </div>
</div>
<hr style='border:1px solid #ccc;'>
""", unsafe_allow_html=True)

# ===========================================
# SIDEBAR: DESCARGA DE FORMATO BASE
# ===========================================
with st.sidebar:
    st.header("📄 Formato de carga de datos")
    format_df = pd.DataFrame({
        "lat": [3.45, 3.46],
        "lon": [-76.53, -76.54],
        "date1": ["2025-10-01", "2025-10-01"],
        "value1": [3, 8],
        "date2": ["2025-10-08", "2025-10-08"],
        "value2": [5, 10],
    })
    csv_format = format_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar Formato CSV",
        data=csv_format,
        file_name="Formato_Monitoreo_Dalbulus.csv",
        mime="text/csv"
    )
    st.info("📂 Cargue su archivo CSV con columnas: lat, lon, dateN, valueN...")

# ===========================================
# SUBIR ARCHIVO CSV
# ===========================================
uploaded_file = st.file_uploader("📂 Seleccione el archivo CSV", type="csv")

# ===========================================
# MAPA BASE
# ===========================================
m = folium.Map(
    location=[3.45, -76.53],
    zoom_start=8,
    tiles="Esri.WorldImagery",
    attr="Tiles © Esri & Contributors"
)
LocateControl(auto_start=False, flyTo=True).add_to(m)

# ===========================================
# PROCESAMIENTO DE DATOS
# ===========================================
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    capas = [(f"date{i}", f"value{i}") for i in range(1, 10)
             if f"date{i}" in df.columns and f"value{i}" in df.columns]

    if not capas:
        st.error("⚠️ El CSV debe contener al menos una pareja de columnas: date1 y value1")
    else:

        def crear_capa(df, date_col, value_col, nombre_capa):
            layer = folium.FeatureGroup(name=nombre_capa, show=False)

            def color_por_valor(val):
                if val <= 1: return "blue"
                elif val <= 3: return "green"
                elif val == 4: return "yellow"
                elif val <= 6: return "orange"
                else: return "red"

            for _, row in df.iterrows():
                color = color_por_valor(row[value_col])
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=7,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.85,
                    popup=f"<b>📅 {row[date_col]}</b><br>Valor: {row[value_col]}" +
                          ("<br><b style='color:red;'>🚨 Nivel ≥ 7</b>" if row[value_col] >= 7 else "")
                ).add_to(layer)

            # Interpolación
            points = df[["lon", "lat"]].values
            values = df[value_col].values
            grid_lon = np.linspace(df["lon"].min(), df["lon"].max(), 200)
            grid_lat = np.linspace(df["lat"].min(), df["lat"].max(), 200)
            grid_x, grid_y = np.meshgrid(grid_lon, grid_lat)
            grid_z = griddata(points, values, (grid_x, grid_y), method="linear")

            colors = [
                (0.0, "blue"),
                (0.2, "green"),
                (0.4, "yellow"),
                (0.6, "orange"),
                (1.0, "red")
            ]
            cmap_custom = LinearSegmentedColormap.from_list("alerta", colors)

            fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
            ax.imshow(
                grid_z,
                extent=(df["lon"].min(), df["lon"].max(),
                        df["lat"].min(), df["lat"].max()),
                origin="lower",
                cmap=cmap_custom,
                alpha=0.6,
                vmin=0,
                vmax=10
            )
            ax.axis("off")

            buf = BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight",
                        pad_inches=0, transparent=True)
            plt.close(fig)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            img_url = f"data:image/png;base64,{b64}"

            bounds = [[df["lat"].min(), df["lon"].min()],
                      [df["lat"].max(), df["lon"].max()]]
            folium.raster_layers.ImageOverlay(
                image=img_url,
                bounds=bounds,
                opacity=0.6,
                name=f"Interpolación {nombre_capa}"
            ).add_to(layer)
            layer.add_to(m)

        for i, (date_col, value_col) in enumerate(capas, start=1):
            crear_capa(df, date_col, value_col, f"Capa {i} - {date_col}")

        folium.LayerControl(collapsed=False, position='topright').add_to(m)

        # ---------- GRÁFICO PROMEDIO TEMPORAL ----------
        melted = []
        for i, (date_col, value_col) in enumerate(capas, start=1):
            temp = df[["lat", "lon", date_col, value_col]].rename(
                columns={date_col: "date", value_col: "value"})
            melted.append(temp)

        df_plot = pd.concat(melted)
        df_plot["date"] = pd.to_datetime(df_plot["date"])
        df_mean = df_plot.groupby("date", as_index=False)["value"].mean()

        alerta = (df_mean["value"] >= 7).any()
        if alerta:
            st.markdown("""
            <div style='background-color:#ffcccc; color:#b71c1c; padding:10px; border-radius:8px; text-align:center; font-weight:bold;'>
            🚨 ALERTA: Se detectaron promedios iguales o superiores a 7 en una o más fechas
            </div>
            """, unsafe_allow_html=True)
            st.markdown(
                "[📲 Enviar alerta por WhatsApp](https://wa.me/?text=🚨+Alerta:+Riesgo+alto+de+achaparramiento+detectado+en+su+finca)",
                unsafe_allow_html=True
            )

        def color_promedio(val):
            if val <= 1: return "blue"
            elif val <= 3: return "green"
            elif val == 4: return "yellow"
            elif val <= 6: return "orange"
            else: return "red"

        colores = df_mean["value"].apply(color_promedio)
        st.markdown("<hr style='border:0.5px solid #ccc;'>",
                    unsafe_allow_html=True)
        st.subheader("📈 Evolución temporal promedio de los valores monitoreados")

        # Figura más equilibrada para todos los dispositivos
        fig, ax = plt.subplots(figsize=(8, 5))
        for i in range(len(df_mean) - 1):
            ax.plot(df_mean["date"].iloc[i:i+2], df_mean["value"].iloc[i:i+2],
                    color=colores.iloc[i], linewidth=4)
        ax.scatter(df_mean["date"], df_mean["value"],
                   c=colores, s=120, edgecolor="black")
        ax.set_xlabel("Fecha", fontsize=11)
        ax.set_ylabel("Promedio del valor monitoreado", fontsize=11)
        ax.set_title("Comportamiento temporal promedio",
                     fontsize=13, color="#2E7D32", pad=15)
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.set_ylim(0, 10)
        plt.xticks(rotation=90, fontsize=9)
        plt.yticks(fontsize=9)

        for x, y, c in zip(df_mean["date"], df_mean["value"], colores):
            ax.text(x, y + 0.25, f"{y:.1f}", ha="center",
                    va="bottom", fontsize=9, color=c, fontweight="bold")

        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=200)
        plt.close(fig)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        # Contenedor adaptable
        st.markdown(f"""
        <div style='text-align:center; width:100%; max-width:900px; margin:auto;'>
            <img src="data:image/png;base64,{b64}" style="width:100%; border-radius:12px; box-shadow:0 2px 6px rgba(0,0,0,0.2);">
        </div>
        """, unsafe_allow_html=True)

# ===========================================
# MOSTRAR MAPA
# ===========================================
st.markdown("<hr style='border:0.5px solid #ccc;'>", unsafe_allow_html=True)
st.subheader("🗺️ Mapa interactivo de monitoreo")
st_folium(m, width=None, height=600)

# ===========================================
# PIE DE PÁGINA
# ===========================================
st.markdown("""
<hr style='border:0.5px solid #ccc;'>
<p style='text-align:center; color:gray; font-size:13px;'>
Desarrollado por <b>Kevin Doncel Yela</b> — Equipo Técnico <b>FENALCE Regional Valle del Cauca 2025</b><br>
Agricultura Digital y Regenerativa
</p>
""", unsafe_allow_html=True)




