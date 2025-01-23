import streamlit as st
import pandas as pd

# --------------------------------------------------
# 1. Cargamos un DataFrame de prueba
# --------------------------------------------------
def load_sample_data():
    sample_data = {
      "pair": ["ETH/USDT", "BTC/USDT", "ETH/DAI", "AVAX/USDT", "SOL/USDC"],
      "volume": [1500000, 3000000, 500000, 2000000, 1000000],
      "tvl": [500000, 800000, 200000, 600000, 300000],
      "apr": [0.12, 0.15, 0.10, 0.20, 0.18]
    }
    return pd.DataFrame(sample_data)

# --------------------------------------------------
# 2. Detectar si el usuario pide un cálculo estadístico
# --------------------------------------------------
def detect_aggregation(user_query: str):
    """
    Retorna la operación de agregación que usará .agg() de pandas:
    - 'mean' si encuentra palabras como 'media', 'promedio'
    - 'max' si encuentra palabras como 'máximo', 'max'
    - 'min' si encuentra 'mínimo', 'min'
    - 'sum' si encuentra 'suma', 'sum'
    - 'count' si encuentra 'conteo', 'count'
    De lo contrario, retorna None.
    """
    lower_q = user_query.lower()
    if any(word in lower_q for word in ["media", "promedio", "mean"]):
        return "mean"
    elif any(word in lower_q for word in ["máximo", "maximo", "max"]):
        return "max"
    elif any(word in lower_q for word in ["mínimo", "minimo", "min"]):
        return "min"
    elif any(word in lower_q for word in ["suma", "sum"]):
        return "sum"
    elif any(word in lower_q for word in ["conteo", "count"]):
        return "count"
    return None

# --------------------------------------------------
# 3. Detectar tipo de gráfico (bar, line, area)
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
        # Pie/pastel no está soportado nativamente por Streamlit
        if "pastel" in lower_q or "pie" in lower_q:
            return "unsupported_pie"
        return "bar"  # Valor por defecto

# --------------------------------------------------
# 4. Detectar la métrica a usar (volume, tvl, apr)
# --------------------------------------------------
def detect_metric(user_query: str, df: pd.DataFrame) -> str:
    """
    Retorna la columna (col) que más se ajuste a la consulta.
    Por defecto, si no lo detecta, retorna la primera columna numérica.
    """
    lower_q = user_query.lower()
    numeric_cols = [c for c in df.columns if str(df[c].dtype).startswith(("float", "int"))]

    if "volume" in lower_q:
        return "volume" if "volume" in numeric_cols else numeric_cols[0]
    elif "tvl" in lower_q:
        return "tvl" if "tvl" in numeric_cols else numeric_cols[0]
    elif "apr" in lower_q:
        return "apr" if "apr" in numeric_cols else numeric_cols[0]
    else:
        # Si no se encontró nada específico, devolver la primera columna numérica
        return numeric_cols[0] if numeric_cols else None

# --------------------------------------------------
# 5. Función para graficar
# --------------------------------------------------
def plot_with_streamlit_builtin_charts(df: pd.DataFrame, chart_type: str, metric_col: str):
    """
    Emplea st.bar_chart, st.line_chart o st.area_chart (nativos de Streamlit).
    """
    if df.empty:
        st.warning("No hay datos para graficar.")
        return

    if metric_col not in df.columns:
        st.warning(f"No se encontró la métrica '{metric_col}' en el DataFrame.")
        st.dataframe(df)
        return

    # Ponemos 'pair' como índice para que aparezca en el eje X como categorías
    df_plot = df.set_index("pair")

    if chart_type == "bar":
        st.bar_chart(df_plot[[metric_col]])
    elif chart_type == "line":
        st.line_chart(df_plot[[metric_col]])
    elif chart_type == "area":
        st.area_chart(df_plot[[metric_col]])
    else:
        st.error("Tipo de gráfico no soportado (por ejemplo, pastel).")

# --------------------------------------------------
# 6. Interfaz principal
# --------------------------------------------------
def main():
    st.title("Ejemplo con cálculos estadísticos y gráficos nativos de Streamlit")

    df = load_sample_data()
    st.write("### DataFrame de prueba")
    st.dataframe(df)

    user_query = st.text_input(
        "Ejemplo: 'Muéstrame la media del volume' o 'Quiero un gráfico de barras con el tvl'",
        value="Muéstrame el máximo del volume"
    )

    if st.button("Ejecutar consulta"):
        if not user_query.strip():
            st.warning("Por favor ingresa una instrucción válida.")
            return

        # Detecta si se solicita agregación
        aggregator = detect_aggregation(user_query)

        # Detecta la métrica (columna)
        metric_col = detect_metric(user_query, df)

        if aggregator:
            # El usuario pidió un cálculo estadístico
            st.write(f"**Operación de agregación detectada:** {aggregator}")
            st.write(f"**Métrica:** {metric_col}")

            if metric_col in df.columns:
                result = df[metric_col].agg(aggregator)
                st.success(f"El resultado de {aggregator} para '{metric_col}' es: **{result}**")
            else:
                st.warning(f"La columna '{metric_col}' no existe en el DataFrame.")
                st.dataframe(df)
        else:
            # Si no hay agregación, interpretamos que quiere un gráfico
            chart_type = detect_chart_type(user_query)
            st.write(f"**Tipo de gráfico detectado:** {chart_type}")
            st.write(f"**Métrica:** {metric_col}")
            plot_with_streamlit_builtin_charts(df, chart_type, metric_col)

if __name__ == "__main__":
    main()

# Created/Modified files during execution:
print("app.py")
