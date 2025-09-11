import streamlit as st
import pandas as pd
from gspread_pandas import Spread, Client
from google.oauth2.service_account import Credentials
import gspread

# =============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA E ESTILO
# =============================================================================

st.set_page_config(
    page_title="Studio Stock",
    page_icon="🎨",
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
            body {
                color: #E0E0E0;
            }
            .stApp {
                background-color: #0F172A;
            }
            h1, h2, h3 {
                color: #FFFFFF;
            }
            
            /* Sidebar */
            .css-1d391kg {
                background-color: #1E293B;
                border-right: 1px solid #334155;
            }
            .css-1d391kg .st-emotion-cache-1fttcpj, .css-1d391kg .st-emotion-cache-1v0mbdj {
                color: #E0E0E0;
            }
            /* Botão de navegação ativo */
            .st-emotion-cache-1v0mbdj.e115fcil2 {
                background-color: #0F172A;
                border-radius: 5px;
            }
            
            /* Contêineres principais */
            .main-container {
                background-color: #1E293B;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }

            /* Tabela de dados (Meu Estoque) */
            .stDataFrame {
                border-radius: 8px;
            }
            
            /* Cards do Dashboard */
            .metric-card {
                background-color: #334155;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                border: 1px solid #475569;
            }
            .metric-card i {
                font-size: 2.5rem;
                margin-bottom: 10px;
                color: #00A9FF; /* Cor do ícone */
            }
            .metric-card .metric-value {
                font-size: 2rem;
                font-weight: bold;
                color: #FFFFFF;
            }
            .metric-card .metric-label {
                font-size: 1rem;
                color: #94A3B8;
            }
            
            /* Alertas e Botões */
            .stButton>button {
                background-color: #00A9FF;
                color: white;
                border-radius: 8px;
                border: none;
            }
            .stButton>button:hover {
                background-color: #0087CC;
                color: white;
            }
            .st-emotion-cache-19n60e.e1b2p2lg4 { /* Botão de exclusão */
                 background-color: #DC3545 !important;
            }
        </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# CONEXÃO COM GOOGLE SHEETS (BACKEND)
# =============================================================================

# Define o escopo de permissões
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Função para conectar ao Google Sheets de forma segura
@st.cache_resource
def get_gspread_client():
    try:
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
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
        }
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        return None

# Função para carregar os dados do estoque
@st.cache_data(ttl=60) # Cache de 1 minuto
def load_stock_data(_client, sheet_name="BaseDeDados_Estoque", worksheet_name="estoque"):
    try:
        spreadsheet = _client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        df = pd.DataFrame(worksheet.get_all_records())
        # Garantir tipos de dados corretos
        numeric_cols = ['Quantidade em Estoque', 'Estoque Mínimo', 'Preço de Custo']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"A planilha '{worksheet_name}' não foi encontrada em '{sheet_name}'. Verifique os nomes.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Não foi possível carregar os dados: {e}")
        return pd.DataFrame()

# Função para salvar os dados no estoque
def save_stock_data(client, df, sheet_name="BaseDeDados_Estoque", worksheet_name="estoque"):
    try:
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
        # Converte o DataFrame para lista de listas para o gspread
        data_to_save = [df.columns.values.tolist()] + df.values.tolist()
        worksheet.update(data_to_save)
        st.cache_data.clear() # Limpa o cache para recarregar os dados
    except Exception as e:
        st.error(f"Erro ao salvar os dados: {e}")

# Inicializa o cliente e carrega os dados
client = get_gspread_client()
if client:
    if 'stock_df' not in st.session_state:
        st.session_state.stock_df = load_stock_data(client)
else:
    st.session_state.stock_df = pd.DataFrame() # Fallback para DataFrame vazio

# Placeholder para outros cadastros (Fornecedores, Categorias) - pode ser outra aba na planilha
# Por simplicidade, vamos gerenciá-los a partir dos dados existentes
def get_unique_values(column_name):
    if not st.session_state.stock_df.empty and column_name in st.session_state.stock_df.columns:
        return sorted(st.session_state.stock_df[column_name].unique().tolist())
    return []


# =============================================================================
# DEFINIÇÃO DAS PÁGINAS (VIEWS)
# =============================================================================

