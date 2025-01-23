import streamlit as st
import pandas as pd

# --------------------------------------------------
# 1. DataFrame local con datos ficticios
# --------------------------------------------------
def load_sample_data():
    sample_data = {
      "pair": ["ETH/USDT", "BTC/USDT", "ETH/DAI", "AVAX/USDT", "SOL/USDC"],
      "volume": [1500000, 3000000, 500000, 2000000, 1000000],
      "tvl": [500000, 800000, 200000, 600000, 300000],
      "apr": [0.12, 0.15, 0.10, 0.20, 0.18]
    }
    df = pd.DataFrame(sample_data)
    return df

# --------------------------------------------------
# 2. Función para detectar tipo de gráfico
#    (bar, line, area)
# --------------------------------------------------
def detect_chart_type(user_query: str) -> str:
    lower_q = user_query.lower()
    if "barras" in lower_q or "bar" in lower_q:
        return "bar"
    elif "línea" in lower_q or "line" in lower_q:
        return "line"
    elif "área" in lower_q or "area" in lower_q:
        return "area"
    else:
        # Si pide "pastel" diremos que no está soportado
        if "pastel" in lower_q or "pie" in lower_q:
            return "unsupported_pie"
        return "bar"  # Por defecto, bar

# --------------------------------------------------
# 3. Función para detectar la métrica (columna)
#    (volume, tvl, apr)
# --------------------------------------------------
def detect_metric(user_query: str, df: pd.DataFrame) -> str:
    lower_q = user_query.lower()
    numeric_cols = [c for c in df.columns if str(df[c].dtype).startswith(("float", "int"))]

    if "volume" in lower_q:
        return "volume" if "volume" in numeric_cols else numeric_cols[0]
    elif "tvl" in lower_q:
        return "tvl" if "tvl" in numeric_cols else numeric_cols[0]
    elif "apr" in lower_q:
        return "apr" if "apr" in numeric_cols else numeric_cols[0]
    else:
        return numeric_cols[0] if numeric_cols else None

# --------------------------------------------------
# 4. Crear el gráfico con las funciones nativas de Streamlit
# --------------------------------------------------
def plot_with_streamlit_builtin_charts(df: pd.DataFrame, chart_type: str, metric_col: str):
    """
    Usamos st.bar_chart, st.line_chart o st.area_chart sobre la métrica elegida.
    - La columna 'pair' se usará como índice para que se vea la comparación por par
      en el eje X (categorías).
    """
    if df.empty:
        st.warning("No hay datos para graficar.")
        return

    if metric_col not in df.columns:
        st.warning(f"No se encontró la métrica '{metric_col}' en el DataFrame.")
        st.dataframe(df)
        return

    # Configuramos 'pair' como índice para que no se grafique como una columna numérica
    df_plot = df.set_index("pair")

    # Chequeamos que la métrica existe y sea numérica
    if metric_col not in df_plot.columns:
        st.warning(f"La métrica '{metric_col}' no existe en df_plot.")
        st.dataframe(df_plot)
        return

    if chart_type == "bar":
        st.bar_chart(df_plot[[metric_col]])
    elif chart_type == "line":
        st.line_chart(df_plot[[metric_col]])
    elif chart_type == "area":
        st.area_chart(df_plot[[metric_col]])
    else:
        # No soportado (por ejemplo, "pastel")
        st.error("Gráfico de pastel (pie) no está soportado en Streamlit por defecto.")

# --------------------------------------------------
# 5. Interfaz principal de Streamlit
# --------------------------------------------------
def main():
    st.title("Ejemplo con gráficos nativos de Streamlit (sin Altair, sin APIs)")

    # Cargamos el DataFrame ficticio
    df = load_sample_data()

    st.write("**DataFrame de ejemplo:**")
    st.dataframe(df)

    # Campo de texto para la petición
    user_query = st.text_input(
        "Escribe tu petición: (Ej. 'Quiero un gráfico de barras con el volume')",
        value="Quiero un gráfico de barras con el volume"
    )

    if st.button("Generar gráfico"):
        if not user_query.strip():
            st.warning("Por favor ingresa una consulta válida")
            return

        # 1) Detectamos el tipo de gráfico
        chart_type = detect_chart_type(user_query)
        st.write(f"**Tipo de gráfico detectado:** {chart_type}")

        # 2) Detectamos la métrica
        metric_col = detect_metric(user_query, df)
        st.write(f"**Métrica detectada:** {metric_col}")

        # 3) Dibujamos con funciones nativas
        plot_with_streamlit_builtin_charts(df, chart_type, metric_col)

if __name__ == "__main__":
    main()

# Created/Modified files during execution:
print("app.py")
