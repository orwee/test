import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import numpy as np

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
                                    'total_supply': float(token.get('balance', 0)),
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
        page_title="Solana DeFi Advisor",
        page_icon="🌟",
        layout="wide"
    )

    st.title("🌟 Solana DeFi Advisor")

    st.sidebar.header("Configuración")
    wallet_address = st.sidebar.text_input("Dirección de Wallet")
    api_key = "uXbmFEMc02mUl4PclRXy5fEZcHyqTLUK"

    if wallet_address and api_key:
        st.write(f"Wallet conectada: {wallet_address}")

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
                    df_display['total_supply'] = df_display['total_supply'].apply(format_number)
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

                    # Crear y mostrar gráfico de tortas
                    if df['balance_usd'].sum() > 0:
                        st.subheader("Distribución de Balance USD por Protocol")

                        # Agregar los datos por protocolo
                        df_grouped = df.groupby('common_name')['balance_usd'].sum().reset_index()
                        df_grouped = df_grouped[df_grouped['balance_usd'] > 0]  # Filtrar solo valores positivos

                        # Crear el gráfico de tortas
                        fig = px.pie(
                            df_grouped,
                            values='balance_usd',
                            names='common_name',
                            title='Distribución de Balance USD por Protocolo',
                            hover_data=['balance_usd'],
                            labels={'balance_usd': 'Balance USD'}
                        )

                        # Personalizar el diseño del gráfico
                        fig.update_traces(
                            textposition='inside',
                            textinfo='percent+label'
                        )
                        fig.update_layout(
                            showlegend=True,
                            width=800,
                            height=500
                        )

                        # Mostrar el gráfico
                        st.plotly_chart(fig, use_container_width=True)

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

    # Añadir información adicional en el footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>Desarrollado con ❤️ por Tu Nombre</p>
            <p style='font-size: small'>Powered by Solana</p>
        </div>
        """,
        unsafe_allow_html=True
    )
if __name__ == "__main__":
    main()
