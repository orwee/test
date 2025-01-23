
import streamlit as st
import pandas as pd
import altair as alt

# --------------------------------------------------
# 1. Cargamos un DataFrame de prueba, totalmente local
# --------------------------------------------------
def load_sample_data():
    """
    Crea un DataFrame ficticio con datos de liquidity pool pairs,
    incluyendo volume, tvl y apr.
    """
    sample_data = {
      "pair": ["ETH/USDT", "BTC/USDT", "ETH/DAI", "AVAX/USDT", "SOL/USDC"],
      "volume": [1500000, 3000000, 500000, 2000000, 1000000],
      "tvl": [500000, 800000, 200000, 600000, 300000],
      "apr": [0.12, 0.15, 0.10, 0.20, 0.18]
    }
    df = pd.DataFrame(sample_data)
    return df

# --------------------------------------------------
# 2. Detección sencilla del tipo de gráfico
# --------------------------------------------------
def detect_chart_type(user_query: str) -> str:
    """
    Identifica 'barras' / 'pastel' / 'línea' en la query.
    Devuelve 'bar', 'pie' o 'line' para usar en Altair.
    """
    lower_q = user_query.lower()
    if "barras" in lower_q or "bar" in lower_q:
        return "bar"
    elif "pastel" in lower_q or "pie" in lower_q:
        return "pie"
    elif "línea" in lower_q or "line" in lower_q:
        return "line"
    else:
        return "bar"  # Por defecto

# --------------------------------------------------
# 3. Detección de la métrica a graficar
# --------------------------------------------------
def detect_metric(user_query: str, df: pd.DataFrame) -> str:
    """
    Busca si el usuario menciona 'volume', 'tvl' o 'apr' en la query.
    Si no encuentra nada, elige la primera columna numérica por defecto.
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
        # Por defecto, la primera columna numérica
        return numeric_cols[0] if numeric_cols else None

# --------------------------------------------------
# 4. Función para generar el gráfico dinámico en Altair
# --------------------------------------------------
def plot_chart_dynamic(df: pd.DataFrame, chart_type: str, metric_col: str):
    """
    Crea el gráfico usando altair según 'chart_type'.
    EJE X: 'pair' (string), EJE Y: metric_col (número).
    """
    if df.empty:
        st.warning("No hay datos para graficar.")
        return

    # Validaciones mínimas
    if metric_col not in df.columns:
        st.warning(f"No se encontró la métrica '{metric_col}' en el DataFrame.")
        st.dataframe(df)
        return

    if "pair" not in df.columns:
        st.warning("No existe la columna 'pair' en el DataFrame.")
        st.dataframe(df)
        return

    # Construcción del chart base según el tipo
    if chart_type == "bar":
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("pair:N", sort="-y"),
            y=alt.Y(f"{metric_col}:Q"),
            tooltip=["pair", f"{metric_col}"]
        )
    elif chart_type == "pie":
        # Gráfico de pastel: se usa 'theta' y 'color'
        chart = alt.Chart(df).mark_arc().encode(
            theta=alt.Theta(f"{metric_col}:Q", stack=True),
            color=alt.Color("pair:N"),
            tooltip=["pair", f"{metric_col}"]
        )
    elif chart_type == "line":
        # Suele usarse para series temporales,
        # pero aquí lo forzamos con 'pair' como eje X
        chart = alt.Chart(df.reset_index()).mark_line().encode(
            x=alt.X("pair:N", sort=None),
            y=alt.Y(f"{metric_col}:Q"),
            tooltip=["pair", f"{metric_col}"]
        )
    else:
        # Por defecto, barras
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("pair:N", sort="-y"),
            y=alt.Y(f"{metric_col}:Q"),
            tooltip=["pair", f"{metric_col}"]
        )

    st.altair_chart(chart, use_container_width=True)

# --------------------------------------------------
# 5. Interfaz principal en Streamlit
# --------------------------------------------------
def main():
    st.title("Ejemplo local - Gráficos dinámicos según petición del usuario")

    # Cargamos el DataFrame ficticio
    df = load_sample_data()

    st.write("**DataFrame inicial (ficticio):**")
    st.dataframe(df)

    user_query = st.text_input(
        "¿Qué gráfico deseas? (ej: 'barras con el volume de cada par', 'gráfico de pastel con el TVL', etc.)",
        value="Muéstrame un gráfico de barras con el volumen de cada par"
    )

    if st.button("Generar gráfico"):
        if not user_query.strip():
            st.warning("Por favor, ingresa una consulta válida.")
            return

        # Detectar tipo de gráfico
        chart_type = detect_chart_type(user_query)
        st.write(f"**Tipo de gráfico detectado:** {chart_type}")

        # Detectar la métrica (columna a usar en Y)
        metric_col = detect_metric(user_query, df)
        st.write(f"**Métrica detectada:** {metric_col}")

        # Dibujar el gráfico
        plot_chart_dynamic(df, chart_type, metric_col)

if __name__ == "__main__":
    main()

# Created/Modified files during execution:
print("app.py")
