import streamlit as st
import pandas as pd
from datetime import date, datetime
from fpdf import FPDF
import os
import json
import logging

# --- CONFIGURAÇÃO INICIAL ---
# Configuração do logging para depuração
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Tattoo Studio Estoque",
    page_icon="✒️",
    layout="wide"
)

# --- CONSTANTES GLOBAIS ---
ESTOQUE_FILE = 'estoque.csv'
CADASTROS_FILE = 'cadastros.json'
APP_VERSION = "2.4"

# Define as colunas e seus tipos de dados para garantir consistência
COLUNAS_ESTOQUE = [
    "ID", "Nome do Item", "Marca/Modelo", "Tipo/Especificação", "Categoria",
    "Fornecedor Principal", "Quantidade em Estoque", "Estoque Mínimo",
    "Unidade de Medida", "Preço de Custo", "Data da Última Compra", "Observações"
]
TIPOS_DADOS_ESTOQUE = {
    "ID": int, "Quantidade em Estoque": float, "Estoque Mínimo": float, "Preço de Custo": float
}


# --- CSS E COMPONENTES VISUAIS ---
def injetar_estilos(num_itens_alerta=0):
    """Injeta o CSS para estilizar a aplicação, incluindo ícones e layout da sidebar."""
    lista_compras_icon = '\\f071' if num_itens_alerta > 0 else '\\f07a' # fa-triangle-exclamation ou fa-cart-shopping

    st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">', unsafe_allow_html=True)
    st.markdown(f"""
    <style>
        /* Ajuste para evitar sobreposição do cabeçalho */
        .block-container {{ padding-top: 4rem; }}
        .stApp {{ background-color: #0f0f1a; color: #e0e0e0; }}
        h1, h2, h3, h4 {{ color: #e0e0e0; }}

        /* Layout da Sidebar para ocupar 100% da altura e evitar scroll */
        [data-testid="stSidebar"] > div:first-child {{
            display: flex; flex-direction: column; height: 100vh;
            overflow: hidden; background-color: #1a1a2e;
        }}
        .sidebar-menu {{ flex-grow: 1; overflow-y: auto; }}

        /* Header da Sidebar */
        .sidebar-header {{ text-align: center; padding: 1.5rem 0; }}
        .sidebar-header .main-icon {{ font-size: 3rem; color: #ffffff; margin-bottom: 0.5rem; }}
        .sidebar-header h3 {{ color: #ffffff; font-weight: bold; margin: 0; }}

        /* Ícones dos Botões da Sidebar */
        .stButton > button::before {{
            font-family: "Font Awesome 6 Free"; font-weight: 900;
            margin-right: 12px; font-size: 1.1em;
        }}
        .sidebar-menu .stButton:nth-child(1) > button::before {{ content: '\\f200'; }} /* Painel */
        .sidebar-menu .stButton:nth-child(2) > button::before {{ content: '\\f468'; }} /* Estoque */
        .sidebar-menu .stButton:nth-child(3) > button::before {{ content: '\\f055'; }} /* Adicionar */
        .sidebar-menu .stButton:nth-child(4) > button::before {{ content: '\\f2f5'; }} /* Registrar Uso */
        .sidebar-menu .stButton:nth-child(5) > button::before {{ content: '{lista_compras_icon}'; }} /* Compras (Dinâmico) */
        .sidebar-menu .stButton:nth-child(6) > button::before {{ content: '\\f013'; }} /* Gerenciar */
        
        /* Estilo dos Botões da Sidebar */
        .stButton > button {{
            border-radius: 8px; border: 1px solid transparent;
            transition: background-color 0.2s, border-color 0.2s;
        }}
        .stButton > button:hover {{ border-color: #4a4a8a; background-color: #162447; }}
        .stButton > button:focus:not(:hover) {{ border-color: #4a90e2; background-color: #2e2e54; }}

        /* Badge de Notificação */
        .sidebar-menu .stButton:nth-child(5) > button > div {{
            display: flex; justify-content: space-between; align-items: center; width: 100%;
        }}
        .sidebar-menu .stButton:nth-child(5) > button > div::after {{
            content: '{num_itens_alerta if num_itens_alerta > 0 else ""}';
            background-color: #e53935; color: white; padding: 2px 8px;
            border-radius: 12px; font-size: 0.8em; font-weight: bold;
            display: { 'inline-block' if num_itens_alerta > 0 else 'none' };
        }}
        
        /* Rodapé da Sidebar */
        .sidebar-footer {{
            text-align: center; padding: 1rem; flex-shrink: 0;
            border-top: 1px solid #2e2e54;
        }}
        .sidebar-footer .brand {{ font-weight: bold; color: #e0e0e0; margin: 0; }}
        .sidebar-footer .version {{ font-size: 0.8em; color: #808080; margin: 0; }}

        /* Novos Cards de Métricas */
        .metric-card {{
            background-color: #1c1c2e; border-radius: 10px; padding: 1.5rem;
            display: flex; align-items: center; border-left: 5px solid;
            transition: all 0.3s ease-in-out; margin-bottom: 1rem;
        }}
        .metric-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 15px rgba(0,0,0,0.2); }}
        .metric-card-1 {{ border-color: #4a90e2; }} /* Blue */
        .metric-card-2 {{ border-color: #f5a623; }} /* Orange */
        .metric-card-3 {{ border-color: #7ed321; }} /* Green */
        .metric-icon {{ font-size: 2.5em; margin-right: 1rem; opacity: 0.8; }}
        .metric-text p {{ margin: 0; font-size: 1em; color: #a9a9a9; }}
        .metric-text h3 {{ margin: 0; font-size: 1.8em; color: #ffffff; }}
    </style>
    """, unsafe_allow_html=True)


