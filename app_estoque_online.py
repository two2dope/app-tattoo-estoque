import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

# =============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA E ESTILO
# =============================================================================

st.set_page_config(
    page_title="Studio Stock",
    page_icon="💀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# SCHEMA DE DADOS: Define a estrutura esperada do nosso DataFrame. Essencial para robustez.
COLUMNS_SCHEMA = {
    "ID": int, "Nome do Item": str, "Marca/Modelo": str, "Tipo/Especificação": str,
    "Categoria": str, "Fornecedor Principal": str, "Quantidade em Estoque": float,
    "Estoque Mínimo": int, "Unidade de Medida": str, "Preço de Custo": float,
    "Código/SKU": str, "Observações": str, "Data da Última Compra": str
}

# Função para carregar CSS customizado, Font Awesome e CSS de Impressão
def load_css():
    st.markdown("""
        <style>
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
            
            /* --- ESTILO GERAL --- */
            .stApp { background-color: #0F172A; }
            h1, h2, h3 { color: #FFFFFF; }
            
            /* --- SIDEBAR --- */
            [data-testid="stSidebar"] {
                background-color: #1E293B;
                border-right: 1px solid #334155;
            }
            [data-testid="stSidebar"] h1 {
                font-size: 24px;
                text-align: center;
            }
            .sidebar-button {
                display: flex;
                align-items: center;
                padding: 0.5rem 0.75rem !important;
                margin: 0.2rem 0;
                background-color: transparent;
                border: none;
                color: #E0E0E0;
                width: 100%;
                text-align: left;
                font-size: 1rem;
                border-radius: 8px;
                transition: background-color 0.2s, color 0.2s;
            }
            .sidebar-button:hover {
                background-color: #334155;
                color: #FFFFFF;
            }
            .sidebar-button.active {
                background-color: #0F172A;
                color: #FFFFFF;
                font-weight: bold;
            }
            .sidebar-button i {
                margin-right: 12px;
                width: 20px; /* Alinhamento dos ícones */
            }
            
            /* --- CARDS DO DASHBOARD --- */
            .metric-card {
                background-color: #334155; border-radius: 10px; padding: 20px;
                text-align: center; border: 1px solid #475569;
            }
            .metric-card i { font-size: 2.5rem; margin-bottom: 10px; color: #00A9FF; }
            .metric-card .metric-value { font-size: 2rem; font-weight: bold; color: #FFFFFF; }
            .metric-card .metric-label { font-size: 1rem; color: #94A3B8; }
            
            /* --- CSS PARA IMPRESSÃO --- */
            @media print {
                [data-testid="stSidebar"], [data-testid="stHeader"], .no-print {
                    display: none !important;
                }
                .stApp {
                    background-color: #FFFFFF !important;
                }
                h1, h2, h3, .stDataFrame, .stTable {
                    color: #000000 !important;
                }
            }
        </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# CONEXÃO COM GOOGLE SHEETS E GERENCIAMENTO DE DADOS (BACKEND)
# =============================================================================
@st.cache_resource
def get_gspread_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_stock_data(_client, sheet_name="BaseDeDados_Estoque", worksheet_name="estoque"):
    try:
        spreadsheet = _client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()
        
        df = pd.DataFrame(records)
        
        # GARANTE A ROBUSTEZ: Se a planilha estiver vazia, cria um DF com a estrutura correta.
        if df.empty:
            df = pd.DataFrame(columns=list(COLUMNS_SCHEMA.keys()))
        
        # Garante que todas as colunas existem, preenchendo com valores nulos se faltarem.
        for col, dtype in COLUMNS_SCHEMA.items():
            if col not in df.columns:
                df[col] = pd.NA
            df[col] = df[col].astype(dtype, errors='ignore')

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame(columns=list(COLUMNS_SCHEMA.keys()))

def save_stock_data(client, df, sheet_name="BaseDeDados_Estoque", worksheet_name="estoque"):
    try:
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
        
        # Garante que as colunas estão na ordem correta antes de salvar
        df_to_save = df[list(COLUMNS_SCHEMA.keys())].fillna('')
        
        worksheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
        st.cache_data.clear() # Limpa o cache para recarregar
    except Exception as e:
        st.error(f"Erro ao salvar os dados: {e}")

# Inicialização dos dados
client = get_gspread_client()
if 'stock_df' not in st.session_state:
    st.session_state.stock_df = load_stock_data(client)

# =============================================================================
# COMPONENTES REUTILIZÁVEIS (EX: BOTÃO DE IMPRESSÃO)
# =============================================================================
def print_button():
    st.markdown("""
        <div class="no-print" style="text-align: right;">
            <button onclick="window.print()" style="padding: 8px 16px; border-radius: 8px; border: none; background-color: #00A9FF; color: white; cursor: pointer;">
                <i class="fa-solid fa-print"></i> Imprimir / Salvar em PDF
            </button>
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# DEFINIÇÃO DAS PÁGINAS (VIEWS)
# =============================================================================

def page_dashboard():
    st.title("Painel Principal")
    df = st.session_state.stock_df
    if df.empty:
        st.warning("Nenhum item no estoque. Adicione um item para começar.")
        return

    total_value = (pd.to_numeric(df['Quantidade em Estoque'], errors='coerce').fillna(0) * pd.to_numeric(df['Preço de Custo'], errors='coerce').fillna(0)).sum()
    items_in_alert = df[pd.to_numeric(df['Quantidade em Estoque'], errors='coerce') <= pd.to_numeric(df['Estoque Mínimo'], errors='coerce')].shape[0]
    total_unique_items = df.shape[0]

    col1, col2, col3 = st.columns(3)
    # ... (código dos cards do dashboard, que permanece o mesmo) ...

def page_my_stock():
    st.title("Meu Estoque")
    # ... (código da página de estoque, que permanece o mesmo) ...
    # Adicionar botão de impressão
    print_button()

def page_add_item():
    st.title("Adicionar Novo Item")
    # ... (código da página de adicionar item, que permanece o mesmo) ...

def page_register_usage():
    st.title("Registrar Uso de Material")
    # ... (código da página de registrar uso, que permanece o mesmo) ...

def page_shopping_list():
    st.title("Lista de Compras")
    st.info("Esta lista mostra todos os itens que atingiram ou estão abaixo do estoque mínimo definido.")
    print_button()

    df = st.session_state.stock_df.copy()
    df['Quantidade em Estoque'] = pd.to_numeric(df['Quantidade em Estoque'], errors='coerce').fillna(0)
    df['Estoque Mínimo'] = pd.to_numeric(df['Estoque Mínimo'], errors='coerce').fillna(0)

    shopping_list_df = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']]
    
    # ... (restante do código da lista de compras) ...

def page_registrations():
    st.title("Cadastros")
    
    tab1, tab2 = st.tabs(["Gerenciar Fornecedores", "Gerenciar Categorias"])

    with tab1:
        st.subheader("Fornecedores")
        # Lógica para gerenciar fornecedores
        
    with tab2:
        st.subheader("Categorias")
        # Lógica para gerenciar categorias

# =============================================================================
# NAVEGAÇÃO PRINCIPAL (SIDEBAR)
# =============================================================================

PAGES = {
    "Painel Principal": ("fa-solid fa-house", page_dashboard),
    "Meu Estoque": ("fa-solid fa-box-archive", page_my_stock),
    "Adicionar Item": ("fa-solid fa-plus-circle", page_add_item),
    "Registrar Uso": ("fa-solid fa-check-circle", page_register_usage),
    "Lista de Compras": ("fa-solid fa-shopping-cart", page_shopping_list),
    "Cadastros": ("fa-solid fa-cogs", page_registrations), # Alterado
}

def render_sidebar():
    with st.sidebar:
        st.markdown(f"<h1><i class='fa-solid fa-skull'></i> Studio Stock</h1>", unsafe_allow_html=True)
        st.markdown("---")
        
        if "page" not in st.session_state:
            st.session_state.page = "Painel Principal"

        for page_name, (icon, _) in PAGES.items():
            active_class = "active" if st.session_state.page == page_name else ""
            button_html = f"""
                <button class="sidebar-button {active_class}" onclick="document.getElementById('{page_name.replace(" ", "_")}').click()">
                    <i class="{icon}"></i>
                    <span>{page_name}</span>
                </button>
            """
            st.markdown(button_html, unsafe_allow_html=True)
            # Botão real escondido para acionar o callback do Streamlit
            if st.button(page_name, key=page_name.replace(" ", "_"), type="primary", use_container_width=True):
                st.session_state.page = page_name
                st.rerun()

        st.markdown("---", unsafe_allow_html=True)
        st.info("Versão 2.0\n\nFeito para estúdios modernos.")

render_sidebar()

# Renderiza a página selecionada
if client:
    page_icon, page_function = PAGES[st.session_state.page]
    page_function()
else:
    st.error("Falha na conexão com a base de dados. Verifique as configurações de 'secrets' do Streamlit.")
