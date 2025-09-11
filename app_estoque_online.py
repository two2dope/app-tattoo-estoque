import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import datetime
import io

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA E ESTILOS
# =============================================================================

st.set_page_config(
    page_title="Tattoo Estoque",
    page_icon="💀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injetando o CSS
# Refatorado para usar seletores mais estáveis e suportar a navegação com st.radio
custom_css = """
/* Importa a fonte Font Awesome */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

/* Estilos Gerais */
body {
    background-color: #0F172A;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #1E293B;
    padding-top: 2rem;
}

/* Esconde o label do st.radio */
[data-testid="stSidebar"] .st-emotion-cache-16txtl3 {
    padding-top: 0;
}
[data-testid="stSidebar"] .st-emotion-cache-16txtl3 label {
    display: none;
}

/* Estiliza os botões do st.radio para parecerem botões de navegação */
[data-testid="stSidebar"] div[role="radiogroup"] > div {
    margin-bottom: 0.5rem;
}
[data-testid="stSidebar"] div[role="radiogroup"] label {
    display: block;
    width: 100%;
    border-radius: 0.5rem;
    color: #FFFFFF;
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 0.75rem 1rem;
    font-size: 1rem;
    transition: background-color 0.3s ease, color 0.3s ease;
    cursor: pointer;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background-color: #334155;
    color: #FFFFFF;
}

/* Estiliza o botão ATIVO (selecionado) */
[data-testid="stSidebar"] div[role="radiogroup"] input:checked + div {
    background-color: #00A9FF;
    color: #FFFFFF;
}

/* Badge de Notificação */
.badge-container {
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
}
.badge {
    position: absolute;
    right: 15px;
    background-color: #EF4444; /* Vermelho */
    color: white;
    border-radius: 50%;
    padding: 2px 8px;
    font-size: 0.8rem;
    font-weight: bold;
}


/* Cards de Métricas no Painel Principal */
.metric-card {
    background-color: #1E293B;
    border-radius: 0.75rem;
    padding: 1.5rem;
    color: white;
    text-align: center;
    border: 1px solid #334155;
}

.metric-card .icon {
    font-size: 2.5rem;
    color: #00A9FF;
    margin-bottom: 1rem;
}

.metric-card h3 {
    font-size: 1.25rem;
    color: #CBD5E1;
    margin-bottom: 0.5rem;
}

.metric-card p {
    font-size: 2rem;
    font-weight: 600;
    color: #FFFFFF;
}

/* Logo na Sidebar */
.sidebar-logo {
    font-size: 3rem;
    color: #00A9FF;
    text-align: center;
    display: block;
    margin-bottom: 1.5rem;
}
"""
st.markdown(f'<style>{custom_css}</style>', unsafe_allow_html=True)


# =============================================================================
# CONEXÃO COM GOOGLE SHEETS
# =============================================================================

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
EXPECTED_COLUMNS = [
    'ID', 'Nome do Item', 'Marca/Modelo', 'Tipo/Especificação', 'Categoria', 
    'Fornecedor Principal', 'Quantidade em Estoque', 'Estoque Mínimo', 
    'Unidade de Medida', 'Preço de Custo', 'Observações', 'Data da Última Compra'
]

@st.cache_resource(ttl=600)
def get_gspread_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=60)
def load_data():
    try:
        client = get_gspread_client()
        sheet = client.open("BaseDeDados_Estoque").worksheet("estoque")
        records = sheet.get_all_records()
        
        if not records:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
            
        df = pd.DataFrame(records)
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = ''
        
        numeric_cols = ['ID', 'Quantidade em Estoque', 'Estoque Mínimo', 'Preço de Custo']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Garante que ID seja inteiro
        df['ID'] = df['ID'].astype(int)

        return df[EXPECTED_COLUMNS]

    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Planilha 'BaseDeDados_Estoque' não encontrada.")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    except gspread.exceptions.WorksheetNotFound:
        st.error("Aba 'estoque' não encontrada.")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

def save_data(df):
    try:
        df_to_save = df.fillna('').copy()
        client = get_gspread_client()
        sheet = client.open("BaseDeDados_Estoque").worksheet("estoque")
        sheet.clear()
        
        header = df_to_save.columns.values.tolist()
        data_to_insert = df_to_save.values.tolist()
        sheet.update([header] + data_to_insert)

        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar os dados: {e}")
        return False