# --- 1. PAINEL PRINCIPAL (DASHBOARD) ---
def page_dashboard():
    st.title("Painel Principal")
    st.markdown("---")

    df = st.session_state.stock_df
    if df.empty:
        st.warning("Nenhum item no estoque. Adicione um item para começar.")
        return

    # Cards de Métricas
    total_value = (df['Quantidade em Estoque'] * df['Preço de Custo']).sum()
    items_in_alert = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]
    total_unique_items = df.shape[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <i class="fa-solid fa-gem"></i>
            <div class="metric-value">R$ {total_value:,.2f}</div>
            <div class="metric-label">Valor Total do Estoque</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <div class="metric-value">{items_in_alert}</div>
            <div class="metric-label">Itens em Alerta</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <i class="fa-solid fa-boxes-stacked"></i>
            <div class="metric-value">{total_unique_items}</div>
            <div class="metric-label">Total de Itens Únicos</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Lista de Reposição Urgente
    urgent_items = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']]
    if not urgent_items.empty:
        with st.container():
            st.subheader("Itens Precisando de Reposição Urgente")
            for _, row in urgent_items.iterrows():
                col_item, col_button = st.columns([4, 1])
                with col_item:
                     st.error(f"**{row['Nome do Item']}** ({row.get('Marca/Modelo', '')}) - Estoque: {row['Quantidade em Estoque']} / Mínimo: {row['Estoque Mínimo']}")
                with col_button:
                    if st.button("Ver na Lista", key=f"urgent_{row['ID']}"):
                        st.session_state.page = "Lista de Compras"
                        st.rerun()

# --- 2. MEU ESTOQUE ---
def page_my_stock():
    st.title("Meu Estoque")

    if st.session_state.stock_df.empty:
        st.info("Seu estoque está vazio.")
        if st.button("Adicionar Novo Item"):
            st.session_state.page = "Adicionar Item"
            st.rerun()
        return

    # Ferramentas de Busca e Filtro
    search_query = st.text_input("Buscar por nome, marca ou tipo...")
    categories = ["Todas as Categorias"] + get_unique_values("Categoria")
    selected_category = st.selectbox("Filtrar por Categoria", options=categories)

    filtered_df = st.session_state.stock_df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df['Nome do Item'].str.contains(search_query, case=False, na=False) |
            filtered_df['Marca/Modelo'].str.contains(search_query, case=False, na=False) |
            filtered_df['Tipo/Especificação'].str.contains(search_query, case=False, na=False)
        ]
    if selected_category != "Todas as Categorias":
        filtered_df = filtered_df[filtered_df['Categoria'] == selected_category]
    
    # Adicionar coluna de exclusão
    filtered_df['Excluir'] = False
    
    # Colunas a serem exibidas
    cols_to_display = ['Excluir', 'Nome do Item', 'Marca/Modelo', 'Categoria', 'Quantidade em Estoque', 'Estoque Mínimo', 'Preço de Custo', 'Unidade de Medida']
    
    st.info("Dê um duplo clique em uma célula para editar o valor. Pressione Enter para salvar.")
    
    # Editor de dados
    edited_df = st.data_editor(
        filtered_df[cols_to_display],
        key="stock_editor",
        num_rows="dynamic",
        hide_index=True
    )
    
    if st.button("Salvar Alterações", type="primary"):
        items_to_delete_indices = edited_df[edited_df['Excluir'] == True].index
        
        # Sincroniza as edições e exclusões com o DataFrame principal na session_state
        if not items_to_delete_indices.empty:
             # Mapeia os índices do DF filtrado de volta para o DF original
            original_indices_to_delete = filtered_df.iloc[items_to_delete_indices].index
            st.session_state.stock_df.drop(original_indices_to_delete, inplace=True)

        # Atualiza os dados editados (excluindo a coluna 'Excluir')
        update_df = edited_df.drop(columns=['Excluir'])
        update_df.index = filtered_df.index # Mantém os índices originais para a atualização
        st.session_state.stock_df.update(update_df)
        
        # Salva no Google Sheets
        save_stock_data(client, st.session_state.stock_df)
        st.success("Alterações salvas com sucesso!")
        st.rerun()