# --- PERSISTÊNCIA DE DADOS (CARREGAR E SALVAR) ---
def salvar_dados():
    """Salva o DataFrame de estoque e os cadastros (categorias/fornecedores) em seus respectivos arquivos."""
    try:
        st.session_state['estoque_df'].to_csv(ESTOQUE_FILE, index=False)
        cadastros = {
            'categorias': st.session_state.get('categorias', []),
            'fornecedores': st.session_state.get('fornecedores', []),
            'colunas_visiveis': st.session_state.get('colunas_visiveis', [])
        }
        with open(CADASTROS_FILE, 'w', encoding='utf-8') as f:
            json.dump(cadastros, f, indent=4)
        logging.info("Dados salvos com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao salvar dados: {e}")
        st.error(f"Ocorreu um erro ao salvar os dados: {e}")

def criar_dados_iniciais():
    """Cria um conjunto de dados iniciais se o arquivo de estoque não existir."""
    st.session_state.estoque_df = pd.DataFrame(columns=COLUNAS_ESTOQUE)
    itens_iniciais = [
        {"ID": 1, "Nome do Item": "Cartucho", "Marca/Modelo": "Cheyenne", "Tipo/Especificação": "7RL", "Categoria": "Agulhas", "Fornecedor Principal": "Art Prime", "Quantidade em Estoque": 25.0, "Estoque Mínimo": 30.0, "Unidade de Medida": "Unidade", "Preço de Custo": 3.00, "Data da Última Compra": date.today().strftime("%Y-%m-%d"), "Observações": ""},
        {"ID": 2, "Nome do Item": "Tinta Preta", "Marca/Modelo": "Dynamic", "Tipo/Especificação": "Triple Black", "Categoria": "Tintas", "Fornecedor Principal": "Tattoo Loja", "Quantidade em Estoque": 240.0, "Estoque Mínimo": 100.0, "Unidade de Medida": "ml", "Preço de Custo": 0.37, "Data da Última Compra": date.today().strftime("%Y-%m-%d"), "Observações": ""},
        {"ID": 3, "Nome do Item": "Luva Nitrílica", "Marca/Modelo": "Talge", "Tipo/Especificação": "M", "Categoria": "Descartáveis", "Fornecedor Principal": "Fornecedor Local", "Quantidade em Estoque": 40.0, "Estoque Mínimo": 50.0, "Unidade de Medida": "Par", "Preço de Custo": 0.80, "Data da Última Compra": date.today().strftime("%Y-%m-%d"), "Observações": ""}
    ]
    st.session_state.estoque_df = pd.DataFrame(itens_iniciais)
    salvar_dados()

