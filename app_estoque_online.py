import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import base64
from datetime import datetime

# =============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA E ESTILO
# =============================================================================

st.set_page_config(
    page_title="Studio Stock",
    page_icon="💀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para carregar o CSS customizado e Font Awesome (usado nos cards)
def load_css():
    st.markdown("""
        <style>
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
            .stApp { background-color: #0F172A; }
            h1, h2, h3 { color: #FFFFFF; }
            
            /* Sidebar */
            [data-testid="stSidebar"] { background-color: #1E293B; }
            [data-testid="stSidebar"] .stButton button {
                text-align: left !important;
                justify-content: flex-start !important;
                white-space: nowrap;
                padding: 0.5rem 1rem; /* Condensa o menu */
            }
            
            /* Cards do Dashboard */
            .metric-card { background-color: #334155; border-radius: 10px; padding: 20px; text-align: center; border: 1px solid #475569; }
            .metric-card i { font-size: 2.5rem; margin-bottom: 10px; color: #00A9FF; }
            .metric-card .metric-value { font-size: 2rem; font-weight: bold; color: #FFFFFF; }
            .metric-card .metric-label { font-size: 1rem; color: #94A3B8; }
        </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# CONEXÃO COM GOOGLE SHEETS E GERENCIAMENTO DE DADOS
# =============================================================================

EXPECTED_COLUMNS = [
    "ID", "Nome do Item", "Marca/Modelo", "Tipo/Especificação", "Categoria",
    "Fornecedor Principal", "Quantidade em Estoque", "Estoque Mínimo",
    "Unidade de Medida", "Preço de Custo", "Código/SKU", "Observações",
    "Data da Última Compra"
]

@st.cache_resource
def get_gspread_client():
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro de conexão com Google Sheets: {e}")
        return None

@st.cache_data(ttl=60)
def load_data(_client, sheet_name="BaseDeDados_Estoque", worksheet_name="estoque"):
    try:
        spreadsheet = _client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        
        if not data:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)

        df = pd.DataFrame(data)
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = None

        numeric_cols = ['Quantidade em Estoque', 'Estoque Mínimo', 'Preço de Custo', 'ID']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df[EXPECTED_COLUMNS]
    except Exception as e:
        st.error(f"Não foi possível carregar os dados: {e}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

def save_data(client, df):
    try:
        spreadsheet = client.open("BaseDeDados_Estoque")
        worksheet = spreadsheet.worksheet("estoque")
        worksheet.clear()
        df_to_save = df.fillna('').astype(str)
        worksheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar os dados: {e}")

client = get_gspread_client()
if client and 'stock_df' not in st.session_state:
    st.session_state.stock_df = load_data(client)
elif 'stock_df' not in st.session_state:
    st.session_state.stock_df = pd.DataFrame(columns=EXPECTED_COLUMNS)

def get_unique_values(column_name):
    df = st.session_state.stock_df
    if not df.empty and column_name in df.columns:
        return sorted([x for x in df[column_name].unique() if pd.notna(x) and str(x).strip() != ''])
    return []

# =============================================================================
# FUNÇÃO DE GERAÇÃO DE PDF
# =============================================================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Lista de Compras - Studio Stock', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generate_pdf_link(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    headers = ['Item', 'Marca/Modelo', 'Fornecedor', 'Comprar (Sugestão)']
    col_widths = [70, 45, 45, 30]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
    pdf.ln()

    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 8, str(row['Nome do Item']), 1)
        pdf.cell(col_widths[1], 8, str(row['Marca/Modelo']), 1)
        pdf.cell(col_widths[2], 8, str(row['Fornecedor Principal']), 1)
        pdf.cell(col_widths[3], 8, str(row['Qtd. a Comprar (Sugestão)']), 1)
        pdf.ln()
        
    pdf_output = pdf.output(dest='S').encode('latin-1')
    b64 = base64.b64encode(pdf_output).decode('utf-8')
    return f'<a href="data:application/pdf;base64,{b64}" download="lista_de_compras.pdf" style="display: inline-block; padding: 8px 12px; background-color: #00A9FF; color: white; text-decoration: none; border-radius: 8px;">Baixar PDF</a>'

# =============================================================================
# PÁGINAS (VIEWS)
# =============================================================================

def page_dashboard():
    st.title("Painel Principal")
    df = st.session_state.stock_df
    if df.empty:
        st.warning("Nenhum item no estoque. Adicione um item para começar.")
        return

    total_value = (df['Quantidade em Estoque'] * df['Preço de Custo']).sum()
    items_in_alert = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]
    total_unique_items = df.shape[0]

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"""<div class="metric-card"><i class="fa-solid fa-gem"></i><div class="metric-value">R$ {total_value:,.2f}</div><div class="metric-label">Valor Total do Estoque</div></div>""", unsafe_allow_html=True)
    col2.markdown(f"""<div class="metric-card"><i class="fa-solid fa-triangle-exclamation"></i><div class="metric-value">{items_in_alert}</div><div class="metric-label">Itens em Alerta</div></div>""", unsafe_allow_html=True)
    col3.markdown(f"""<div class="metric-card"><i class="fa-solid fa-boxes-stacked"></i><div class="metric-value">{total_unique_items}</div><div class="metric-label">Total de Itens Únicos</div></div>""", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    urgent_items = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']]
    if not urgent_items.empty:
        st.subheader("Itens Precisando de Reposição Urgente")
        for _, row in urgent_items.iterrows():
            st.error(f"**{row['Nome do Item']}** ({row.get('Marca/Modelo', '')}) - Estoque: {row['Quantidade em Estoque']} / Mínimo: {row['Estoque Mínimo']}")

def page_my_stock():
    st.title("Meu Estoque")
    # ... (código da página de estoque)

def page_add_item():
    st.title("Adicionar Novo Item")
    # ... (código da página de adicionar item)

def page_register_usage():
    st.title("Registrar Uso de Material")
    # ... (código da página de registrar uso)

def page_shopping_list():
    st.title("Lista de Compras")
    df = st.session_state.stock_df
    shopping_list_df = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].copy()

    if shopping_list_df.empty:
        st.success("Ótima notícia! Nenhum item precisa de reposição.")
        return

    shopping_list_df['Qtd. a Comprar (Sugestão)'] = shopping_list_df.apply(
        lambda row: f"{max(0, row['Estoque Mínimo'] - row['Quantidade em Estoque'])} {row['Unidade de Medida']}(s)", 
        axis=1
    )
    
    st.dataframe(shopping_list_df[['Nome do Item', 'Marca/Modelo', 'Fornecedor Principal', 'Qtd. a Comprar (Sugestão)']], hide_index=True, use_container_width=True)
    
    pdf_link = generate_pdf_link(shopping_list_df)
    st.markdown(pdf_link, unsafe_allow_html=True)

def page_registrations():
    st.title("Cadastros")
    tab1, tab2 = st.tabs(["Fornecedores", "Categorias"])
    with tab1:
        st.subheader("Fornecedores Cadastrados")
        for item in get_unique_values("Fornecedor Principal"): st.write(f"- {item}")
    with tab2:
        st.subheader("Categorias Cadastradas")
        for item in get_unique_values("Categoria"): st.write(f"- {item}")

# =============================================================================
# NAVEGAÇÃO PRINCIPAL (SIDEBAR)
# =============================================================================

# Dicionário de páginas com Emojis
PAGES = {
    "Painel Principal": ("🏠", page_dashboard),
    "Meu Estoque": ("📦", page_my_stock),
    "Adicionar Item": ("➕", page_add_item),
    "Registrar Uso": ("✔️", page_register_usage),
    "Lista de Compras": ("🛒", page_shopping_list),
    "Cadastros": ("📚", page_registrations),
}

with st.sidebar:
    st.markdown('<div style="text-align: center; padding: 1rem 0;"><i class="fa-solid fa-skull" style="font-size: 4rem; color: #E0E0E0;"></i></div>', unsafe_allow_html=True)
    st.title("Studio Stock")
    
    if "page" not in st.session_state:
        st.session_state.page = "Painel Principal"

    df = st.session_state.get('stock_df', pd.DataFrame())
    alert_count = 0
    if not df.empty:
        alert_count = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]

    for page_name, (icon, page_func) in PAGES.items():
        badge = f" ({alert_count})" if page_name == "Lista de Compras" and alert_count > 0 else ""
        if st.button(f"{icon} {page_name}{badge}", use_container_width=True):
            st.session_state.page = page_name
            st.rerun()

    st.markdown("---")
    st.info("Versão 1.2\n\nFeito para estúdios modernos.")

# Executa a função da página atual
if client:
    PAGES[st.session_state.page][1]()
else:
    st.error("Falha na conexão com a base de dados. Verifique as configurações de 'secrets'.")
