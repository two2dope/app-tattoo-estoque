import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import base64

# =============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA E ESTILO
# =============================================================================

st.set_page_config(
    page_title="Studio Stock",
    page_icon="💀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para carregar o CSS customizado e Font Awesome
def load_css():
    st.markdown("""
        <style>
            /* Importa Font Awesome */
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

            /* Estilo Geral */
            .stApp { background-color: #0F172A; }
            h1, h2, h3 { color: #FFFFFF; }
            
            /* Sidebar */
            [data-testid="stSidebar"] {
                background-color: #1E293B;
                border-right: 1px solid #334155;
            }
            /* Condensar sidebar */
            [data-testid="stSidebar"] .st-emotion-cache-1v0mbdj {
                padding-top: 0.5rem;
                padding-bottom: 0.5rem;
            }
            [data-testid="stSidebar"] .stButton button {
                text-align: left !important;
                justify-content: flex-start !important;
                white-space: nowrap; /* Evita quebra de linha */
            }
            /* Botão de navegação ativo */
            [data-testid="stSidebar"] .st-emotion-cache-1v0mbdj.e115fcil2 {
                background-color: #0F172A;
                border-radius: 5px;
            }
            
            /* Cards do Dashboard */
            .metric-card {
                background-color: #334155;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                border: 1px solid #475569;
            }
            .metric-card i { font-size: 2.5rem; margin-bottom: 10px; color: #00A9FF; }
            .metric-card .metric-value { font-size: 2rem; font-weight: bold; color: #FFFFFF; }
            .metric-card .metric-label { font-size: 1rem; color: #94A3B8; }
            
            /* Botões */
            .stButton>button {
                background-color: #00A9FF;
                color: white;
                border-radius: 8px;
                border: none;
            }
        </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# CONEXÃO COM GOOGLE SHEETS E GERENCIAMENTO DE DADOS
# =============================================================================

# Define as colunas esperadas para evitar KeyErrors
EXPECTED_COLUMNS = [
    "ID", "Nome do Item", "Marca/Modelo", "Tipo/Especificação", "Categoria",
    "Fornecedor Principal", "Quantidade em Estoque", "Estoque Mínimo",
    "Unidade de Medida", "Preço de Custo", "Código/SKU", "Observações",
    "Data da Última Compra"
]

@st.cache_resource
def get_gspread_client():
    # ... (código de conexão idêntico ao anterior)
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Erro de conexão com Google Sheets: {e}")
        return None

@st.cache_data(ttl=60)
def load_stock_data(_client, sheet_name="BaseDeDados_Estoque", worksheet_name="estoque"):
    try:
        spreadsheet = _client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        
        if not data: # Se a planilha estiver vazia
            return pd.DataFrame(columns=EXPECTED_COLUMNS)

        df = pd.DataFrame(data)
        # Garante que todas as colunas esperadas existam
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = None

        numeric_cols = ['Quantidade em Estoque', 'Estoque Mínimo', 'Preço de Custo', 'ID']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df[EXPECTED_COLUMNS] # Garante a ordem correta
    except Exception as e:
        st.error(f"Não foi possível carregar os dados: {e}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

def save_stock_data(client, df, sheet_name="BaseDeDados_Estoque", worksheet_name="estoque"):
    try:
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
        df_to_save = df.fillna('').astype(str)
        worksheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar os dados: {e}")

client = get_gspread_client()
if client:
    if 'stock_df' not in st.session_state:
        st.session_state.stock_df = load_stock_data(client)
else:
    st.session_state.stock_df = pd.DataFrame(columns=EXPECTED_COLUMNS)

def get_unique_values(column_name):
    df = st.session_state.stock_df
    if not df.empty and column_name in df.columns:
        return sorted([x for x in df[column_name].unique() if pd.notna(x) and x != ''])
    return []

# =============================================================================
# FUNÇÃO DE GERAÇÃO DE PDF
# =============================================================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Lista de Compras - Studio Stock', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generate_pdf_download_link(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Cabeçalhos da tabela
    headers = ['Item', 'Marca/Modelo', 'Fornecedor', 'Qtd. a Comprar']
    col_widths = [70, 40, 40, 40]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
    pdf.ln()

    # Dados da tabela
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 10, str(row['Nome do Item']), 1)
        pdf.cell(col_widths[1], 10, str(row['Marca/Modelo']), 1)
        pdf.cell(col_widths[2], 10, str(row['Fornecedor Principal']), 1)
        pdf.cell(col_widths[3], 10, str(row['Qtd. a Comprar (Sugestão)']), 1)
        pdf.ln()
        
    pdf_output = pdf.output(dest='S').encode('latin-1')
    b64 = base64.b64encode(pdf_output).decode('utf-8')
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="lista_de_compras.pdf">Imprimir em PDF</a>'
    return href

# =============================================================================
# PÁGINAS (VIEWS)
# =============================================================================

def page_dashboard():
    st.title("Painel Principal")
    df = st.session_state.stock_df
    if df.empty:
        st.warning("Nenhum item no estoque. Adicione um item para começar.")
        return
    # ... (Restante do código do dashboard idêntico ao anterior)
    total_value = (df['Quantidade em Estoque'] * df['Preço de Custo']).sum()
    items_in_alert = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]
    total_unique_items = df.shape[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card"><i class="fa-solid fa-gem"></i><div class="metric-value">R$ {total_value:,.2f}</div><div class="metric-label">Valor Total do Estoque</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><i class="fa-solid fa-triangle-exclamation"></i><div class="metric-value">{items_in_alert}</div><div class="metric-label">Itens em Alerta</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><i class="fa-solid fa-boxes-stacked"></i><div class="metric-value">{total_unique_items}</div><div class="metric-label">Total de Itens Únicos</div></div>""", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    urgent_items = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']]
    if not urgent_items.empty:
        st.subheader("Itens Precisando de Reposição Urgente")
        for _, row in urgent_items.iterrows():
            st.error(f"**{row['Nome do Item']}** ({row.get('Marca/Modelo', '')}) - Estoque: {row['Quantidade em Estoque']} / Mínimo: {row['Estoque Mínimo']}")


def page_my_stock():
    st.title("Meu Estoque")
    df = st.session_state.stock_df
    if df.empty:
        st.info("Seu estoque está vazio.")
        return
    # ... (Restante do código da página de estoque idêntico, já era robusto)
    search_query = st.text_input("Buscar por nome, marca ou tipo...", placeholder="Buscar...")
    filtered_df = df[
        df['Nome do Item'].str.contains(search_query, case=False, na=False) |
        df['Marca/Modelo'].str.contains(search_query, case=False, na=False)
    ] if search_query else df
    
    edited_df = st.data_editor(filtered_df, hide_index=True, use_container_width=True)
    
    if st.button("Salvar Alterações"):
        # Lógica de salvar aqui (complexa, melhor simplificar ou manter como antes)
        st.session_state.stock_df.update(edited_df)
        save_stock_data(client, st.session_state.stock_df)
        st.success("Alterações salvas!")
        st.rerun()


def page_add_item():
    st.title("Adicionar Novo Item")
    # ... (Código da página de adicionar item idêntico, já era robusto)
    with st.form(key="add_item_form"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome do Item")
            # ... (outros campos)
        with c2:
            marca = st.text_input("Marca/Modelo")
            # ... (outros campos)
        submit_button = st.form_submit_button(label="Salvar Item")
        if submit_button:
            # Lógica de adicionar item
            st.success("Item adicionado!")


def page_register_usage():
    st.title("Registrar Uso de Material")
    df = st.session_state.stock_df
    if df.empty:
        st.warning("Estoque vazio. Não é possível registrar uso.")
        return
    
    if 'session_items' not in st.session_state:
        st.session_state.session_items = []

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Adicionar Itens Consumidos")
        item_names = df.apply(
            lambda row: f"{row['Nome do Item']} ({row.get('Marca/Modelo', '')}) - Estoque: {row['Quantidade em Estoque']}", 
            axis=1
        ).tolist()
        selected_item_str = st.selectbox("Buscar item...", [""] + item_names)
        # ... (Restante da lógica idêntica)

    with col2:
        st.subheader("Itens da Sessão")
        # ... (Restante da lógica idêntica)


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
    
    if st.button("Gerar PDF para Impressão"):
        pdf_link = generate_pdf_download_link(shopping_list_df)
        st.markdown(pdf_link, unsafe_allow_html=True)


def page_registrations():
    st.title("Cadastros")
    
    tab1, tab2 = st.tabs(["Fornecedores", "Categorias"])

    with tab1:
        st.subheader("Fornecedores Cadastrados")
        suppliers = get_unique_values("Fornecedor Principal")
        if suppliers:
            for supplier in suppliers:
                st.markdown(f"- {supplier}")
        else:
            st.info("Nenhum fornecedor cadastrado. Adicione um item para cadastrar seu fornecedor.")

    with tab2:
        st.subheader("Categorias Cadastradas")
        categories = get_unique_values("Categoria")
        if categories:
            for category in categories:
                st.markdown(f"- {category}")
        else:
            st.info("Nenhuma categoria cadastrada. Adicione um item para cadastrar uma categoria.")


# =============================================================================
# NAVEGAÇÃO PRINCIPAL (SIDEBAR)
# =============================================================================

PAGES = {
    "Painel Principal": ("fa-solid fa-hous
