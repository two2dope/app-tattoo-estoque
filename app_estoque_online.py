import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
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

# SCHEMA DE DADOS: Define a estrutura e os tipos de dados esperados do nosso DataFrame.
# Essencial para a robustez e para evitar erros de tipo.
COLUMNS_SCHEMA = {
    "ID": "int64", "Nome do Item": "str", "Marca/Modelo": "str", "Tipo/Especificação": "str",
    "Categoria": "str", "Fornecedor Principal": "str", "Quantidade em Estoque": "float64",
    "Estoque Mínimo": "float64", "Unidade de Medida": "str", "Preço de Custo": "float64",
    "Código/SKU": "str", "Observações": "str", "Data da Última Compra": "str"
}

# Função para carregar o CSS customizado
def load_css():
    """Injeta o CSS customizado para estilizar a aplicação."""
    st.markdown("""
        <style>
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
            
            /* --- ESTILO GERAL --- */
            .stApp { background-color: #0F172A; color: #E2E8F0; }
            h1, h2, h3 { color: #FFFFFF; }
            .stButton > button { border-radius: 8px; }
            .stTabs [data-baseweb="tab-list"] { justify-content: center; }
            
            /* --- SIDEBAR --- */
            [data-testid="stSidebar"] {
                background-color: #1E293B;
                border-right: 1px solid #334155;
            }
            [data-testid="stSidebar"] h1 {
                font-size: 24px;
                text-align: center;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            .stButton > button {
                background-color: transparent;
                border: 1px solid #334155;
            }
            .stButton > button:hover {
                background-color: #334155;
                color: #FFFFFF;
                border: 1px solid #475569;
            }
            .stButton > button:focus {
                background-color: #0F172A;
                color: #FFFFFF;
                border: 1px solid #00A9FF;
                box-shadow: none;
            }
            
            /* --- CARDS DO DASHBOARD --- */
            .metric-card {
                background-color: #1E293B; border-radius: 10px; padding: 20px;
                text-align: center; border: 1px solid #334155; margin-bottom: 1rem;
            }
            .metric-card i { font-size: 2.5rem; margin-bottom: 10px; color: #00A9FF; }
            .metric-card .metric-value { font-size: 2rem; font-weight: bold; color: #FFFFFF; }
            .metric-card .metric-label { font-size: 1rem; color: #94A3B8; }
        </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# CONEXÃO COM GOOGLE SHEETS E GERENCIAMENTO DE DADOS
# =============================================================================
@st.cache_resource
def get_gspread_client():
    """Conecta-se ao Google Sheets usando as credenciais do Streamlit Secrets."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro ao autenticar com o Google: {e}")
        return None

@st.cache_data(ttl=60)
def load_data(_client, sheet_name="BaseDeDados_Estoque", worksheet_name="estoque"):
    """Carrega os dados da planilha e garante que o DataFrame tenha a estrutura correta."""
    try:
        spreadsheet = _client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()
        
        df = pd.DataFrame(records)
        
        if df.empty:
            df = pd.DataFrame(columns=COLUMNS_SCHEMA.keys())
        
        # Garante que todas as colunas do schema existam no DataFrame
        for col, dtype in COLUMNS_SCHEMA.items():
            if col not in df.columns:
                df[col] = pd.NA
            # Converte os tipos de dados, tratando erros
            if 'int' in dtype or 'float' in dtype:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].astype(dtype, errors='ignore').fillna(
                0 if 'int' in dtype or 'float' in dtype else ''
            )
        
        return df[COLUMNS_SCHEMA.keys()] # Garante a ordem correta das colunas
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Planilha '{sheet_name}' não encontrada. Verifique o nome e as permissões.")
        return pd.DataFrame(columns=COLUMNS_SCHEMA.keys())
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame(columns=COLUMNS_SCHEMA.keys())

def save_data(client, df, sheet_name="BaseDeDados_Estoque", worksheet_name="estoque"):
    """Salva o DataFrame inteiro na planilha, substituindo os dados existentes."""
    try:
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
        
        # Prepara o DF para salvar, garantindo a ordem e preenchendo NaNs
        df_to_save = df[COLUMNS_SCHEMA.keys()].fillna('')
        
        worksheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
        st.cache_data.clear() # Limpa o cache para forçar a releitura dos dados
        return True
    except Exception as e:
        st.error(f"Erro ao salvar os dados: {e}")
        return False