# =============================================================================
# GERAÇÃO DE PDF
# =============================================================================

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Lista de Compras - Tattoo Estoque', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')
        self.cell(0, 10, f'Gerado em: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 0, 'R')

    def create_table(self, data, headers):
        self.set_fill_color(224, 235, 255)
        self.set_font('Arial', 'B', 10)
        col_widths = [60, 40, 30, 30, 30] 
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, header, 1, 0, 'C', 1)
        self.ln()

        self.set_font('Arial', '', 10)
        fill = False
        for row in data:
            for i, item in enumerate(row):
                self.cell(col_widths[i], 6, str(item), 1, 0, 'L', fill)
            self.ln()
            fill = not fill

# =============================================================================
# INICIALIZAÇÃO E ESTADO DA SESSÃO
# =============================================================================

if 'page' not in st.session_state:
    st.session_state.page = 'Painel Principal'

if 'session_items' not in st.session_state:
    st.session_state.session_items = []

df = load_data()

# =============================================================================
# SIDEBAR / NAVEGAÇÃO
# =============================================================================

with st.sidebar:
    st.markdown('<i class="fa-solid fa-skull sidebar-logo"></i>', unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: white; margin-bottom: 2rem;'>Tattoo Estoque</h1>", unsafe_allow_html=True)

    items_in_alert_count = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]

    # Formata o label da lista de compras com o badge
    shopping_list_label = "🛒 Lista de Compras"
    if items_in_alert_count > 0:
        shopping_list_html = f"""
        <div class="badge-container">
            {shopping_list_label}
            <span class="badge">{items_in_alert_count}</span>
        </div>
        """
        shopping_list_label_display = shopping_list_html
    else:
        shopping_list_label_display = shopping_list_label

    PAGES = {
        "Painel Principal": "🏠 Painel Principal",
        "Meu Estoque": "📦 Meu Estoque",
        "Adicionar Item": "➕ Adicionar Item",
        "Registrar Uso": "✒️ Registrar Uso",
        "Lista de Compras": shopping_list_label_display,
        "Cadastros": "📂 Cadastros"
    }
    
    # Renderiza o radio com a opção que tem HTML
    page_selection = st.radio(
        "Navegação", 
        options=list(PAGES.keys()), 
        format_func=lambda page: PAGES[page],
        label_visibility="collapsed"
    )
    # Atualiza a session_state.page apenas se a seleção mudou
    if st.session_state.page != page_selection:
        st.session_state.page = page_selection
        st.rerun()
    
    # Rodapé da Sidebar
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #CBD5E1;'>Versão 2.1 Refatorada</p>", unsafe_allow_html=True)


# =============================================================================
# PÁGINAS DA APLICAÇÃO
# =============================================================================

