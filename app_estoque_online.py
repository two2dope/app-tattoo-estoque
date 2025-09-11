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

# Função para carregar o CSS customizado
def load_css():
    """Carrega o CSS customizado para estilizar a aplicação."""
    with open("style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Injetando o CSS
# (Nota: Em um ambiente real, o ideal é ter o style.css no mesmo diretório. 
# Para este script único, o CSS será definido aqui.)
custom_css = """
/* Importa a fonte Font Awesome */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

/* Estilos Gerais */
body {
    background-color: #0F172A; /* Cor de fundo principal */
}

/* Sidebar */
.st-emotion-cache-16txtl3 {
    background-color: #1E293B; /* Cor de fundo da sidebar */
    padding-top: 2rem;
}

/* Botões da Sidebar */
.stButton>button {
    width: 100%;
    border-radius: 0.5rem;
    color: #FFFFFF;
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 1rem;
    transition: background-color 0.3s ease, color 0.3s ease;
}

.stButton>button:hover {
    background-color: #334155;
    color: #FFFFFF;
}

.stButton>button:focus {
    background-color: #00A9FF;
    color: #FFFFFF;
    box-shadow: none;
    outline: none;
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

/* Badge de Notificação */
.badge-container {
    position: relative;
    display: inline-block;
    width: 100%;
}

.badge {
    position: absolute;
    top: 50%;
    right: 15px;
    transform: translateY(-50%);
    background-color: #EF4444; /* Vermelho */
    color: white;
    border-radius: 50%;
    padding: 2px 8px;
    font-size: 0.8rem;
    font-weight: bold;
    line-height: 1.2;
}
"""
st.markdown(f'<style>{custom_css}</style>', unsafe_allow_html=True)


# =============================================================================
# CONEXÃO COM GOOGLE SHEETS
# =============================================================================

# Define o escopo de acesso da API
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Schema esperado da planilha
EXPECTED_COLUMNS = [
    'ID', 'Nome do Item', 'Marca/Modelo', 'Tipo/Especificação', 'Categoria', 
    'Fornecedor Principal', 'Quantidade em Estoque', 'Estoque Mínimo', 
    'Unidade de Medida', 'Preço de Custo', 'Observações', 'Data da Última Compra'
]

@st.cache_resource(ttl=600)
def get_gspread_client():
    """Retorna um cliente gspread autenticado."""
    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
    }
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=60)
def load_data():
    """Carrega os dados da planilha Google Sheets."""
    try:
        client = get_gspread_client()
        sheet = client.open("BaseDeDados_Estoque").worksheet("estoque")
        records = sheet.get_all_records()
        
        if not records:
            # Planilha vazia, retorna DataFrame com a estrutura correta
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
            
        df = pd.DataFrame(records)

        # Garante que todas as colunas esperadas existam
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = ''
        
        # Converte colunas numéricas, tratando erros
        numeric_cols = ['Quantidade em Estoque', 'Estoque Mínimo', 'Preço de Custo']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df[EXPECTED_COLUMNS] # Garante a ordem correta

    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Planilha 'BaseDeDados_Estoque' não encontrada. Verifique o nome e as permissões.")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    except gspread.exceptions.WorksheetNotFound:
        st.error("Aba 'estoque' não encontrada na planilha. Verifique o nome da aba.")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

def save_data(df):
    """Salva o DataFrame de volta na planilha Google Sheets."""
    try:
        # Garante que o DataFrame a ser salvo não contenha NaNs
        df_to_save = df.fillna('').copy()

        client = get_gspread_client()
        sheet = client.open("BaseDeDados_Estoque").worksheet("estoque")
        
        # Limpa a planilha antes de inserir os novos dados
        sheet.clear()
        
        # Escreve o cabeçalho e depois os dados
        header = df_to_save.columns.values.tolist()
        data_to_insert = df_to_save.values.tolist()
        sheet.update([header] + data_to_insert)

        # Limpa o cache para forçar o recarregamento dos dados
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
        
        # Largura das colunas (ajuste conforme necessário)
        col_widths = [60, 40, 30, 30, 30] 
        
        # Cabeçalho
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, header, 1, 0, 'C', 1)
        self.ln()

        # Dados
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

# Carrega os dados
df = load_data()

# =============================================================================
# SIDEBAR / NAVEGAÇÃO
# =============================================================================