# Inicialização do cliente e dos dados
client = get_gspread_client()
if 'stock_df' not in st.session_state and client:
    st.session_state.stock_df = load_data(client)

# =============================================================================
# PÁGINAS DA APLICAÇÃO
# =============================================================================

def page_dashboard():
    st.title("Painel Principal")
    df = st.session_state.get('stock_df', pd.DataFrame())
    
    if df.empty:
        st.warning("Nenhum item no estoque. Adicione um item para começar.")
        return

    total_value = (df['Quantidade em Estoque'] * df['Preço de Custo']).sum()
    items_in_alert = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]
    total_unique_items = df.shape[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><i class="fa-solid fa-dollar-sign"></i><div class="metric-value">R$ {total_value:,.2f}</div><div class="metric-label">Valor Total do Estoque</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><i class="fa-solid fa-triangle-exclamation"></i><div class="metric-value">{items_in_alert}</div><div class="metric-label">Itens em Alerta</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><i class="fa-solid fa-boxes-stacked"></i><div class="metric-value">{total_unique_items}</div><div class="metric-label">Itens Únicos</div></div>', unsafe_allow_html=True)
    
    st.subheader("Itens com Estoque Baixo")
    alert_df = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']]
    if not alert_df.empty:
        st.dataframe(alert_df[['Nome do Item', 'Marca/Modelo', 'Quantidade em Estoque', 'Estoque Mínimo']], use_container_width=True)
    else:
        st.success("Tudo certo! Nenhum item com estoque baixo.")

def page_my_stock():
    st.title("Meu Estoque")
    df = st.session_state.get('stock_df', pd.DataFrame())
    
    if df.empty:
        st.info("Seu estoque está vazio.")
        return
        
    df_editable = df.copy()
    df_editable["Excluir"] = False
    
    edited_df = st.data_editor(
        df_editable,
        hide_index=True,
        use_container_width=True,
        column_config={"ID": st.column_config.NumberColumn(disabled=True)}
    )

    if st.button("Salvar Alterações", type="primary"):
        # Itens para excluir
        ids_to_delete = edited_df[edited_df["Excluir"]]["ID"].tolist()
        
        # Itens que foram modificados (excluindo os marcados para deleção)
        final_df = edited_df[~edited_df["ID"].isin(ids_to_delete)].drop(columns=["Excluir"])
        
        st.session_state.stock_df = final_df
        if save_data(client, final_df):
            st.success("Estoque atualizado com sucesso!")
            st.rerun()

def page_add_item():
    st.title("Adicionar Novo Item")
    with st.form("add_item_form", clear_on_submit=True):
        st.subheader("Detalhes do Item")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do Item*", help="Obrigatório")
        marca = c1.text_input("Marca/Modelo")
        especificacao = c2.text_input("Tipo/Especificação")
        sku = c2.text_input("Código/SKU")
        
        st.subheader("Categorização e Fornecedor")
        df = st.session_state.get('stock_df', pd.DataFrame())
        categorias = [""] + sorted(df['Categoria'].unique().tolist())
        fornecedores = [""] + sorted(df['Fornecedor Principal'].unique().tolist())
        
        cat = st.selectbox("Categoria*", options=categorias, help="Obrigatório")
        forn = st.selectbox("Fornecedor Principal*", options=fornecedores, help="Obrigatório")
        
        st.subheader("Detalhes de Estoque e Custo")
        c3, c4, c5 = st.columns(3)
        qtd = c3.number_input("Quantidade em Estoque*", min_value=0.0, format="%.2f")
        est_min = c4.number_input("Estoque Mínimo*", min_value=0.0, format="%.2f")
        unidade = c5.text_input("Unidade de Medida*", help="Ex: Un, Cx, pct")
        preco = c3.number_input("Preço de Custo (R$)*", min_value=0.0, format="%.2f")
        
        obs = st.text_area("Observações")

        if st.form_submit_button("Adicionar Item ao Estoque", type="primary"):
            if not all([nome, cat, forn, unidade]):
                st.error("Por favor, preencha todos os campos obrigatórios (*).")
            else:
                novo_id = df['ID'].max() + 1 if not df.empty else 1
                novo_item = pd.DataFrame([{
                    "ID": novo_id, "Nome do Item": nome, "Marca/Modelo": marca,
                    "Tipo/Especificação": especificacao, "Categoria": cat,
                    "Fornecedor Principal": forn, "Quantidade em Estoque": qtd,
                    "Estoque Mínimo": est_min, "Unidade de Medida": unidade,
                    "Preço de Custo": preco, "Código/SKU": sku, "Observações": obs,
                    "Data da Última Compra": datetime.now().strftime("%Y-%m-%d")
                }])
                
                updated_df = pd.concat([df, novo_item], ignore_index=True)
                st.session_state.stock_df = updated_df
                if save_data(client, updated_df):
                    st.success(f"Item '{nome}' adicionado com sucesso!")

def page_shopping_list():
    st.title("Lista de Compras")
    st.info("Esta lista mostra todos os itens que atingiram ou estão abaixo do estoque mínimo.")
    
    df = st.session_state.get('stock_df', pd.DataFrame())
    shopping_list_df = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].copy()

    if shopping_list_df.empty:
        st.success("Sua lista de compras está vazia!")
    else:
        shopping_list_df['Quantidade a Comprar'] = shopping_list_df['Estoque Mínimo'] - shopping_list_df['Quantidade em Estoque']
        st.dataframe(
            shopping_list_df[['Nome do Item', 'Marca/Modelo', 'Fornecedor Principal', 'Quantidade em Estoque', 'Estoque Mínimo', 'Quantidade a Comprar']],
            use_container_width=True
        )

