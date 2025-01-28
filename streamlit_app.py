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
    data = []
    for protocol in result:
        chain = str(protocol.get('chain', ''))
        common_name = str(protocol.get('commonName', ''))

        for portfolio in protocol.get('portfolio', []):
            module = str(portfolio.get('module', ''))

            if 'detailed' in portfolio and 'supply' in portfolio['detailed']:
                supply_tokens = portfolio['detailed']['supply']

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
                            'total_supply': balance_0 + balance_1,
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

    if not data:
        return pd.DataFrame(columns=['chain', 'common_name', 'module', 'token_symbol', 'total_supply', 'balance_usd'])

    df = pd.DataFrame(data)

    # Convertir tipos de datos explícitamente
    df['chain'] = df['chain'].astype(str)
    df['common_name'] = df['common_name'].astype(str)
    df['module'] = df['module'].astype(str)
    df['token_symbol'] = df['token_symbol'].astype(str)
    df['total_supply'] = pd.to_numeric(df['total_supply'], errors='coerce').fillna(0)
    df['balance_usd'] = pd.to_numeric(df['balance_usd'], errors='coerce').fillna(0)

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

        result = get_user_defi_positions(wallet_address, api_key)

        if 'error' not in result:
            try:
                df = process_defi_data(result)

                if not df.empty:
                    st.subheader("Posiciones DeFi")

                    # Formatear las columnas numéricas
                    df_display = df.copy()
                    df_display['total_supply'] = df_display['total_supply'].apply(format_number)
                    df_display['balance_usd'] = df_display['balance_usd'].apply(lambda x: f"${format_number(x)}")

                    # Mostrar la tabla formateada
                    st.dataframe(
                        df_display,
                        column_config={
                            "chain": "Chain",
                            "common_name": "Protocol",
                            "module": "Module",
                            "token_symbol": "Token",
                            "total_supply": "Total Supply",
                            "balance_usd": "Balance USD"
                        },
                        hide_index=True
                    )
                    else:
                        st.warning("No hay datos de balance USD para mostrar en el gráfico")
                else:
                    st.warning("No se encontraron datos para mostrar")
            except Exception as e:
                st.error(f"Error al procesar los datos: {str(e)}")
        else:
            st.error(f"Error al obtener datos: {result['error']}")

if __name__ == "__main__":
    main()