# 5.1. Painel Principal (Dashboard)
if st.session_state.page == 'Painel Principal':
    st.title("Painel Principal")
    st.markdown("---")
    valor_total_estoque = (df['Quantidade em Estoque'] * df['Preço de Custo']).sum()
    total_itens_unicos = len(df)
    col1, col2, col3 = st.columns(3)
    col1.markdown(f'<div class="metric-card"><div class="icon"><i class="fa-solid fa-dollar-sign"></i></div><h3>Valor Total do Estoque</h3><p>R$ {valor_total_estoque:,.2f}</p></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card"><div class="icon"><i class="fa-solid fa-triangle-exclamation"></i></div><h3>Itens em Alerta</h3><p>{items_in_alert_count}</p></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card"><div class="icon"><i class="fa-solid fa-box-archive"></i></div><h3>Total de Itens Únicos</h3><p>{total_itens_unicos}</p></div>', unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("Itens Precisando de Reposição Urgente")
    df_alerta = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']]
    if df_alerta.empty:
        st.success("Nenhum item precisando de reposição no momento.")
    else:
        for _, row in df_alerta.iterrows():
            st.warning(f"**{row['Nome do Item']} ({row['Marca/Modelo']})** - Estoque: {row['Quantidade em Estoque']} / Mínimo: {row['Estoque Mínimo']}")

# 5.2. Meu Estoque
elif st.session_state.page == 'Meu Estoque':
    st.title("Meu Estoque")
    col1, col2 = st.columns([3, 1])
    search_query = col1.text_input("Buscar por Nome, Marca ou Tipo", placeholder="Digite para buscar...")
    categorias = ["Todas"] + sorted(df['Categoria'].unique().tolist())
    category_filter = col2.selectbox("Filtrar por Categoria", options=categorias)

    filtered_df = df.copy()
    if search_query:
        mask = (
            filtered_df['Nome do Item'].str.contains(search_query, case=False, na=False) |
            filtered_df['Marca/Modelo'].str.contains(search_query, case=False, na=False) |
            filtered_df['Tipo/Especificação'].str.contains(search_query, case=False, na=False)
        )
        filtered_df = filtered_df[mask]
    if category_filter != "Todas":
        filtered_df = filtered_df[filtered_df['Categoria'] == category_filter]

    st.markdown("Edite os dados diretamente na tabela e clique em 'Salvar Alterações'.")
    edited_df = st.data_editor(filtered_df, num_rows="dynamic", use_container_width=True, key="data_editor_estoque", hide_index=True)

    if st.button("Salvar Alterações"):
        with st.spinner("Salvando..."):
            # BUG FIX: Atualiza o DF principal apenas com as linhas editadas, preservando o resto.
            df_copy = df.copy().set_index('ID')
            edited_df_indexed = pd.DataFrame(edited_df).set_index('ID')
            df_copy.update(edited_df_indexed)
            
            if save_data(df_copy.reset_index()):
                st.success("Estoque atualizado com sucesso!")
                st.rerun()
            else:
                st.error("Falha ao salvar. Tente novamente.")

# 5.3. Adicionar Item
elif st.session_state.page == 'Adicionar Item':
    st.title("Adicionar Novo Item ao Estoque")
    with st.form(key="add_item_form"):
        col1, col2 = st.columns(2)
        nome_item = col1.text_input("Nome do Item", max_chars=100)
        marca_modelo = col2.text_input("Marca/Modelo", max_chars=100)
        
        col1, col2 = st.columns(2)
        tipo_especificacao = col1.text_input("Tipo/Especificação", placeholder="Ex: Agulha 7RL, Tinta preta", max_chars=100)
        fornecedores = ["<Adicionar Novo>"] + sorted(df['Fornecedor Principal'].astype(str).unique().tolist())
        fornecedor_selecionado = col2.selectbox("Fornecedor Principal", fornecedores)
        fornecedor_principal = col2.text_input("Nome do Novo Fornecedor") if fornecedor_selecionado == "<Adicionar Novo>" else fornecedor_selecionado

        col1, col2 = st.columns(2)
        categorias = ["<Adicionar Novo>"] + sorted(df['Categoria'].astype(str).unique().tolist())
        categoria_selecionada = col1.selectbox("Categoria", categorias)
        categoria = col1.text_input("Nome da Nova Categoria") if categoria_selecionada == "<Adicionar Novo>" else categoria_selecionada
        unidade_medida = col2.selectbox("Unidade de Medida", ["Unidade(s)", "Caixa(s)", "Frasco(s)", "Pacote(s)", "Rolo(s)"])
        
        col1, col2, col3 = st.columns(3)
        qtd_estoque = col1.number_input("Quantidade em Estoque", min_value=0, step=1)
        estoque_minimo = col2.number_input("Estoque Mínimo", min_value=0, step=1)
        preco_custo = col3.number_input("Preço de Custo (R$)", min_value=0.0, format="%.2f")

        col1, col2 = st.columns(2)
        observacoes = col1.text_area("Observações")
        data_ultima_compra = col2.date_input("Data da Última Compra", datetime.date.today())

        if st.form_submit_button(label="Adicionar Item"):
            if not nome_item or not categoria or not fornecedor_principal:
                st.warning("Preencha os campos obrigatórios: Nome do Item, Categoria e Fornecedor.")
            else:
                novo_id = df['ID'].max() + 1 if not df.empty else 1
                new_item_data = pd.DataFrame([{
                    'ID': novo_id, 'Nome do Item': nome_item, 'Marca/Modelo': marca_modelo,
                    'Tipo/Especificação': tipo_especificacao, 'Categoria': categoria,
                    'Fornecedor Principal': fornecedor_principal, 'Quantidade em Estoque': qtd_estoque,
                    'Estoque Mínimo': estoque_minimo, 'Unidade de Medida': unidade_medida,
                    'Preço de Custo': preco_custo, 'Observações': observacoes,
                    'Data da Última Compra': data_ultima_compra.strftime("%Y-%m-%d")
                }])
                df_atualizado = pd.concat([df, new_item_data], ignore_index=True)
                if save_data(df_atualizado):
                    st.success("Item adicionado com sucesso!")
                else:
                    st.error("Falha ao adicionar o item.")

# 5.4. Registrar Uso
elif st.session_state.page == 'Registrar Uso':
    st.title("Registrar Uso de Material")
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.subheader("Adicionar Itens Consumidos")
        # REFACTOR: Usa ID para buscar o item, evitando bugs com nomes duplicados
        item_options = df.set_index('ID').apply(lambda row: f"{row['Nome do Item']} ({row['Marca/Modelo']}) - Estoque: {row['Quantidade em Estoque']}", axis=1)
        selected_id = st.selectbox("Buscar item no estoque...", options=[""] + list(item_options.index), format_func=lambda id: item_options.get(id, ""))
        if selected_id:
            item_selecionado = df.loc[df['ID'] == selected_id].iloc[0]
            max_qty = int(item_selecionado['Quantidade em Estoque'])
            quantidade_usada = st.number_input("Quantidade Utilizada", min_value=1, max_value=max_qty, step=1, key=f"qty_{item_selecionado['ID']}")
            if st.button("Adicionar à Sessão"):
                st.session_state.session_items.append({
                    "ID": item_selecionado['ID'],
                    "Nome": f"{item_selecionado['Nome do Item']} ({item_selecionado['Marca/Modelo']})",
                    "Quantidade": quantidade_usada
                })
                st.rerun()
    with col2:
        st.subheader("Itens da Sessão")
        if not st.session_state.session_items:
            st.info("Nenhum item adicionado à sessão.")
        else:
            for item in st.session_state.session_items:
                st.write(f"- {item['Nome']}: {item['Quantidade']}")
        if st.session_state.session_items:
            if st.button("Confirmar Uso", type="primary", use_container_width=True):
                df_copy = df.copy().set_index('ID')
                for item_sessao in st.session_state.session_items:
                    df_copy.loc[item_sessao['ID'], 'Quantidade em Estoque'] -= item_sessao['Quantidade']
                if save_data(df_copy.reset_index()):
                    st.success("Uso registrado e estoque atualizado!")
                    st.session_state.session_items = []
                    st.rerun()
                else:
                    st.error("Erro ao salvar as alterações.")

# 5.5. Lista de Compras
elif st.session_state.page == 'Lista de Compras':
    st.title("Lista de Compras")
    st.markdown("Itens que atingiram ou estão abaixo do estoque mínimo definido.")
    df_compras = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].copy()
    if df_compras.empty:
        st.success("Tudo em ordem! Nenhum item na lista de compras.")
    else:
        df_compras['Qtd. a Comprar (Sugestão)'] = (df_compras['Estoque Mínimo'] - df_compras['Quantidade em Estoque']).apply(lambda x: max(1, x))
        display_cols = {'Nome do Item': 'Item (Nome/Marca/Tipo)', 'Fornecedor Principal': 'Fornecedor', 'Quantidade em Estoque': 'Estoque Atual', 'Estoque Mínimo': 'Estoque Mínimo', 'Qtd. a Comprar (Sugestão)': 'Qtd. a Comprar'}
        df_display = df_compras[display_cols.keys()].rename(columns=display_cols)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        if st.button("🖨️ Imprimir em PDF"):
            pdf = PDF()
            pdf.add_page()
            pdf_data = df_display.values.tolist()
            pdf_headers = df_display.columns.tolist()
            pdf.create_table(pdf_data, pdf_headers)
            pdf_buffer = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
            st.download_button(label="Baixar Lista de Compras em PDF", data=pdf_buffer, file_name="lista_de_compras.pdf", mime="application/pdf")

# 5.6. Cadastros
elif st.session_state.page == 'Cadastros':
    st.title("Gerenciar Cadastros")
    tab1, tab2 = st.tabs(["Fornecedores", "Categorias"])
    with tab1:
        st.subheader("Fornecedores Cadastrados")
        fornecedores_unicos = sorted(df['Fornecedor Principal'].dropna().unique().tolist())
        st.info('\n'.join(f"- {f}" for f in fornecedores_unicos) if fornecedores_unicos else "Nenhum fornecedor cadastrado.")
    with tab2:
        st.subheader("Categorias Cadastradas")
        categorias_unicas = sorted(df['Categoria'].dropna().unique().tolist())
        st.info('\n'.join(f"- {c}" for c in categorias_unicas) if categorias_unicas else "Nenhuma categoria cadastrada.")

