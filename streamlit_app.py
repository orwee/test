import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import numpy as np
from openai import OpenAI
import os

# Nueva función para generar el análisis con GPT
def generate_investment_analysis(current_position, alternatives):
    # Obtener API key de Streamlit secrets
    api_key = st.secrets.get("openai_api_key")

    if not api_key:
        st.error("No se encontró la API key de OpenAI. Por favor, configúrala en Streamlit Secrets.")
        return "No se pudo generar el análisis debido a la falta de API key."

    # Inicializar el cliente de OpenAI
    client = OpenAI(api_key=api_key)

    # Crear el prompt
    prompt = f"""
    Analiza las siguientes alternativas de inversión DeFi:

    Posición actual:
    - Token: {current_position['token_symbol']}
    - Protocolo: {current_position['common_name']}
    - Balance USD: ${format_number(current_position['balance_usd'])}

    Alternativas disponibles:
    {'\n'.join([f"- {alt['project']} en {alt['chain']}: {alt['symbol']} (APY: {alt['apy']:.2f}%, TVL: ${format_number(alt['tvlUsd'])})" for alt in alternatives])}

    Por favor, proporciona un análisis conciso que incluya:
    1. Comparación de APYs y riesgos potenciales
    2. Ventajas y desventajas de cada alternativa
    3. Consideraciones sobre la seguridad y el TVL
    4. Una recomendación final basada en el balance riesgo/beneficio
    """

    try:
        # Hacer la llamada a la API
        response = client.chat.completions.create(
            model="gpt-4",  # o "gpt-3.5-turbo" si prefieres
            messages=[
                {"role": "system", "content": "Eres un experto asesor DeFi que proporciona análisis objetivos y profesionales sobre oportunidades de inversión."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        # Extraer y devolver la respuesta
        return response.choices[0].message.content

    except Exception as e:
        st.error(f"Error al generar el análisis: {str(e)}")
        return "No se pudo generar el análisis debido a un error en la API."
        
# Añade esta nueva función después de get_user_defi_positions
def get_defi_llama_yields():
    url = "https://yields.llama.fi/pools"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Exception occurred: {str(e)}"}

def get_alternatives_for_token(token_symbol, llama_data, n=3):
    """
    Busca las mejores alternativas en DefiLlama para un token específico.
    """
    if not llama_data or 'data' not in llama_data:
        return []

    # Separar tokens si es un par de liquidez
    tokens = token_symbol.split('/')

    alternatives = []
    for pool in llama_data['data']:
        # Comprobar si el símbolo del pool coincide con alguno de los tokens
        if any(token.upper() in pool['symbol'].upper() for token in tokens):
            alternatives.append({
                'symbol': pool['symbol'],
                'project': pool['project'],
                'chain': pool['chain'],
                'apy': pool.get('apy', 0),
                'tvlUsd': pool.get('tvlUsd', 0)
            })

    # Ordenar por APY descendente y tomar los top n
    alternatives.sort(key=lambda x: x['apy'], reverse=True)
    return alternatives[:n]
    
def format_number(value):
    if abs(value) >= 1e6:
        return f"{value:,.2f}".rstrip('0').rstrip('.')
    else:
        return f"{value:.6f}".rstrip('0').rstrip('.')

def get_user_defi_positions(address, api_key):
    base_url = "https://api-v1.mymerlin.io/api/merlin/public/userDeFiPositions/all"
    url = f"{base_url}/{address}"
    headers = {
        "Authorization": f"{api_key}"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Exception occurred: {str(e)}"}

def process_defi_data(result):
    # Validar que el resultado no sea None y sea iterable
    if not result or not isinstance(result, list):
        return pd.DataFrame(columns=['chain', 'common_name', 'module', 'token_symbol', 'balance_usd'])

    data = []
    for protocol in result:
        # Validar que el protocolo tenga las claves necesarias
        chain = str(protocol.get('chain', ''))
        common_name = str(protocol.get('commonName', ''))

        for portfolio in protocol.get('portfolio', []):  # Asegurarse de que 'portfolio' sea una lista
            module = str(portfolio.get('module', ''))

            if 'detailed' in portfolio and 'supply' in portfolio['detailed']:
                supply_tokens = portfolio['detailed']['supply']

                if isinstance(supply_tokens, list):  # Validar que 'supply' sea una lista
                    if module == 'Liquidity Pool' and len(supply_tokens) >= 2:
                        try:
                            balance_0 = float(supply_tokens[0].get('balance', 0))
                            balance_1 = float(supply_tokens[1].get('balance', 0))
                            balance_usd_0 = float(supply_tokens[0].get('balanceUSD', 0))
                            balance_usd_1 = float(supply_tokens[1].get('balanceUSD', 0))

                            data.append({
                                'chain': chain,
                                'common_name': common_name,
                                'module': module,
                                'token_symbol': f"{supply_tokens[0].get('tokenSymbol', '')}/{supply_tokens[1].get('tokenSymbol', '')}",
                                'balance_usd': balance_usd_0 + balance_usd_1
                            })
                        except (ValueError, TypeError):
                            continue
                    else:
                        for token in supply_tokens:
                            try:
                                data.append({
                                    'chain': chain,
                                    'common_name': common_name,
                                    'module': module,
                                    'token_symbol': str(token.get('tokenSymbol', '')),
                                    'balance_usd': float(token.get('balanceUSD', 0))
                                })
                            except (ValueError, TypeError):
                                continue

    # Si no hay datos, devolver un DataFrame vacío con las columnas esperadas
    if not data:
        return pd.DataFrame(columns=['chain', 'common_name', 'module', 'token_symbol', 'balance_usd'])

    # Crear el DataFrame
    df = pd.DataFrame(data)

    # Convertir tipos de datos explícitamente
    df['chain'] = df['chain'].astype(str)
    df['common_name'] = df['common_name'].astype(str)
    df['module'] = df['module'].astype(str)
    df['token_symbol'] = df['token_symbol'].astype(str)
    df['balance_usd'] = pd.to_numeric(df['balance_usd'], errors='coerce').fillna(0)

    # Filtrar por balance USD mayor a \$5
    df = df[df['balance_usd'] > 5]

    # Redondear valores numéricos
    df['balance_usd'] = df['balance_usd'].round(6)

    return df

def main():
    st.set_page_config(
        page_title="Rocky by Orwee",
        page_icon="https://corp.orwee.io/wp-content/uploads/2023/07/cropped-imageonline-co-transparentimage-23-e1689783905238-300x300.webp",
        layout="wide"
    )

    # Add logo and title in columns
    col1, col2 = st.columns([1, 10])
    with col1:
        st.image("https://corp.orwee.io/wp-content/uploads/2023/07/cropped-imageonline-co-transparentimage-23-e1689783905238-300x300.webp", width=100)
    with col2:
        st.title("Rocky by Orwee")

    st.sidebar.header("Configuración")
    wallet_address = st.sidebar.text_input("Dirección de Wallet")
    api_key = "uXbmFEMc02mUl4PclRXy5fEZcHyqTLUK"
    
    # Agregar un botón que redirija a orwee.io
    if st.sidebar.button("Visitar Orwee.io 🌐"):
        st.sidebar.markdown(
            """
            <script>
                window.open("https://orwee.io", "_blank");
            </script>
            """,
            unsafe_allow_html=True
        )
    wallet_address = st.sidebar.text_input("Dirección de Wallet")
    api_key = "uXbmFEMc02mUl4PclRXy5fEZcHyqTLUK"

    if wallet_address and api_key:
        #st.write(f"Wallet conectada: {wallet_address}")

        # Obtener datos
        result = get_user_defi_positions(wallet_address, api_key)

        if 'error' not in result:
            try:
                # Procesar datos y crear DataFrame
                df = process_defi_data(result)

                if not df.empty:
                    # Mostrar tabla
                    st.subheader("Posiciones DeFi")

                    # Crear una copia del DataFrame para el display
                    df_display = df.copy()

                    # Formatear las columnas numéricas
                    df_display['balance_usd'] = df_display['balance_usd'].apply(lambda x: f"${format_number(x)}")

                    # Configuración de la tabla con formato mejorado
                    st.dataframe(
                        df_display,
                        column_config={
                            "chain": st.column_config.TextColumn(
                                "Chain",
                                help="Blockchain network"
                            ),
                            "common_name": st.column_config.TextColumn(
                                "Protocol",
                                help="DeFi protocol name"
                            ),
                            "module": st.column_config.TextColumn(
                                "Module",
                                help="Type of DeFi position"
                            ),
                            "token_symbol": st.column_config.TextColumn(
                                "Token",
                                help="Token symbol"
                            ),
                            "balance_usd": st.column_config.TextColumn(
                                "Balance USD",
                                help="Value in USD"
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )

                    # Reemplaza la sección del gráfico original con esto:
                    if df['balance_usd'].sum() > 0:
                        st.subheader("Distribución de Balance USD")
                    
                        # Crear dos columnas para los gráficos
                        col1, col2 = st.columns(2)
                    
                        with col1:
                            # Gráfico por Token y Protocolo
                            df_grouped_protocol = df.groupby(['token_symbol', 'common_name'])['balance_usd'].sum().reset_index()
                            df_grouped_protocol = df_grouped_protocol[df_grouped_protocol['balance_usd'] > 0]
                    
                            fig1 = px.pie(
                                df_grouped_protocol,
                                values='balance_usd',
                                names=df_grouped_protocol.apply(lambda x: f"{x['token_symbol']} ({x['common_name']})", axis=1),
                                title='Distribución por Token y Protocolo',
                                hover_data=['balance_usd'],
                                labels={'balance_usd': 'Balance USD'}
                            )
                    
                            # Personalizar el diseño del gráfico
                            fig1.update_traces(
                                textposition='inside',
                                textinfo='percent+label'
                            )
                            fig1.update_layout(
                                showlegend=True,
                                height=500
                            )
                    
                            st.plotly_chart(fig1, use_container_width=True)
                    
                        with col2:
                            # Gráfico por Módulo
                            df_grouped_module = df.groupby('module')['balance_usd'].sum().reset_index()
                            df_grouped_module = df_grouped_module[df_grouped_module['balance_usd'] > 0]
                    
                            fig2 = px.pie(
                                df_grouped_module,
                                values='balance_usd',
                                names='module',
                                title='Distribución por Módulo',
                                hover_data=['balance_usd'],
                                labels={'balance_usd': 'Balance USD'}
                            )
                    
                            # Personalizar el diseño del gráfico
                            fig2.update_traces(
                                textposition='inside',
                                textinfo='percent+label'
                            )
                            fig2.update_layout(
                                showlegend=True,
                                height=500
                            )
                    
                            st.plotly_chart(fig2, use_container_width=True)
                    
                        # Mostrar estadísticas adicionales
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "Balance Total USD",
                                f"${format_number(df['balance_usd'].sum())}"
                            )
                        with col2:
                            st.metric(
                                "Número de Protocolos",
                                len(df['common_name'].unique())
                            )
                        with col3:
                            st.metric(
                                "Número de Posiciones",
                                len(df)
                            )
                    else:
                        st.warning("No hay datos de balance USD para mostrar en el gráfico")
                else:
                    st.warning("No se encontraron datos para mostrar")
            except Exception as e:
                st.error(f"Error al procesar los datos: {str(e)}")
        else:
            st.error(f"Error al obtener datos: {result['error']}")

        llama_result = get_defi_llama_yields()

        if 'error' not in llama_result:
            st.subheader("🔄 Alternativas de inversión en DeFi")

            # Para cada posición en el portafolio
            for idx, row in df.iterrows():
                with st.expander(f"Alternativas para {row['token_symbol']} (actual en {row['common_name']})"):
                    alternatives = get_alternatives_for_token(row['token_symbol'], llama_result)

                    if alternatives:
                        # Crear un DataFrame con las alternativas
                        df_alternatives = pd.DataFrame(alternatives)

                        # Formatear las columnas
                        df_display = df_alternatives.copy()
                        df_display['apy'] = df_display['apy'].apply(lambda x: f"{x:.2f}%")
                        df_display['tvlUsd'] = df_display['tvlUsd'].apply(lambda x: f"${format_number(x)}")

                        # Mostrar la tabla de alternativas
                        st.dataframe(
                            df_display,
                            column_config={
                                "symbol": "Token",
                                "project": "Protocolo",
                                "chain": "Blockchain",
                                "apy": "APY",
                                "tvlUsd": "TVL"
                            },
                            hide_index=True,
                            use_container_width=True
                        )

                        # Mostrar métricas comparativas
                        if len(alternatives) > 0:
                            mejor_apy = alternatives[0]['apy']
                            diferencia_apy = mejor_apy - 0  # Aquí podrías comparar con el APY actual si lo tienes

                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(
                                    "Mejor APY disponible",
                                    f"{mejor_apy:.2f}%",
                                    f"+{diferencia_apy:.2f}%" if diferencia_apy > 0 else f"{diferencia_apy:.2f}%"
                                )
                            with col2:
                                st.metric(
                                    "Potencial ganancia adicional anual",
                                    f"${format_number(row['balance_usd'] * diferencia_apy / 100)}"
                                )
                        # Añadir el análisis de GPT
                        '''
                        st.subheader("💡 Análisis de Alternativas")
                        with st.spinner('Generando análisis...'):
                            analysis = generate_investment_analysis(row, alternatives)
                            st.markdown(analysis)
                        '''
                    else:
                        st.info("No se encontraron alternativas para este token")
        else:
            st.error("No se pudieron obtener datos de DefiLlama")

        
        # Usar HTML para centrar la imagen
        st.markdown(
            """
            <div style="text-align: center; margin-top: 20px; margin-bottom: 20px;">
                <img src="https://www.deepseek.com/_next/image?url=https%3A%2F%2Fcdn.deepseek.com%2Flogo.png&w=828&q=75"
                     alt="DeepSeek Logo"
                     width="150"
                     style="padding-top: 30px; padding-bottom: 30px;">
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown(
            """
            <div style='text-align: center'>
                <p>Developed by Orwee | Powered by DeepSeek</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
if __name__ == "__main__":
    main()
