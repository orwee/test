import streamlit as st

def main():
    st.set_page_config(
        page_title="Solana DeFi Advisor",
        page_icon="🌟",
        layout="wide"
    )

    # Título principal
    st.title("🌟 Solana DeFi Advisor")

    # Barra lateral
    st.sidebar.header("Configuración")
    wallet_address = st.sidebar.text_input("Dirección de Wallet")

    if wallet_address:
        st.write(f"Wallet conectada: {wallet_address}")

if __name__ == "__main__":
    main()