# --- 3. ADICIONAR ITEM ---
def page_add_item():
    st.title("Adicionar Novo Item")
    
    with st.form(key="add_item_form"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome do Item", placeholder="Ex: Cartucho Descartável")
            tipo = st.text_input("Tipo/Especificação", placeholder="Ex: 7RL Bold 0.35mm")
            categoria = st.selectbox("Categoria", options=get_unique_values("Categoria") + ["Nova Categoria..."])
            if categoria == "Nova Categoria...":
                categoria = st.text_input("Nome da Nova Categoria")

            qtd = st.number_input("Qtd. em Estoque", min_value=0.0, step=0.1, format="%.2f")
            unidade = st.selectbox("Unidade de Medida", options=["Unidade", "Caixa", "Frasco", "Par", "Rolo"])

        with c2:
            marca = st.text_input("Marca/Modelo", placeholder="Ex: Cheyenne Craft")
            sku = st.text_input("Código/SKU (Opcional)")
            fornecedor = st.selectbox("Fornecedor Principal", options=get_unique_values("Fornecedor Principal"))
            
            minimo = st.number_input("Estoque Mínimo", min_value=0, step=1)
            custo = st.number_input("Preço de Custo (R$)", min_value=0.0, format="%.2f")

        observacoes = st.text_area("Observações Adicionais")

        submit_button = st.form_submit_button(label="Salvar Item")

        if submit_button:
            if not nome or not categoria:
                st.error("Nome do Item e Categoria são obrigatórios.")
            else:
                new_id = (st.session_state.stock_df['ID'].max() + 1) if not st.session_state.stock_df.empty else 1
                new_item = pd.DataFrame([{
                    "ID": new_id,
                    "Nome do Item": nome,
                    "Marca/Modelo": marca,
                    "Tipo/Especificação": tipo,
                    "Categoria": categoria,
                    "Fornecedor Principal": fornecedor,
                    "Quantidade em Estoque": qtd,
                    "Estoque Mínimo": minimo,
                    "Unidade de Medida": unidade,
                    "Preço de Custo": custo,
                    "Código/SKU": sku,
                    "Observações": observacoes,
                    "Data da Última Compra": pd.to_datetime('today').strftime('%Y-%m-%d')
                }])
                
                st.session_state.stock_df = pd.concat([st.session_state.stock_df, new_item], ignore_index=True)
                save_stock_data(client, st.session_state.stock_df)
                st.success(f"Item '{nome}' adicionado com sucesso!")


# --- 4. REGISTRAR USO DE MATERIAL ---
def page_register_usage():
    st.title("Registrar Uso de Material")

    if 'session_items' not in st.session_state:
        st.session_state.session_items = []

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Adicionar Itens Consumidos")
        
        # Gerar uma lista de nomes para o selectbox
        item_names = st.session_state.stock_df.apply(
            lambda row: f"{row['Nome do Item']} ({row.get('Marca/Modelo', '')}) - Estoque: {row['Quantidade em Estoque']}", 
            axis=1
        ).tolist()
        
        selected_item_str = st.selectbox("Buscar item no estoque...", [""] + item_names)

        if selected_item_str:
            # Encontrar o índice do item selecionado
            selected_idx = item_names.index(selected_item_str)
            item_data = st.session_state.stock_df.iloc[selected_idx]
            
            qty_consumed = st.number_input(f"Quantidade de '{item_data['Nome do Item']}' a ser usada:", min_value=0.1, step=0.1, value=1.0, format="%.2f")
            
            if st.button("Adicionar à Sessão"):
                st.session_state.session_items.append({
                    "id": item_data['ID'],
                    "name": item_data['Nome do Item'],
                    "quantity": qty_consumed
                })
                st.rerun()

    with col2:
        st.subheader("Itens da Sessão")
        if not st.session_state.session_items:
            st.info("Nenhum item adicionado.")
        else:
            for i, item in enumerate(st.session_state.session_items):
                st.write(f"- {item['quantity']}x {item['name']}")
            
            st.markdown("---")
            if st.button("Confirmar Uso", type="primary"):
                for item_to_use in st.session_state.session_items:
                    # Encontra o item no DF principal e subtrai a quantidade
                    item_index = st.session_state.stock_df[st.session_state.stock_df['ID'] == item_to_use['id']].index
                    if not item_index.empty:
                        current_qty = st.session_state.stock_df.loc[item_index[0], 'Quantidade em Estoque']
                        st.session_state.stock_df.loc[item_index[0], 'Quantidade em Estoque'] = current_qty - item_to_use['quantity']

                save_stock_data(client, st.session_state.stock_df)
                st.success("Baixa no estoque realizada com sucesso!")
                st.session_state.session_items = [] # Limpa a sessão
                st.rerun()


# --- 5. LISTA DE COMPRAS ---
def page_shopping_list():
    st.title("Lista de Compras")
    st.info("Esta lista mostra todos os itens que atingiram ou estão abaixo do estoque mínimo definido.")
    
    shopping_list_df = st.session_state.stock_df[
        st.session_state.stock_df['Quantidade em Estoque'] <= st.session_state.stock_df['Estoque Mínimo']
    ].copy()

    if shopping_list_df.empty:
        st.success("Ótima notícia! Nenhum item precisa de reposição no momento.")
        return

    # Calcula a sugestão de compra (pode ser ajustada)
    shopping_list_df['Qtd. a Comprar (Sugestão)'] = shopping_list_df['Estoque Mínimo'] * 2 - shopping_list_df['Quantidade em Estoque']
    
    # Exibe a lista
    st.dataframe(
        shopping_list_df[['Nome do Item', 'Marca/Modelo', 'Fornecedor Principal', 'Estoque Mínimo', 'Quantidade em Estoque', 'Qtd. a Comprar (Sugestão)']],
        hide_index=True,
        use_container_width=True
    )

    # Botão de Exportação (CSV)
    csv = shopping_list_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Exportar para CSV",
        data=csv,
        file_name='lista_de_compras.csv',
        mime='text/csv',
    )


