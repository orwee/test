import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import numpy as np
from openai import OpenAI
import os

# New function to generate the investment analysis using GPT
def generate_investment_analysis(current_position, alternatives):
    # Retrieve API key from Streamlit secrets
    api_key = st.secrets.get("openai_api_key")

    if not api_key:
        st.error("OpenAI API key not found. Please set it in Streamlit Secrets.")
        return "Could not generate the analysis due to missing API key."

    # Initialize the OpenAI client
    client = OpenAI(api_key=api_key)

    # Create the prompt
    prompt = f"""
    Analyze the following DeFi investment alternatives:

    Current position:
    - Token: {current_position['token_symbol']}
    - Protocol: {current_position['common_name']}
    - Balance USD: ${format_number(current_position['balance_usd'])}

    Available alternatives:
    {'\n'.join([f"- {alt['project']} on {alt['chain']}: {alt['symbol']} (APY: {alt['apy']:.2f}%, TVL: ${format_number(alt['tvlUsd'])})" for alt in alternatives])}

    Please provide a concise analysis that includes:
    1. Comparison of APYs and potential risks
    2. Advantages and disadvantages of each alternative
    3. Security and TVL considerations
    4. A final recommendation based on the risk/benefit balance
    """

    try:
        # Call the API
        response = client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo" if you prefer
            messages=[
                {"role": "system", "content": "You are a DeFi expert advisor providing objective and professional analysis of investment opportunities."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        # Extract and return the response
        return response.choices[0].message.content

    except Exception as e:
        st.error(f"Error generating analysis: {str(e)}")
        return "Could not generate the analysis due to an API error."


# Add this new function after get_user_defi_positions
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
    Searches for the best DeFiLlama alternatives for a specific token.
    """
    if not llama_data or 'data' not in llama_data:
        return []

    # Split token symbols if it's a liquidity pair
    tokens = token_symbol.split('/')

    alternatives = []
    for pool in llama_data['data']:
        # Check whether the pool symbol matches any of the tokens
        if any(token.upper() in pool['symbol'].upper() for token in tokens):
            alternatives.append({
                'symbol': pool['symbol'],
                'project': pool['project'],
                'chain': pool['chain'],
                'apy': pool.get('apy', 0),
                'tvlUsd': pool.get('tvlUsd', 0)
            })

    # Sort by descending APY and take top n
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
    # Validate that the result is not None and is iterable
    if not result or not isinstance(result, list):
        return pd.DataFrame(columns=['chain', 'common_name', 'module', 'token_symbol', 'balance_usd'])

    data = []
    for protocol in result:
        # Validate that the protocol has the necessary keys
        chain = str(protocol.get('chain', ''))
        common_name = str(protocol.get('commonName', ''))

        for portfolio in protocol.get('portfolio', []):  # Ensure 'portfolio' is a list
            module = str(portfolio.get('module', ''))

            if 'detailed' in portfolio and 'supply' in portfolio['detailed']:
                supply_tokens = portfolio['detailed']['supply']

                if isinstance(supply_tokens, list):  # Validate that 'supply' is a list
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

    # If there is no data, return an empty DataFrame with the expected columns
    if not data:
        return pd.DataFrame(columns=['chain', 'common_name', 'module', 'token_symbol', 'balance_usd'])

    # Create the DataFrame
    df = pd.DataFrame(data)

    # Explicitly convert data types
    df['chain'] = df['chain'].astype(str)
    df['common_name'] = df['common_name'].astype(str)
    df['module'] = df['module'].astype(str)
    df['token_symbol'] = df['token_symbol'].astype(str)
    df['balance_usd'] = pd.to_numeric(df['balance_usd'], errors='coerce').fillna(0)

    # Filter for balance USD > \$5
    df = df[df['balance_usd'] > 5]

    # Round numeric values
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

    st.sidebar.header("Settings")
    wallet_address = st.sidebar.text_input("Wallet Address")
    api_key = "uXbmFEMc02mUl4PclRXy5fEZcHyqTLUK"

    if wallet_address and api_key:
        # Retrieve data
        result = get_user_defi_positions(wallet_address, api_key)

        if 'error' not in result:
            try:
                # Process data and create a DataFrame
                df = process_defi_data(result)

                if not df.empty:
                    # Display table
                    st.subheader("DeFi Positions")

                    # Create a copy of the DataFrame for display
                    df_display = df.copy()

                    # Format numeric columns
                    df_display['balance_usd'] = df_display['balance_usd'].apply(lambda x: f"${format_number(x)}")

                    # Enhanced table configuration
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

                    # Plotly chart customization
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

                    # Example of customized charts
                    if df['balance_usd'].sum() > 0:
                        st.subheader("Balance USD Distribution")

                        # Create two columns for charts
                        col1, col2 = st.columns(2)

                        with col1:
                            # Chart by Token and Protocol
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

                            fig1 = customize_plotly(fig1)
                            st.plotly_chart(fig1, use_container_width=True)

                        with col2:
                            # Chart by Module
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

                            fig2 = customize_plotly(fig2)
                            st.plotly_chart(fig2, use_container_width=True)

                        # Display additional stats
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "Total Balance USD",
                                f"${format_number(df['balance_usd'].sum())}"
                            )
                        with col2:
                            st.metric(
                                "Number of Protocols",
                                len(df['common_name'].unique())
                            )
                        with col3:
                            st.metric(
                                "Number of Positions",
                                len(df)
                            )
                    else:
                        st.warning("No USD balance data available for chart display")
                else:
                    st.warning("No data found to display")
            except Exception as e:
                st.error(f"Error processing data: {str(e)}")
        else:
            st.error(f"Error retrieving data: {result['error']}")

        llama_result = get_defi_llama_yields()

        if 'error' not in llama_result:
            st.subheader("🔄 DeFi Investment Alternatives")

            # For each position in the portfolio
            for idx, row in df.iterrows():
                with st.expander(f"Alternatives for {row['token_symbol']} (currently in {row['common_name']})"):
                    alternatives = get_alternatives_for_token(row['token_symbol'], llama_result)

                    if alternatives:
                        # Create a DataFrame with the alternatives
                        df_alternatives = pd.DataFrame(alternatives)

                        # Format columns
                        df_display = df_alternatives.copy()
                        df_display['apy'] = df_display['apy'].apply(lambda x: f"{x:.2f}%")
                        df_display['tvlUsd'] = df_display['tvlUsd'].apply(lambda x: f"${format_number(x)}")

                        # Display the alternatives table
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

                        # Show comparative metrics
                        if len(alternatives) > 0:
                            best_apy = alternatives[0]['apy']
                            apy_difference = best_apy - 0  # Here you could compare to the current APY if available

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

                        # Add GPT analysis (currently commented out):
                        '''
                        st.subheader("💡 Analysis of Alternatives")
                        with st.spinner('Generating analysis...'):
                            analysis = generate_investment_analysis(row, alternatives)
                            st.markdown(analysis)
                        '''
                    else:
                        st.info("No alternatives found for this token")
        else:
            st.error("Could not retrieve DefiLlama data")


        # Use HTML to center the image
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

        st.markdown(
            """
            <style>
            /* Import IBM Plex Mono from Google Fonts */
            @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');

            /* General style */
            * {
                font-family: 'IBM Plex Mono', monospace;
            }

            /* Customize headers */
            h1, h2, h3, h4, h5, h6 {
                font-family: 'IBM Plex Mono', monospace;
                color: #A199DA;
            }

            /* Customize button colors */
            .stButton>button {
                background-color: #A199DA;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0.5rem 1rem;
                font-family: 'IBM Plex Mono', monospace;
            }

            .stButton>button:hover {
                background-color: #8A82C9;
            }

            /* Customize metrics */
            .css-1wivap2 {
                background-color: #A199DA20;
                border: 1px solid #A199DA;
                border-radius: 4px;
                padding: 1rem;
            }

            /* Customize links */
            a {
                color: #A199DA !important;
                text-decoration: none;
            }

            a:hover {
                color: #8A82C9 !important;
            }

            /* Customize input widgets */
            .stTextInput>div>div>input {
                font-family: 'IBM Plex Mono', monospace;
            }

            /* Customize selectbox */
            .stSelectbox>div>div>select {
                font-family: 'IBM Plex Mono', monospace;
            }

            /* Customize expander */
            .streamlit-expanderHeader {
                font-family: 'IBM Plex Mono', monospace;
                background-color: #A199DA20;
                color: #A199DA;
            }

            /* Customize sidebar */
            .css-1d391kg {
                font-family: 'IBM Plex Mono', monospace;
            }

            /* Customize dataframe */
            .dataframe {
                font-family: 'IBM Plex Mono', monospace;
            }

            /* Customize metric text */
            .css-1wivap2 label {
                font-family: 'IBM Plex Mono', monospace;
            }

            /* Customize tooltips */
            .tooltip {
                font-family: 'IBM Plex Mono', monospace;
            }

            /* Customize charts */
            .plotly-graph-div {
                font-family: 'IBM Plex Mono', monospace;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Plotly configuration
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

        # Button on the sidebar
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

if __name__ == "__main__":
    main()