def page_registrations():
    st.title("Cadastros")
    df = st.session_state.get('stock_df', pd.DataFrame())
    
    tab1, tab2 = st.tabs(["Gerenciar Fornecedores", "Gerenciar Categorias"])

    with tab1:
        st.subheader("Fornecedores")
        fornecedores = sorted(df['Fornecedor Principal'].unique().tolist())
        st.write(fornecedores)
        # A lógica de adição/remoção aqui exigiria atualizar todas as linhas
        # correspondentes na planilha, o que é mais complexo.
        st.info("Para adicionar ou remover fornecedores, edite diretamente na planilha ou adicione um item com o novo fornecedor.")

    with tab2:
        st.subheader("Categorias")
        categorias = sorted(df['Categoria'].unique().tolist())
        st.write(categorias)
        st.info("Para adicionar ou remover categorias, edite diretamente na planilha ou adicione um item com a nova categoria.")

# =============================================================================
# NAVEGAÇÃO E RENDERIZAÇÃO PRINCIPAL
# =============================================================================
PAGES = {
    "Painel Principal": ("fa-solid fa-house", page_dashboard),
    "Meu Estoque": ("fa-solid fa-box-archive", page_my_stock),
    "Adicionar Item": ("fa-solid fa-plus-circle", page_add_item),
    "Lista de Compras": ("fa-solid fa-shopping-cart", page_shopping_list),
    "Cadastros": ("fa-solid fa-cogs", page_registrations),
}

def set_page(page_name):
    """Callback para definir a página atual."""
    st.session_state.page = page_name

def render_sidebar():
    with st.sidebar:
        st.markdown(f"<h1><i class='fa-solid fa-skull'></i> Studio Stock</h1>", unsafe_allow_html=True)
        st.markdown("---")
        
        if "page" not in st.session_state:
            st.session_state.page = "Painel Principal"

        for page_name, (icon, _) in PAGES.items():
            st.button(
                label=page_name,
                on_click=set_page,
                args=(page_name,),
                key=f"btn_{page_name}",
                use_container_width=True
            )
        
        st.markdown("---")
        st.info("Versão 3.0 | Conectado ao Google Sheets")

# Fluxo principal da aplicação
if not client:
    st.error("Falha na conexão com a base de dados. Verifique as configurações de 'secrets' do Streamlit.")
else:
    render_sidebar()
    page_icon, page_function = PAGES[st.session_state.page]
    page_function()
