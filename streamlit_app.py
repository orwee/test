import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# Configuración inicial de la página
st.set_page_config(
    page_title="Solana DeFi Advisor",
    page_icon="🌟",
    layout="wide"
)

# Clases y funciones auxiliares
class PortfolioAnalyzer:
    def __init__(self):
        self.step_finance_api = "https://api.step.finance/v1/portfolio/"
        self.defillama_api = "https://yields.llama.fi/pools"

    def get_portfolio(self, wallet_address: str):
        """Obtiene el portfolio desde Step Finance"""
        try:
            response = requests.get(f"{self.step_finance_api}{wallet_address}")
            return response.json()
        except Exception as e:
            st.error(f"Error al obtener el portfolio: {str(e)}")
            return {}

    def get_defi_opportunities(self):
        """Obtiene oportunidades DeFi desde DeFiLlama"""
        try:
            response = requests.get(self.defillama_api)
            data = response.json()
            # Filtrar solo pools de Solana
            solana_pools = [
                pool for pool in data['data']
                if pool['chain'] == 'Solana'
            ]
            return solana_pools
        except Exception as e:
            st.error(f"Error al obtener oportunidades DeFi: {str(e)}")
            return []

def calculate_additional_gains(portfolio, opportunities, time_in_months=12):
    """Calcula las ganancias adicionales si se invierte en las oportunidades recomendadas"""
    results = []
    for token in portfolio.get('tokens', []):
        symbol = token['symbol']
        amount = token['amount']
        apy_current = 0  # APY actual (asumimos 0 si no hay posición activa)

        # Buscar la mejor oportunidad para este token
        best_opportunity = max(
            (op for op in opportunities if symbol in op['tokens']),
            key=lambda x: x['apy'],
            default=None
        )

        if best_opportunity:
            apy_recommended = best_opportunity['apy']
            protocol = best_opportunity['protocol']

            # Calcular ganancias adicionales
            current_gain = amount * ((1 + apy_current / 100) ** (time_in_months / 12) - 1)
            recommended_gain = amount * ((1 + apy_recommended / 100) ** (time_in_months / 12) - 1)
            additional_gain = recommended_gain - current_gain

            results.append({
                "Token": symbol,
                "Cantidad": amount,
                "APY Actual (%)": apy_current,
                "APY Recomendado (%)": apy_recommended,
                "Ganancia Actual ($)": current_gain,
                "Ganancia Recomendada ($)": recommended_gain,
                "Ganancia Adicional ($)": additional_gain,
                "Protocolo Recomendado": protocol
            })

    return pd.DataFrame(results)

# Funciones para la interfaz
def render_portfolio_section(portfolio):
    """Renderiza la sección del portfolio"""
    st.subheader("📊 Tu Portfolio")

    if portfolio and 'tokens' in portfolio:
        # Crear DataFrame para mostrar los tokens
        df = pd.DataFrame(portfolio['tokens'])

        # Mostrar gráfico de composición del portfolio
        fig = px.pie(df, values='value', names='symbol', title='Composición del Portfolio')
        st.plotly_chart(fig)

        # Mostrar tabla de tokens
        st.dataframe(df)
    else:
        st.warning("No se encontraron tokens en el portfolio")

def render_opportunities_section(opportunities):
    """Renderiza la sección de oportunidades"""
    st.subheader("💎 Oportunidades de Inversión")

    if opportunities:
        # Crear DataFrame para mostrar las oportunidades
        df = pd.DataFrame(opportunities)

        # Filtros interactivos
        col1, col2 = st.columns(2)
        with col1:
            min_apy = st.slider("APY Mínimo (%)", 0, 100, 0)
        with col2:
            selected_protocols = st.multiselect(
                "Protocolos",
                options=df['protocol'].unique(),
                default=df['protocol'].unique()
            )

        # Aplicar filtros
        filtered_df = df[
            (df['apy'] >= min_apy) &
            (df['protocol'].isin(selected_protocols))
        ]

        # Mostrar gráfico de APY por protocolo
        fig = px.bar(
            filtered_df,
            x='protocol',
            y='apy',
            title='APY por Protocolo'
        )
        st.plotly_chart(fig)

        # Mostrar tabla de oportunidades
        st.dataframe(filtered_df)
    else:
        st.warning("No se encontraron oportunidades de inversión")

def render_additional_gains_section(portfolio, opportunities):
    """Renderiza la sección de ganancias adicionales"""
    st.subheader("📈 Ganancias Adicionales Potenciales")

    # Calcular ganancias adicionales
    df = calculate_additional_gains(portfolio, opportunities)

    if not df.empty:
        # Mostrar tabla de ganancias adicionales
        st.dataframe(df)

        # Mostrar gráfico de ganancias adicionales
        fig = px.bar(
            df,
            x="Token",
            y="Ganancia Adicional ($)",
            color="Protocolo Recomendado",
            title="Ganancias Adicionales por Token"
        )
        st.plotly_chart(fig)
    else:
        st.warning("No se encontraron ganancias adicionales para mostrar")

def main():
    # Título y descripción
    st.title("🌟 Solana DeFi Advisor")
    st.markdown("""
    Este asistente te ayuda a analizar tu portfolio en Solana y encontrar las mejores oportunidades DeFi.
    """)

    # Inicializar clases
    analyzer = PortfolioAnalyzer()

    # Sidebar para entrada de datos
    with st.sidebar:
        st.header("📝 Entrada de datos")
        wallet_address = st.text_input(
            "Dirección de Wallet Solana",
            placeholder="Ingresa tu dirección de wallet..."
        )

        analyze_button = st.button("Analizar")

    # Contenido principal
    if analyze_button and wallet_address:
        with st.spinner("Analizando tu portfolio..."):
            # Obtener datos
            portfolio = analyzer.get_portfolio(wallet_address)
            opportunities = analyzer.get_defi_opportunities()

            # Mostrar secciones
            col1, col2 = st.columns(2)
            with col1:
                render_portfolio_section(portfolio)
            with col2:
                render_opportunities_section(opportunities)

            # Mostrar sección de ganancias adicionales
            render_additional_gains_section(portfolio, opportunities)

    # Footer
    st.markdown("---")
    st.markdown("""
    💡 **Nota**: Este es un asistente de inversión. Siempre DYOR (Do Your Own Research).
    """)

if __name__ == "__main__":
    main()