def carregar_dados():
    """Carrega os dados dos arquivos ou inicializa o estado da sessão se os arquivos não existirem."""
    try:
        if os.path.exists(ESTOQUE_FILE) and os.path.exists(CADASTROS_FILE):
            st.session_state.estoque_df = pd.read_csv(ESTOQUE_FILE, dtype=TIPOS_DADOS_ESTOQUE, keep_default_na=False)
            with open(CADASTROS_FILE, 'r', encoding='utf-8') as f:
                cadastros = json.load(f)
                st.session_state.categorias = cadastros.get('categorias', ["Agulhas", "Tintas"])
                st.session_state.fornecedores = cadastros.get('fornecedores', ["Art Prime", "Tattoo Loja"])
                st.session_state.colunas_visiveis = cadastros.get('colunas_visiveis', ['Nome do Item', 'Quantidade em Estoque'])
            logging.info("Dados carregados com sucesso.")
        else:
            logging.warning("Arquivos de dados não encontrados. Criando dados iniciais.")
            st.session_state.categorias = ["Agulhas", "Tintas", "Descartáveis", "Higiene"]
            st.session_state.fornecedores = ["Art Prime", "Tattoo Loja", "Fornecedor Local"]
            st.session_state.colunas_visiveis = ['Nome do Item', 'Marca/Modelo', 'Categoria', 'Quantidade em Estoque']
            criar_dados_iniciais()
    except (pd.errors.ParserError, json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Erro ao carregar ou parsear arquivos: {e}. Recriando arquivos.")
        st.warning("Um dos arquivos de dados estava corrompido ou ausente e foi recriado. Alguns dados podem ter sido perdidos.")
        st.session_state.categorias = ["Agulhas", "Tintas", "Descartáveis", "Higiene"]
        st.session_state.fornecedores = ["Art Prime", "Tattoo Loja", "Fornecedor Local"]
        st.session_state.colunas_visiveis = ['Nome do Item', 'Marca/Modelo', 'Categoria', 'Quantidade em Estoque']
        criar_dados_iniciais()

# --- LÓGICA DE NEGÓCIO ---
def adicionar_item(nome, marca, especificacao, categoria, fornecedor, quantidade, estoque_minimo, unidade, preco_custo, observacoes=""):
    """Adiciona um novo item ao DataFrame de estoque."""
    df = st.session_state.estoque_df
    novo_id = (df["ID"].max() + 1) if not df.empty else 1
    novo_item = pd.DataFrame([{
        "ID": novo_id, "Nome do Item": nome, "Marca/Modelo": marca, "Tipo/Especificação": especificacao,
        "Categoria": categoria, "Fornecedor Principal": fornecedor, "Quantidade em Estoque": float(quantidade),
        "Estoque Mínimo": float(estoque_minimo), "Unidade de Medida": unidade, "Preço de Custo": float(preco_custo),
        "Data da Última Compra": date.today().strftime("%Y-%m-%d"), "Observações": observacoes
    }])
    st.session_state.estoque_df = pd.concat([df, novo_item], ignore_index=True)
    salvar_dados()

def registrar_uso(item_id, quantidade_usada):
    """Subtrai uma quantidade do estoque de um item específico."""
    df = st.session_state.estoque_df
    idx = df.index[df['ID'] == item_id]
    if not idx.empty:
        df.loc[idx[0], 'Quantidade em Estoque'] -= float(quantidade_usada)
        st.session_state.estoque_df = df
        salvar_dados()
    else:
        st.error(f"ID de item {item_id} não encontrado para registrar uso.")

def gerar_lista_de_compras():
    """Gera um DataFrame com itens que estão abaixo do estoque mínimo."""
    df = st.session_state.estoque_df
    if 'Quantidade em Estoque' not in df.columns or 'Estoque Mínimo' not in df.columns:
        return pd.DataFrame() 
    
    lista = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].copy()
    if not lista.empty:
        lista['Quantidade a Comprar'] = lista['Estoque Mínimo'] - lista['Quantidade em Estoque']
        return lista[['Nome do Item', 'Marca/Modelo', 'Fornecedor Principal', 'Quantidade em Estoque', 'Estoque Mínimo', 'Quantidade a Comprar']]
    return pd.DataFrame()