# --- 6. FORNECEDORES ---
def page_suppliers():
    st.title("Gerenciar Fornecedores")
    st.warning("Funcionalidade em desenvolvimento. No momento, os fornecedores são gerenciados a partir dos itens existentes no estoque.")
    # Futuramente, pode-se criar uma aba "Fornecedores" na planilha e gerenciar aqui
    
    st.subheader("Fornecedores Cadastrados")
    suppliers = get_unique_values("Fornecedor Principal")
    if suppliers:
        for supplier in suppliers:
            st.write(f"- {supplier}")
    else:
        st.info("Nenhum fornecedor cadastrado.")


# =============================================================================
# NAVEGAÇÃO PRINCIPAL (SIDEBAR)
# =============================================================================

# Dicionário de páginas
PAGES = {
    "Painel Principal": ("fa-solid fa-house", page_dashboard),
    "Meu Estoque": ("fa-solid fa-box-archive", page_my_stock),
    "Adicionar Item": ("fa-solid fa-plus-circle", page_add_item),
    "Registrar Uso": ("fa-solid fa-check-circle", page_register_usage),
    "Lista de Compras": ("fa-solid fa-shopping-cart", page_shopping_list),
    "Fornecedores": ("fa-solid fa-truck-fast", page_suppliers),
}

with st.sidebar:
    st.title("Studio Stock")
    st.markdown("---")

    # Inicializa a página
    if "page" not in st.session_state:
        st.session_state.page = "Painel Principal"

    # Cria os botões de navegação
    for page_name, (icon_class, _) in PAGES.items():
        # Lógica para destacar o botão ativo
        button_class = "st-emotion-cache-1v0mbdj e115fcil2" if st.session_state.page == page_name else ""
        if st.button(f'<i class="{icon_class}"></i> &nbsp; {page_name}', use_container_width=True, key=f"nav_{page_name}"):
            st.session_state.page = page_name
            st.rerun()

    # Informações de versão no rodapé da sidebar
    st.markdown("---")
    st.info("Versão 1.0\n\nFeito para estúdios modernos.")


# Chama a função da página selecionada para renderizar o conteúdo
if client: # Só renderiza as páginas se a conexão for bem-sucedida
    page_icon, page_function = PAGES[st.session_state.page]
    page_function()
else:
    st.error("Falha na conexão com a base de dados. Verifique as configurações de 'secrets' do Streamlit.")