with st.sidebar:
    st.markdown('<i class="fa-solid fa-skull sidebar-logo"></i>', unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: white; margin-bottom: 2rem;'>Tattoo Estoque</h1>", unsafe_allow_html=True)

    if st.button("🏠 Painel Principal"):
        st.session_state.page = 'Painel Principal'
    if st.button("📦 Meu Estoque"):
        st.session_state.page = 'Meu Estoque'
    if st.button("➕ Adicionar Item"):
        st.session_state.page = 'Adicionar Item'
    if st.button("✒️ Registrar Uso"):
        st.session_state.page = 'Registrar Uso'

    # Botão Lista de Compras com badge
    items_in_alert_count = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]
    button_label = "🛒 Lista de Compras"
    
    if items_in_alert_count > 0:
        st.markdown(
            f"""
            <div class="badge-container">
                <button class="stButton" style="width:100%;" onclick="document.querySelector('[data-testid=\"stMarkdownContainer\"] .stButton>button:nth-of-type(5)').click()">
                    {button_label}
                </button>
                <span class="badge">{items_in_alert_count}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Botão invisível para acionar a lógica do Streamlit
        if st.button(button_label, key="hidden_shopping_list_btn", type="primary"):
            st.session_state.page = 'Lista de Compras'
    else:
        if st.button(button_label):
            st.session_state.page = 'Lista de Compras'

    if st.button("📂 Cadastros"):
        st.session_state.page = 'Cadastros'

    # Rodapé da Sidebar
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #CBD5E1;'>Versão 2.0</p>", 
        unsafe_allow_html=True
    )


# =============================================================================
# PÁGINAS DA APLICAÇÃO
# =============================================================================

# ---------------------------------
# 5.1. Painel Principal (Dashboard)
# ---------------------------------
if st.session_state.page == 'Painel Principal':
    st.title("Painel Principal")
    st.markdown("---")

    # Métricas
    valor_total_estoque = (df['Quantidade em Estoque'] * df['Preço de Custo']).sum()
    itens_em_alerta = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]
    total_itens_unicos = len(df)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="icon"><i class="fa-solid fa-dollar-sign"></i></div>
            <h3>Valor Total do Estoque</h3>
            <p>R$ {valor_total_estoque:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
            <h3>Itens em Alerta</h3>
            <p>{itens_em_alerta}</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="icon"><i class="fa-solid fa-box-archive"></i></div>
            <h3>Total de Itens Únicos</h3>
            <p>{total_itens_unicos}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Itens precisando de reposição
    st.subheader("Itens Precisando de Reposição Urgente")
    df_alerta = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']]

    if df_alerta.empty:
        st.success("Nenhum item precisando de reposição no momento.")
    else:
        for index, row in df_alerta.iterrows():
            st.warning(
                f"**{row['Nome do Item']} ({row['Marca/Modelo']})** - "
                f"Estoque: {row['Quantidade em Estoque']} / Mínimo: {row['Estoque Mínimo']}"
            )


# ---------------------------------
# 5.2. Meu Estoque
# ---------------------------------
elif st.session_state.page == 'Meu Estoque':
    st.title("Meu Estoque")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Buscar por Nome, Marca ou Tipo", placeholder="Digite para buscar...")
    with col2:
        categorias = ["Todas"] + sorted(df['Categoria'].unique().tolist())
        category_filter = st.selectbox("Filtrar por Categoria", options=categorias)

    # Lógica de filtro
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df['Nome do Item'].str.contains(search_query, case=False, na=False) |
            filtered_df['Marca/Modelo'].str.contains(search_query, case=False, na=False) |
            filtered_df['Tipo/Especificação'].str.contains(search_query, case=False, na=False)
        ]
    if category_filter != "Todas":
        filtered_df = filtered_df[filtered_df['Categoria'] == category_filter]

    st.markdown("Edite os dados diretamente na tabela e clique em 'Salvar Alterações'.")
    
    edited_df = st.data_editor(
        filtered_df,
        num_rows="dynamic",
        use_container_width=True,
        key="data_editor_estoque",
        hide_index=True
    )

    if st.button("Salvar Alterações"):
        with st.spinner("Salvando..."):
            if save_data(edited_df):
                st.success("Estoque atualizado com sucesso!")
                st.rerun()
            else:
                st.error("Falha ao salvar. Tente novamente.")

# ---------------------------------
# 5.3. Adicionar Item
# ---------------------------------
elif st.session_state.page == 'Adicionar Item':
    st.title("Adicionar Novo Item ao Estoque")

    with st.form(key="add_item_form"):
        # Linha 1: Nome, Marca/Modelo
        col1, col2 = st.columns(2)
        with col1:
            nome_item = st.text_input("Nome do Item", max_chars=100)
        with col2:
            marca_modelo = st.text_input("Marca/Modelo", max_chars=100)
            
        # Linha 2: Tipo, Fornecedor
        col1, col2 = st.columns(2)
        with col1:
            tipo_especificacao = st.text_input("Tipo/Especificação", placeholder="Ex: Agulha 7RL, Tinta preta", max_chars=100)

        with col2:
            fornecedores = sorted(df['Fornecedor Principal'].unique().tolist())
            fornecedor_selecionado = st.selectbox(
                "Fornecedor Principal", ["<Adicionar Novo>"] + fornecedores
            )
            if fornecedor_selecionado == "<Adicionar Novo>":
                fornecedor_principal = st.text_input("Nome do Novo Fornecedor")
            else:
                fornecedor_principal = fornecedor_selecionado

        # Linha 3: Categoria, Unidade de Medida
        col1, col2 = st.columns(2)
        with col1:
            categorias = sorted(df['Categoria'].unique().tolist())
            categoria_selecionada = st.selectbox(
                "Categoria", ["<Adicionar Novo>"] + categorias
            )
            if categoria_selecionada == "<Adicionar Novo>":
                categoria = st.text_input("Nome da Nova Categoria")
            else:
                categoria = categoria_selecionada

        with col2:
            unidade_medida = st.selectbox(
                "Unidade de Medida",
                ["Unidade(s)", "Caixa(s)", "Frasco(s)", "Pacote(s)", "Rolo(s)"]
            )
            
        # Linha 4: Quantidade, Estoque Mínimo, Preço
        col1, col2, col3 = st.columns(3)
        with col1:
            qtd_estoque = st.number_input("Quantidade em Estoque", min_value=0, step=1)
        with col2:
            estoque_minimo = st.number_input("Estoque Mínimo", min_value=0, step=1)
        with col3:
            preco_custo = st.number_input("Preço de Custo (R$)", min_value=0.0, format="%.2f")

        # Linha 5: Observações, Data
        col1, col2 = st.columns(2)
        with col1:
             observacoes = st.text_area("Observações")
        with col2:
             data_ultima_compra = st.date_input("Data da Última Compra", datetime.date.today())

        # Botão de submit
        submit_button = st.form_submit_button(label="Adicionar Item")

        if submit_button:
            if not nome_item or not categoria or not fornecedor_principal:
                st.warning("Preencha os campos obrigatórios: Nome do Item, Categoria e Fornecedor.")
            else:
                novo_id = df['ID'].max() + 1 if not df.empty else 1
                new_item_data = {
                    'ID': novo_id, 'Nome do Item': nome_item, 'Marca/Modelo': marca_modelo,
                    'Tipo/Especificação': tipo_especificacao, 'Categoria': categoria,
                    'Fornecedor Principal': fornecedor_principal, 'Quantidade em Estoque': qtd_estoque,
                    'Estoque Mínimo': estoque_minimo, 'Unidade de Medida': unidade_medida,
                    'Preço de Custo': preco_custo, 'Observações': observacoes,
                    'Data da Última Compra': data_ultima_compra.strftime("%Y-%m-%d")
                }
                
                df_atualizado = pd.concat([df, pd.DataFrame([new_item_data])], ignore_index=True)
                
                with st.spinner("Salvando..."):
                    if save_data(df_atualizado):
                        st.success("Item adicionado com sucesso!")
                    else:
                        st.error("Falha ao adicionar o item.")


# ---------------------------------
# 5.4. Registrar Uso
# ---------------------------------
elif st.session_state.page == 'Registrar Uso':
    st.title("Registrar Uso de Material")
    
    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.subheader("Adicionar Itens Consumidos")
        
        # Cria uma lista de nomes de item para o selectbox
        item_options = df.apply(lambda row: f"{row['Nome do Item']} ({row['Marca/Modelo']}) - Estoque: {row['Quantidade em Estoque']}", axis=1).tolist()
        
        selected_item_str = st.selectbox("Buscar item no estoque...", options=[""] + item_options)

        if selected_item_str:
            # Extrai o nome do item da string selecionada
            item_name_to_find = selected_item_str.split(' (')[0]
            item_selecionado = df[df['Nome do Item'] == item_name_to_find].iloc[0]

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
                df_copy = df.copy()
                try:
                    for item_sessao in st.session_state.session_items:
                        item_id = item_sessao['ID']
                        qty_used = item_sessao['Quantidade']
                        
                        # Localiza o índice do item no DataFrame
                        idx = df_copy.index[df_copy['ID'] == item_id].tolist()[0]
                        
                        # Subtrai a quantidade
                        df_copy.loc[idx, 'Quantidade em Estoque'] -= qty_used

                    with st.spinner("Atualizando estoque..."):
                        if save_data(df_copy):
                            st.success("Uso registrado e estoque atualizado com sucesso!")
                            st.session_state.session_items = [] # Limpa a sessão
                            st.rerun()
                        else:
                            st.error("Erro ao salvar as alterações no estoque.")

                except Exception as e:
                    st.error(f"Ocorreu um erro ao processar o uso: {e}")

# ---------------------------------
# 5.5. Lista de Compras
# ---------------------------------
elif st.session_state.page == 'Lista de Compras':
    st.title("Lista de Compras")
    st.markdown("Esta lista mostra todos os itens que atingiram ou estão abaixo do estoque mínimo definido.")

    df_compras = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].copy()
    
    if df_compras.empty:
        st.success("Tudo em ordem! Nenhum item na lista de compras.")
    else:
        df_compras['Qtd. a Comprar (Sugestão)'] = df_compras['Estoque Mínimo'] - df_compras['Quantidade em Estoque']
        
        # Garante que a sugestão seja no mínimo 1
        df_compras['Qtd. a Comprar (Sugestão)'] = df_compras['Qtd. a Comprar (Sugestão)'].apply(lambda x: max(1, x))

        # Seleciona e renomeia colunas para exibição
        display_cols = {
            'Nome do Item': 'Item (Nome/Marca/Tipo)',
            'Fornecedor Principal': 'Fornecedor',
            'Quantidade em Estoque': 'Estoque Atual',
            'Estoque Mínimo': 'Estoque Mínimo',
            'Qtd. a Comprar (Sugestão)': 'Qtd. a Comprar (Sugestão)'
        }
        df_display = df_compras[display_cols.keys()].rename(columns=display_cols)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        if st.button("🖨️ Imprimir em PDF"):
            pdf = PDF()
            pdf.add_page()
            
            pdf_data = df_display.values.tolist()
            pdf_headers = df_display.columns.tolist()
            
            pdf.create_table(pdf_data, pdf_headers)

            # Salva o PDF em um buffer de bytes
            pdf_buffer = io.BytesIO()
            pdf.output(pdf_buffer)
            pdf_buffer.seek(0)

            st.download_button(
                label="Baixar Lista de Compras em PDF",
                data=pdf_buffer,
                file_name="lista_de_compras_tattoo_estoque.pdf",
                mime="application/pdf"
            )

# ---------------------------------
# 5.6. Cadastros
# ---------------------------------
elif st.session_state.page == 'Cadastros':
    st.title("Gerenciar Cadastros")

    tab1, tab2 = st.tabs(["Fornecedores", "Categorias"])

    with tab1:
        st.subheader("Fornecedores Cadastrados")
        fornecedores_unicos = sorted(df['Fornecedor Principal'].unique().tolist())
        if fornecedores_unicos:
            for fornecedor in fornecedores_unicos:
                st.info(fornecedor)
        else:
            st.write("Nenhum fornecedor cadastrado.")
        st.caption("Novos fornecedores são adicionados na tela 'Adicionar Item'.")
        
    with tab2:
        st.subheader("Categorias Cadastradas")
        categorias_unicas = sorted(df['Categoria'].unique().tolist())
        if categorias_unicas:
            for categoria in categorias_unicas:
                st.info(categoria)
        else:
            st.write("Nenhuma categoria cadastrada.")
        st.caption("Novas categorias são adicionadas na tela 'Adicionar Item'.")