def gerar_pdf_relatorio(dataframe, titulo):
    """Gera um arquivo PDF em formato de bytes a partir de um DataFrame."""
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, titulo, 0, 1, "C")
    pdf.ln(5)
    
    # Adiciona a codificação UTF-8 para suportar caracteres especiais
    pdf.add_font('Arial', '', 'Arial.ttf', uni=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "R")
    pdf.ln(5)
    
    if dataframe.empty:
        pdf.set_font("Arial", "I", 12)
        pdf.cell(0, 10, "Nenhum dado para exibir.", 0, 1, "C")
    else:
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(230, 230, 230)
        
        num_colunas = len(dataframe.columns)
        largura_disponivel = pdf.w - 2 * pdf.l_margin
        largura_coluna = largura_disponivel / num_colunas if num_colunas > 0 else 0
        
        for header in dataframe.columns:
            pdf.cell(largura_coluna, 10, str(header), 1, 0, "C", fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", "", 8)
        for _, row in dataframe.iterrows():
            for item in row:
                pdf.cell(largura_coluna, 10, str(item), 1, 0, "C")
            pdf.ln()
            
    # CORREÇÃO: pdf.output() retorna uma string que precisa ser codificada.
    # 'latin-1' é uma codificação segura para arquivos binários como PDF.
    return pdf.output(dest='S').encode('latin-1')


# --- PÁGINAS DA APLICAÇÃO ---
def pagina_painel_principal(lista_compras):
    st.markdown("<h3><i class='fa-solid fa-chart-pie'></i> Painel Principal</h3>", unsafe_allow_html=True)
    st.markdown("Resumo geral do seu inventário.")

    df = st.session_state.estoque_df
    valor_total = (df['Quantidade em Estoque'] * df['Preço de Custo']).sum()
    total_itens = df.shape[0]
    num_itens_alerta = len(lista_compras)

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"""
    <div class="metric-card metric-card-1">
        <i class="fa-solid fa-sack-dollar metric-icon"></i>
        <div class="metric-text">
            <p>Valor Total do Estoque</p>
            <h3>R$ {valor_total:,.2f}</h3>
        </div>
    </div>""", unsafe_allow_html=True)
    
    col2.markdown(f"""
    <div class="metric-card metric-card-2">
        <i class="fa-solid fa-triangle-exclamation metric-icon"></i>
        <div class="metric-text">
            <p>Itens em Alerta</p>
            <h3>{num_itens_alerta}</h3>
        </div>
    </div>""", unsafe_allow_html=True)

    col3.markdown(f"""
    <div class="metric-card metric-card-3">
        <i class="fa-solid fa-boxes-stacked metric-icon"></i>
        <div class="metric-text">
            <p>Total de Itens Únicos</p>
            <h3>{total_itens}</h3>
        </div>
    </div>""", unsafe_allow_html=True)

    st.subheader("Itens Precisando de Reposição Urgente")
    if not lista_compras.empty:
        st.dataframe(lista_compras, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 Nenhum item precisa de reposição no momento!")

def pagina_meu_estoque():
    c1, c2 = st.columns([3, 1])
    c1.markdown("<h3><i class='fa-solid fa-boxes-stacked'></i> Meu Estoque</h3>", unsafe_allow_html=True)
    if c2.button("Adicionar Novo Item", use_container_width=True, type="primary"):
        st.session_state.pagina_atual = "Adicionar Item"
        st.rerun()
    
    df_original = st.session_state.estoque_df.copy()

    with st.expander("Filtrar e Configurar Colunas Visíveis"):
        colunas_disponiveis = [c for c in COLUNAS_ESTOQUE if c != 'ID']
        colunas_selecionadas = st.multiselect(
            "Selecione as colunas para exibir:",
            options=colunas_disponiveis,
            default=st.session_state.get('colunas_visiveis', ['Nome do Item', 'Categoria', 'Quantidade em Estoque'])
        )
        if colunas_selecionadas != st.session_state.get('colunas_visiveis'):
            st.session_state.colunas_visiveis = colunas_selecionadas
            salvar_dados()
            st.rerun()

    df_para_editar = df_original.copy()
    df_para_editar["Excluir"] = False
    colunas_editor = ['ID'] + st.session_state.colunas_visiveis + ['Excluir']
    
    df_modificado = st.data_editor(
        df_para_editar[colunas_editor],
        use_container_width=True, hide_index=True, key="data_editor_estoque",
        column_config={
            "ID": st.column_config.NumberColumn(disabled=True),
            "Quantidade em Estoque": st.column_config.NumberColumn(format="%.2f", required=True),
            "Estoque Mínimo": st.column_config.NumberColumn(format="%.2f", required=True),
            "Preço de Custo": st.column_config.NumberColumn(format="R$ %.2f", required=True),
            "Categoria": st.column_config.SelectboxColumn(options=st.session_state.categorias, required=True),
            "Fornecedor Principal": st.column_config.SelectboxColumn(options=st.session_state.fornecedores, required=True),
        }
    )

    c1, c2 = st.columns([3, 1])
    if c1.button("Salvar Alterações", use_container_width=True, type="primary"):
        ids_para_excluir = df_modificado[df_modificado["Excluir"]]["ID"].tolist()
        df_alterado = df_modificado.drop(columns=["Excluir"]).set_index('ID')
        
        df_atualizado = df_original.copy().set_index('ID')
        df_atualizado.update(df_alterado)
        df_atualizado = df_atualizado.reset_index()

        if ids_para_excluir:
            df_atualizado = df_atualizado[~df_atualizado['ID'].isin(ids_para_excluir)]
        
        st.session_state.estoque_df = df_atualizado
        salvar_dados()
        st.success("Alterações salvas com sucesso!")
        st.rerun()

    if not st.session_state.estoque_df.empty:
        pdf_data = gerar_pdf_relatorio(st.session_state.estoque_df.drop(columns=['ID']), "Relatório de Estoque Completo")
        c2.download_button(
            label="Baixar Relatório PDF", data=pdf_data,
            file_name=f"relatorio_estoque_{date.today()}.pdf", mime="application/pdf",
            use_container_width=True
        )

def pagina_adicionar_item():
    st.markdown("<h3><i class='fa-solid fa-plus-circle'></i> Adicionar Novo Item</h3>", unsafe_allow_html=True)
    with st.form("novo_item_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do Item*", help="Campo obrigatório")
        marca = c1.text_input("Marca/Modelo")
        especificacao = c1.text_input("Tipo/Especificação")
        
        categoria = c2.selectbox("Categoria*", st.session_state.categorias, help="Campo obrigatório")
        fornecedor = c2.selectbox("Fornecedor Principal*", st.session_state.fornecedores, help="Campo obrigatório")
        unidade = c2.text_input("Unidade de Medida*", help="Ex: Unidade, ml, Par, Caixa")
        
        c3, c4 = st.columns(2)
        preco_custo = c3.number_input("Preço de Custo (R$)*", min_value=0.01, format="%.2f", help="Campo obrigatório")
        quantidade = c3.number_input("Quantidade em Estoque*", min_value=0.0, format="%.2f")
        estoque_minimo = c4.number_input("Estoque Mínimo*", min_value=0.0, format="%.2f")
        observacoes = c4.text_area("Observações Adicionais")
        
        if st.form_submit_button("Adicionar Item", use_container_width=True, type="primary"):
            if not all([nome, categoria, fornecedor, unidade, preco_custo]):
                st.error("Preencha todos os campos obrigatórios (*).")
            else:
                adicionar_item(nome, marca, especificacao, categoria, fornecedor, quantidade, estoque_minimo, unidade, preco_custo, observacoes)
                st.success(f"✅ Item '{nome}' adicionado com sucesso!")

def pagina_registrar_uso():
    st.markdown("<h3><i class='fa-solid fa-right-from-bracket'></i> Registrar Uso de Material</h3>", unsafe_allow_html=True)
    if 'sessao_uso' not in st.session_state:
        st.session_state.sessao_uso = []

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Adicionar Itens Consumidos")
        df = st.session_state.estoque_df
        if not df.empty:
            itens_formatados = df.apply(lambda row: f"{row['Nome do Item']} ({row['Marca/Modelo']}) - ID: {row['ID']}", axis=1).tolist()
            item_selecionado_str = st.selectbox("Buscar item no estoque:", ["Selecione..."] + itens_formatados)
            
            if item_selecionado_str != "Selecione...":
                item_id = int(item_selecionado_str.split('ID: ')[-1])
                quantidade_usada = st.number_input("Quantidade utilizada:", min_value=0.1, step=1.0, format="%.2f", key=f"qtd_{item_id}")
                
                if st.button("Adicionar à Sessão"):
                    item_info = df[df['ID'] == item_id].iloc[0]
                    st.session_state.sessao_uso.append({'id': item_id, 'nome': f"{item_info['Nome do Item']} ({item_info['Marca/Modelo']})", 'qtd': quantidade_usada})
                    st.rerun()
    with c2:
        st.subheader("Itens da Sessão Atual")
        if not st.session_state.sessao_uso:
            st.info("Nenhum item adicionado à sessão de uso.")
        else:
            for item in st.session_state.sessao_uso:
                st.markdown(f"- **{item['qtd']}x** {item['nome']}")
            
            c1_uso, c2_uso = st.columns(2)
            if c1_uso.button("Confirmar Uso e Baixar do Estoque", use_container_width=True, type="primary"):
                for item in st.session_state.sessao_uso:
                    registrar_uso(item['id'], item['qtd'])
                st.session_state.sessao_uso = []
                st.toast('Baixa de estoque confirmada!', icon='✅')
                st.rerun()
            if c2_uso.button("Limpar Sessão", use_container_width=True):
                st.session_state.sessao_uso = []
                st.rerun()

def pagina_lista_compras(lista_compras):
    st.markdown("<h3><i class='fa-solid fa-cart-shopping'></i> Lista de Compras</h3>", unsafe_allow_html=True)
    st.write("Itens que atingiram ou ultrapassaram o estoque mínimo definido.")

    if not lista_compras.empty:
        st.dataframe(lista_compras, use_container_width=True, hide_index=True)
        pdf_data = gerar_pdf_relatorio(lista_compras, "Lista de Compras")
        st.download_button(
            label="Baixar Lista em PDF", data=pdf_data,
            file_name=f"lista_compras_{date.today()}.pdf", mime="application/pdf",
            use_container_width=True
        )
    else:
        st.success("🎉 Sua lista de compras está vazia! Tudo em ordem no estoque.")

def pagina_gerenciar_cadastros():
    st.markdown("<h3><i class='fa-solid fa-cog'></i> Gerenciar Cadastros</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Gerenciar Categorias")
        nova_categoria = st.text_input("Adicionar Nova Categoria", key="nova_cat_input")
        if st.button("Adicionar Categoria"):
            if nova_categoria and nova_categoria not in st.session_state.categorias:
                st.session_state.categorias.append(nova_categoria); salvar_dados(); st.rerun()
            else: st.error("Nome de categoria inválido ou já existente.")

        if st.session_state.categorias:
            cat_para_excluir = st.selectbox("Excluir Categoria", options=[""] + st.session_state.categorias, key="del_cat_select")
            if st.button("Excluir Categoria Selecionada"):
                if cat_para_excluir in st.session_state.estoque_df['Categoria'].unique():
                    st.error(f"A categoria '{cat_para_excluir}' está em uso e não pode ser excluída.")
                elif cat_para_excluir:
                    st.session_state.categorias.remove(cat_para_excluir); salvar_dados(); st.rerun()

    with c2:
        st.subheader("Gerenciar Fornecedores")
        novo_fornecedor = st.text_input("Adicionar Novo Fornecedor", key="novo_forn_input")
        if st.button("Adicionar Fornecedor"):
            if novo_fornecedor and novo_fornecedor not in st.session_state.fornecedores:
                st.session_state.fornecedores.append(novo_fornecedor); salvar_dados(); st.rerun()
            else: st.error("Nome de fornecedor inválido ou já existente.")

        if st.session_state.fornecedores:
            forn_para_excluir = st.selectbox("Excluir Fornecedor", options=[""] + st.session_state.fornecedores, key="del_forn_select")
            if st.button("Excluir Fornecedor Selecionado"):
                if forn_para_excluir in st.session_state.estoque_df['Fornecedor Principal'].unique():
                    st.error(f"O fornecedor '{forn_para_excluir}' está em uso e não pode ser excluído.")
                elif forn_para_excluir:
                    st.session_state.fornecedores.remove(forn_para_excluir); salvar_dados(); st.rerun()


# --- INICIALIZAÇÃO E CONTROLE DE FLUXO ---
def main():
    """Função principal que inicializa o estado e renderiza a página correta."""
    if 'app_inicializado' not in st.session_state:
        carregar_dados()
        st.session_state.pagina_atual = 'Painel Principal'
        st.session_state.sessao_uso = []
        st.session_state.app_inicializado = True

    lista_compras_atual = gerar_lista_de_compras()
    num_itens_alerta = len(lista_compras_atual)

    with st.sidebar:
        injetar_estilos(num_itens_alerta)
        
        st.markdown("""
            <div class="sidebar-header">
                <i class="fa-solid fa-pen-nib main-icon"></i>
                <h3>Tattoo Studio Estoque</h3>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)
        menu_items = ["Painel Principal", "Meu Estoque", "Adicionar Item",
                      "Registrar Uso", "Lista de Compras", "Gerenciar Cadastros"]
        
        for item in menu_items:
            if st.button(item, key=f"btn_{item}", use_container_width=True):
                st.session_state.pagina_atual = item
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class="sidebar-footer">
                <p class="brand">Rá Paixão Tattoo</p>
                <p class="version">Versão {APP_VERSION}</p>
            </div>
            """, unsafe_allow_html=True)

    paginas = {
        "Painel Principal": lambda: pagina_painel_principal(lista_compras_atual),
        "Meu Estoque": pagina_meu_estoque, "Adicionar Item": pagina_adicionar_item,
        "Registrar Uso": pagina_registrar_uso,
        "Lista de Compras": lambda: pagina_lista_compras(lista_compras_atual),
        "Gerenciar Cadastros": pagina_gerenciar_cadastros
    }

    pagina_a_renderizar = paginas.get(st.session_state.pagina_atual, paginas["Painel Principal"])
    pagina_a_renderizar()


if __name__ == "__main__":
    main()

