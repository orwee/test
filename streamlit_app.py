import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import numpy as np
from openai import OpenAI
import os

def generate_investment_analysis(current_position, alternatives):
    api_key = st.secrets.get("openai_api_key")

    if not api_key:
        st.error("OpenAI API key not found. Please set it in Streamlit Secrets.")
        return "Could not generate the analysis due to missing API key."

    client = OpenAI(api_key=api_key)

    prompt = f"""
    Analyze the following DeFi investment alternatives:

    Current position:
    - Token: {current_position['token_symbol']}
    - Protocol: {current_position['common_name']}
    - Balance USD: ${format_number(current_position['balance_usd'])}

    Available alternatives:
    {'\n'.join([f"- {alt['project']} on {alt['chain']}: {alt['symbol']} (APY: {alt['apy']:.2f}%, TVL: ${format_number(alt['tvlUsd'])})" for alt in alternatives])}

    Please provide a concise analysis (max 100 words) that including a comparison between current and alternative positions. Remarking the final recomendation
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a DeFi expert advisor providing objective and professional analysis of investment opportunities."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating analysis: {str(e)}")
        return "Could not generate the analysis due to an API error."

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
    if not llama_data or 'data' not in llama_data:
        return []

    tokens = token_symbol.split('/')
    alternatives = []
    for pool in llama_data['data']:
        if any(token.upper() in pool['symbol'].upper() for token in tokens):
            alternatives.append({
                'symbol': pool['symbol'],
                'project': pool['project'],
                'chain': pool['chain'],
                'apy': pool.get('apy', 0),
                'tvlUsd': pool.get('tvlUsd', 0)
            })
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
    headers = {"Authorization": f"{api_key}"}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Exception occurred: {str(e)}"}

def process_defi_data(result):
    if not result or not isinstance(result, list):
        return pd.DataFrame(columns=['chain', 'common_name', 'module', 'token_symbol', 'balance_usd'])

    data = []
    for protocol in result:
        chain = str(protocol.get('chain', ''))
        common_name = str(protocol.get('commonName', ''))

        for portfolio in protocol.get('portfolio', []):
            module = str(portfolio.get('module', ''))

            if 'detailed' in portfolio and 'supply' in portfolio['detailed']:
                supply_tokens = portfolio['detailed']['supply']
                if isinstance(supply_tokens, list):
                    if module == 'Liquidity Pool' and len(supply_tokens) >= 2:
                        try:
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

    if not data:
        return pd.DataFrame(columns=['chain', 'common_name', 'module', 'token_symbol', 'balance_usd'])

    df = pd.DataFrame(data)
    df['chain'] = df['chain'].astype(str)
    df['common_name'] = df['common_name'].astype(str)
    df['module'] = df['module'].astype(str)
    df['token_symbol'] = df['token_symbol'].astype(str)
    df['balance_usd'] = pd.to_numeric(df['balance_usd'], errors='coerce').fillna(0)
    df = df[df['balance_usd'] > 5]
    df['balance_usd'] = df['balance_usd'].round(6)
    return df

def main():
    st.set_page_config(
        page_title="Rocky by Orwee",
        page_icon="https://corp.orwee.io/wp-content/uploads/2023/07/cropped-imageonline-co-transparentimage-23-e1689783905238-300x300.webp",
        layout="wide"
    )

    # Global custom CSS for fonts and button highlights
    st.markdown(
        """
        <style>
        /* Import IBM Plex Mono from Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');

        /* Make absolutely everything use IBM Plex Mono */
        html, body, [class*="css"]  {
            font-family: 'IBM Plex Mono', monospace !important;
        }

        /* Customize button colors globally */
        .stButton>button {
            background-color: #A199DA !important;
            color: white !important;
            border: none !important;
            border-radius: 4px !important;
            padding: 0.5rem 1rem !important;
            font-family: 'IBM Plex Mono', monospace !important;
        }
        /* Hover, focus, and active states in the same color scheme */
        .stButton>button:hover,
        .stButton>button:focus,
        .stButton>button:active {
            background-color: #8A82C9 !important;
            color: white !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 10])
    with col1:
        st.image("https://corp.orwee.io/wp-content/uploads/2023/07/cropped-imageonline-co-transparentimage-23-e1689783905238-300x300.webp", width=100)
    with col2:
        st.title("Rocky by Orwee")

    st.sidebar.header("Settings")

    # Wallet address input
    wallet_address = st.sidebar.text_input("Wallet Address")

    # Example API key (replace or also request from user)
    api_key = "vEDmTpgKh4iRfSFVkS9vFTswy79pPr5h"

    # Button to run the main analysis
    analyze_button = st.sidebar.button("Analyze with AI")

    # If the user clicks on "Analyze with AI" and has provided a wallet address
    if analyze_button and wallet_address and api_key:
        result = get_user_defi_positions(wallet_address, api_key)
        if 'error' not in result:
            try:
                df = process_defi_data(result)

                if not df.empty:
                    st.subheader("DeFi Positions")
                    df_display = df.copy()
                    df_display['balance_usd'] = df_display['balance_usd'].apply(lambda x: f"${format_number(x)}")

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

                    def customize_plotly(fig):
                        fig.update_layout(
                            font_family='IBM Plex Mono',
                            font_color='#A199DA',
                            title_font_size=18,
                            title_font_color='#A199DA',
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            colorway=['#A199DA', '#8A82C9', '#6C63B6', '#524AA3', '#3D3590'],
                        )
                        return fig

                    if df['balance_usd'].sum() > 0:
                        st.subheader("Balance USD Distribution")
                        c1, c2 = st.columns(2)

                        with c1:
                            df_grouped_protocol = df.groupby(['token_symbol', 'common_name'])['balance_usd'].sum().reset_index()
                            df_grouped_protocol = df_grouped_protocol[df_grouped_protocol['balance_usd'] > 0]

                            fig1 = px.pie(
                                df_grouped_protocol,
                                values='balance_usd',
                                names=df_grouped_protocol.apply(lambda x: f"{x['token_symbol']} ({x['common_name']})", axis=1),
                                title='Distribution by Token and Protocol',
                                hover_data=['balance_usd'],
                                labels={'balance_usd': 'Balance USD'}
                            )
                            customize_plotly(fig1)
                            st.plotly_chart(fig1, use_container_width=True)

                        with c2:
                            df_grouped_module = df.groupby('module')['balance_usd'].sum().reset_index()
                            df_grouped_module = df_grouped_module[df_grouped_module['balance_usd'] > 0]

                            fig2 = px.pie(
                                df_grouped_module,
                                values='balance_usd',
                                names='module',
                                title='Distribution by Module',
                                hover_data=['balance_usd'],
                                labels={'balance_usd': 'Balance USD'}
                            )
                            customize_plotly(fig2)
                            st.plotly_chart(fig2, use_container_width=True)

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "Total Balance USD",
                                f"${format_number(df['balance_usd'].sum())}"
                            )
                        with col2:
                            st.metric("Number of Protocols", len(df['common_name'].unique()))
                        with col3:
                            st.metric("Number of Positions", len(df))

                    else:
                        st.warning("No USD balance data available for chart display.")
                else:
                    st.warning("No data found to display.")
            except Exception as e:
                st.error(f"Error processing data: {str(e)}")
        else:
            st.error(f"Error retrieving data: {result['error']}")

        # Retrieve DeFi Llama yields and display possible alternatives
        llama_result = get_defi_llama_yields()
        if 'error' not in llama_result:
            st.subheader("🔄 DeFi Investment Alternatives")

            if 'error' not in result:
                df = process_defi_data(result)
                if not df.empty:
                    for idx, row in df.iterrows():
                        with st.expander(f"Alternatives for {row['token_symbol']} (currently in {row['common_name']})"):
                            alternatives = get_alternatives_for_token(row['token_symbol'], llama_result)
                            if alternatives:
                                df_alternatives = pd.DataFrame(alternatives)
                                df_display = df_alternatives.copy()
                                df_display['apy'] = df_display['apy'].apply(lambda x: f"{x:.2f}%")
                                df_display['tvlUsd'] = df_display['tvlUsd'].apply(lambda x: f"${format_number(x)}")

                                st.dataframe(
                                    df_display,
                                    column_config={
                                        "symbol": "Token",
                                        "project": "Protocol",
                                        "chain": "Blockchain",
                                        "apy": "APY",
                                        "tvlUsd": "TVL"
                                    },
                                    hide_index=True,
                                    use_container_width=True
                                )

                                if len(alternatives) > 0:
                                    best_apy = alternatives[0]['apy']
                                    apy_difference = best_apy - 0  # Compare with current APY if available

                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.metric(
                                            "Best Available APY",
                                            f"{best_apy:.2f}%",
                                            f"+{apy_difference:.2f}%" if apy_difference > 0 else f"{apy_difference:.2f}%"
                                        )
                                    with col2:
                                        st.metric(
                                            "Potential Additional Annual Gain",
                                            f"${format_number(row['balance_usd'] * apy_difference / 100)}"
                                        )

                                
                                # ───────── Show the GPT analysis section here ─────────
                                st.subheader("💡 Analysis of Alternatives")
                                with st.spinner('Generating analysis...'):
                                    analysis = generate_investment_analysis(row, alternatives)
                                    st.markdown(analysis)
                                

                            else:
                                st.info("No alternatives found for this token.")
                else:
                    st.warning("No valid DeFi data for this wallet.")
            else:
                st.error("Error processing final data from wallet positions.")
        else:
            st.error("Could not retrieve DefiLlama data.")

    # "Visit Orwee" button in sidebar, below everything else
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <a href="https://orwee.io" target="_blank" style="text-decoration: none;">
            <button style="
                background-color: #A199DA;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-family: 'IBM Plex Mono', monospace;
                width: 100%;
                margin: 10px 0;
            ">
                Visit Orwee.io 🌐
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    # Footer elements
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

    # Add your investment disclaimer (in English) below
    st.markdown(
        """
        <div style='text-align: center; margin-top: 10px;'>
            <p style='font-size:10px; color: #999999;'>
                This content is for informational purposes only and does not constitute financial advice.
                Neither Orwee nor DeepSeek accepts responsibility for any financial losses. Please do your own research before making investment decisions.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
