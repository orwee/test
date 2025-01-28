import streamlit as st
import requests
import pandas as pd
import plotly.express as px

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
        chain = protocol['chain']
        common_name = protocol['commonName']

        for portfolio in protocol['portfolio']:
            module = portfolio['module']

            if 'detailed' in portfolio and 'supply' in portfolio['detailed']:
                supply_tokens = portfolio['detailed']['supply']

                if module == 'Liquidity Pool' and len(supply_tokens) >= 2:
                    data.append({
                        'chain': chain,
                        'common_name': common_name,
                        'module': module,
                        'token_symbol': f"{supply_tokens[0].get('tokenSymbol', '')}/{supply_tokens[1].get('tokenSymbol', '')}",
                        'total_supply': supply_tokens[0].get('balance', 0) + supply_tokens[1].get('balance', 0),
                        'balance_usd': supply_tokens[0].get('balanceUSD', 0) + supply_tokens[1].get('balanceUSD', 0)
                    })
                else:
                    for token in supply_tokens:
                        data.append({
                            'chain': chain,
                            'common_name': common_name,
                            'module': module,
                            'token_symbol': token.get('tokenSymbol', ''),
                            'total_supply': token.get('balance', 0),
                            'balance_usd': token.get('balanceUSD', 0)
                        })
    return pd.DataFrame(data)

def main():
    st.set_page_config(
        page_title="Solana DeFi Advisor",
        page_icon="🌟",
        layout="wide"
    )

    st.title("🌟 Solana DeFi Advisor")

    st.sidebar.header("Configuración")
    wallet_address = st.sidebar.text_input("Dirección de Wallet")
    api_key = st.sidebar.text_input("API Key", type="password")

    if wallet_address and api_key:
        st.write(f"Wallet conectada: {wallet_address}")

        # Obtener datos
        result = get_user_defi_positions(wallet_address, api_key)

        if 'error' not in result:
            # Procesar datos y crear DataFrame
            df = process_defi_data(result)

            # Mostrar tabla
            st.subheader("Posiciones DeFi")
            st.dataframe(df)

            # Crear y mostrar gráfico de tortas
            st.subheader("Distribución de Balance USD por Protocol")
            fig = px.pie(df,
                        values='balance_usd',
                        names='common_name',
                        title='Distribución de Balance USD por Protocolo')
            st.plotly_chart(fig)
        else:
            st.error(f"Error al obtener datos: {result['error']}")

if __name__ == "__main__":
    main()
