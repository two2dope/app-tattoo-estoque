import streamlit as st
import pandas as pd
from datetime import date, datetime
from fpdf import FPDFimport streamlit as st
import pandas as pd
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- CONFIGURAÇÃO INICIAL DA PÁGINA ---
st.set_page_config(
    page_title="Tattoo Studio Estoque",
    page_icon="✒️",
    layout="wide"
)

# --- CONSTANTES DE ARQUIVOS ---
ESTOQUE_FILE = 'estoque.csv'
CADASTROS_FILE = 'cadastros.json'

# --- CSS E COMPONENTES VISUAIS ---
def carregar_componentes_visuais(num_itens_alerta=0):
    # Injeta a folha de estilos do Font Awesome a partir de um CDN
    st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">', unsafe_allow_html=True)
    
    st.markdown(f"""
    <style>
        /* Ajustes Gerais */
        .block-container {{ padding-top: 2rem; }}
        body, .stApp {{ background-color: #0f0f1a; color: #e0e0e0; }}
        h1, h2, h3, h4 {{ color: #e0e0e0; }}
        
        /* Sidebar */
        [data-testid="stSidebar"] > div:first-child {{
            display: flex; flex-direction: column; height: 100vh;
            padding: 1rem; overflow: hidden;
            background-color: #1a1a2e; border-right: 1px solid #2e2e54;
        }}
        .sidebar-header {{ text-align: center; margin-bottom: 1rem; }}
        .sidebar-icon {{ font-size: 2.5em; margin-bottom: 0.5rem; color: #e0e0e0; }}
        .sidebar-menu {{ flex-grow: 1; }}
        .sidebar-footer {{ text-align: center; color: #a9a9a9; }}
        .footer-brand {{ font-size: 0.9em; font-weight: bold; display: block; }}
        .footer-version {{ font-size: 0.8em; color: #666; display: block; }}
        
        /* Botões do Menu da Sidebar */
        .stButton > button {{
            width: 100%; text-align: left !important;
            background-color: transparent; color: #e0e0e0; 
            padding: 10px 15px; margin-bottom: 5px; font-size: 1.0em;
            transition: all 0.2s ease-in-out; white-space: nowrap; 
            overflow: hidden; text-overflow: ellipsis; 
            display: flex; align-items: center; justify-content: space-between;
            border-radius: 8px;
            border: 1px solid #2e2e54;
        }}
        .stButton > button:hover {{ background-color: #162447; color: #ffffff; border-color: #4a4a8a; }}
        .stButton > button:focus:not(:hover) {{
            background-color: #2e2e54; color: white; border-color: #4a4a8a; font-weight: bold;
        }}

        /* Ícones do Font Awesome via Pseudo-elementos */
        .stButton > button::before {{
            font-family: "Font Awesome 6 Free"; font-weight: 900;
            margin-right: 12px; font-size: 0.9em;
        }}
        .sidebar-menu .stButton:nth-child(1) > button::before {{ content: '\\f080'; }}
        .sidebar-menu .stButton:nth-child(2) > button::before {{ content: '\\f49e'; }}
        .sidebar-menu .stButton:nth-child(3) > button::before {{ content: '\\2b'; }}
        .sidebar-menu .stButton:nth-child(4) > button::before {{ content: '\\f304'; }}
        .sidebar-menu .stButton:nth-child(5) > button::before {{ content: '\\f290'; }}
        .sidebar-menu .stButton:nth-child(6) > button::before {{ content: '\\f085'; }}

        /* Badge de Notificação */
        .sidebar-menu .stButton:nth-child(5) > button::after {{
            content: '{num_itens_alerta if num_itens_alerta > 0 else ""}';
            background-color: #e53935; color: white; padding: 2px 8px;
            border-radius: 12px; font-size: 0.8em; font-weight: bold;
            display: { 'inline-block' if num_itens_alerta > 0 else 'none' };
        }}

        /* Painel Principal: Cards */
        .metric-card {{
            background-color: #1a1a2e; padding: 20px; border-radius: 10px;
            border-left: 5px solid #4a4a8a; margin-bottom: 10px; height: 130px;
        }}
        .metric-card p {{ margin: 0; font-size: 1.1em; color: #a9a9a9; display: flex; align-items: center;}}
        .metric-card p i {{ margin-right: 10px; font-size: 0.9em; }}
        .metric-card h3 {{ font-size: 2.2em; color: #ffffff; margin-top: 5px; }}
        
        /* Outros */
        .stDataFrame, .stDataEditor {{ border: 1px solid #2e2e54; border-radius: 10px; }}
        .stDivider div {{ background-color: #2e2e54; }}
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE PERSISTÊNCIA ---
def salvar_dados():
    st.session_state['estoque_df'].to_csv(ESTOQUE_FILE, index=False)
    cadastros = {
        'categorias': st.session_state.categorias, 'fornecedores': st.session_state.fornecedores,
        'colunas_visiveis': st.session_state.get('colunas_visiveis', [])
    }
    with open(CADASTROS_FILE, 'w', encoding='utf-8') as f: json.dump(cadastros, f)

def carregar_dados():
    colunas = ["ID", "Nome do Item", "Marca/Modelo", "Tipo/Especificação", "Categoria", "Fornecedor Principal", "Quantidade em Estoque", "Estoque Mínimo", "Unidade de Medida", "Preço de Custo", "Data da Última Compra", "Observações"]
    if os.path.exists(ESTOQUE_FILE) and os.path.exists(CADASTROS_FILE):
        st.session_state.estoque_df = pd.read_csv(ESTOQUE_FILE)
        with open(CADASTROS_FILE, 'r', encoding='utf-8') as f:
            cadastros = json.load(f)
            st.session_state.categorias = cadastros.get('categorias', [])
            st.session_state.fornecedores = cadastros.get('fornecedores', [])
            st.session_state.colunas_visiveis = cadastros.get('colunas_visiveis', ['Nome do Item', 'Marca/Modelo', 'Categoria', 'Quantidade em Estoque'])
    else:
        st.session_state.update({
            'categorias': ["Agulhas", "Tintas", "Descartáveis", "Higiene"],
            'fornecedores': ["Art Prime", "Tattoo Loja", "Fornecedor Local"],
            'colunas_visiveis': ['Nome do Item', 'Marca/Modelo', 'Categoria', 'Quantidade em Estoque'],
            'estoque_df': pd.DataFrame(columns=colunas)
        })
        def adicionar_item_inicial(nome, marca, especificacao, categoria, fornecedor, quantidade, estoque_minimo, unidade, preco_custo, observacoes="", save=True):
            df = st.session_state.estoque_df; novo_id = 1 if df.empty else df["ID"].max() + 1
            novo_item = pd.DataFrame([{"ID": novo_id, "Nome do Item": nome, "Marca/Modelo": marca, "Tipo/Especificação": especificacao, "Categoria": categoria, "Fornecedor Principal": fornecedor, "Quantidade em Estoque": float(quantidade), "Estoque Mínimo": int(estoque_minimo), "Unidade de Medida": unidade, "Preço de Custo": float(preco_custo), "Data da Última Compra": date.today().strftime("%Y-%m-%d"), "Observações": observacoes}])
            st.session_state.estoque_df = pd.concat([df, novo_item], ignore_index=True)
            if save: salvar_dados()
        adicionar_item_inicial("Cartucho", "Cheyenne", "7RL", "Agulhas", "Art Prime", 25, 30, "Unidade", 3.00, save=False)
        adicionar_item_inicial("Tinta Preta", "Dynamic", "Triple Black", "Tintas", "Tattoo Loja", 240, 100, "ml", 0.37, save=False)
        adicionar_item_inicial("Luva Nitrílica", "Talge", "M", "Descartáveis", "Fornecedor Local", 40, 50, "Par", 0.80, save=True)

# --- FUNÇÕES DE LÓGICA ---
def adicionar_item(nome, marca, especificacao, categoria, fornecedor, quantidade, estoque_minimo, unidade, preco_custo, observacoes=""):
    df = st.session_state.estoque_df; novo_id = 1 if df.empty else df["ID"].max() + 1
    novo_item = pd.DataFrame([{"ID": novo_id, "Nome do Item": nome, "Marca/Modelo": marca, "Tipo/Especificação": especificacao, "Categoria": categoria, "Fornecedor Principal": fornecedor, "Quantidade em Estoque": float(quantidade), "Estoque Mínimo": int(estoque_minimo), "Unidade de Medida": unidade, "Preço de Custo": float(preco_custo), "Data da Última Compra": date.today().strftime("%Y-%m-%d"), "Observações": observacoes}])
    st.session_state.estoque_df = pd.concat([df, novo_item], ignore_index=True)
    salvar_dados()

def registrar_uso(item_id, quantidade_usada):
    df = st.session_state.estoque_df; idx = df.index[df['ID'] == item_id][0]
    df.loc[idx, 'Quantidade em Estoque'] -= float(quantidade_usada)
    st.session_state.estoque_df = df
    salvar_dados()

def gerar_lista_de_compras():
    df = st.session_state.estoque_df
    lista = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].copy()
    if not lista.empty:
        lista['Quantidade a Comprar'] = lista['Estoque Mínimo'] - lista['Quantidade em Estoque']
        return lista[['Nome do Item', 'Marca/Modelo', 'Fornecedor Principal', 'Quantidade em Estoque', 'Estoque Mínimo', 'Quantidade a Comprar']]
    return None

def gerar_pdf_relatorio(dataframe, titulo):
    pdf = FPDF(orientation='L', unit='mm', format='A4'); pdf.add_page()
    pdf.set_font("Arial", "B", 16); pdf.cell(0, 10, titulo, 0, 1, "C"); pdf.ln(5)
    pdf.set_font("Arial", "", 10); pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "R"); pdf.ln(5)
    pdf.set_font("Arial", "B", 8); pdf.set_fill_color(46, 46, 84); pdf.set_text_color(255, 255, 255)
    col_width = (pdf.w - 2 * pdf.l_margin) / len(dataframe.columns) if len(dataframe.columns) > 0 else 0
    for header in dataframe.columns: pdf.cell(col_width, 10, str(header), 1, 0, "C", fill=True)
    pdf.ln()
    pdf.set_font("Arial", "", 8); pdf.set_text_color(0, 0, 0); fill = False
    for _, row in dataframe.iterrows():
        for item in row: pdf.cell(col_width, 10, str(item), 1, 0, "C", fill=fill)
        fill = not fill; pdf.ln()
    return bytes(pdf.output(dest='S'))

# --- PÁGINAS DO APP ---
def pagina_painel_principal():
    st.markdown("<h3><i class='fa-solid fa-chart-simple'></i> Painel Principal</h3>", unsafe_allow_html=True); st.write("Resumo geral do seu inventário.")
    df = st.session_state.estoque_df; valor_total = (df['Quantidade em Estoque'] * df['Preço de Custo']).sum()
    itens_alerta = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]; total_itens = df.shape[0]
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><p><i class="fa-solid fa-coins"></i>Valor Total do Estoque</p><h3>R$ {valor_total:,.2f}</h3></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><p><i class="fa-solid fa-triangle-exclamation"></i>Itens em Alerta</p><h3>{itens_alerta}</h3></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><p><i class="fa-solid fa-boxes-stacked"></i>Total de Itens Únicos</p><h3>{total_itens}</h3></div>', unsafe_allow_html=True)
    st.subheader("Itens Precisando de Reposição Urgente")
    if (lista_urgente := gerar_lista_de_compras()) is not None:
        st.dataframe(lista_urgente, use_container_width=True, hide_index=True)
    else: st.success("🎉 Nenhum item precisa de reposição no momento!")

def pagina_meu_estoque():
    c1, c2 = st.columns([3, 1]); c1.markdown("<h3><i class='fa-solid fa-box-archive'></i> Meu Estoque</h3>", unsafe_allow_html=True); c2.button("Adicionar Novo Item", on_click=set_page, args=("Adicionar Item",), use_container_width=True, type="primary")
    with st.expander("Configurar Colunas Visíveis"):
        todas_colunas = [c for c in st.session_state.estoque_df.columns if c not in ['ID']]
        colunas_selecionadas = st.multiselect("Selecione as colunas:", options=todas_colunas, default=st.session_state.get('colunas_visiveis', todas_colunas))
        if colunas_selecionadas != st.session_state.get('colunas_visiveis'):
            st.session_state.colunas_visiveis = colunas_selecionadas; salvar_dados(); st.rerun()
    
    df_editavel = st.session_state.estoque_df.copy(); df_editavel["Excluir"] = False
    col_config = {
        "ID": st.column_config.NumberColumn(disabled=True), "Quantidade em Estoque": st.column_config.NumberColumn(format="%.2f", required=True),
        "Estoque Mínimo": st.column_config.NumberColumn(format="%d", required=True), "Preço de Custo": st.column_config.NumberColumn(format="R$ %.2f", required=True),
        "Categoria": st.column_config.SelectboxColumn(options=st.session_state.categorias, required=True),
        "Fornecedor Principal": st.column_config.SelectboxColumn(options=st.session_state.fornecedores, required=True),
    }
    df_modificado = st.data_editor(df_editavel[['ID'] + st.session_state.get('colunas_visiveis', []) + ['Excluir']], use_container_width=True, hide_index=True, key="data_editor", column_config=col_config)
    
    c1, c2 = st.columns([3, 1])
    if c1.button("Salvar Alterações", use_container_width=True, type="primary"):
        itens_para_excluir = df_modificado[df_modificado["Excluir"] == True]["ID"].tolist()
        df_alterado = df_modificado.drop(columns=["Excluir"]).set_index("ID")
        df_original = st.session_state.estoque_df.set_index("ID")
        df_original.update(df_alterado); st.session_state.estoque_df = df_original.reset_index()
        if itens_para_excluir: st.session_state.estoque_df = st.session_state.estoque_df[~st.session_state.estoque_df['ID'].isin(itens_para_excluir)]
        salvar_dados(); st.success("Alterações salvas com sucesso!"); st.rerun()
    if not st.session_state.estoque_df.empty:
        pdf_data = gerar_pdf_relatorio(st.session_state.estoque_df.drop(columns=['ID']), "Relatório de Estoque Completo")
        c2.download_button("Baixar Relatório PDF", pdf_data, f"relatorio_estoque_{date.today()}.pdf", "application/pdf", use_container_width=True)

def pagina_adicionar_item():
    st.markdown("<h3><i class='fa-solid fa-plus'></i> Adicionar Novo Item</h3>", unsafe_allow_html=True)
    with st.form("novo_item_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome=c1.text_input("Nome do Item*"); marca=c1.text_input("Marca/Modelo"); especificacao=c1.text_input("Tipo/Especificação")
        cat=c2.selectbox("Categoria*",st.session_state.categorias); forn=c2.selectbox("Fornecedor Principal*",st.session_state.fornecedores); un=c2.text_input("Unidade de Medida*")
        c3, c4 = st.columns(2)
        pr=c3.number_input("Preço de Custo (R$)*", min_value=0.0, format="%.2f"); qtd=c3.number_input("Quantidade em Estoque*", min_value=0.0)
        est_min=c4.number_input("Estoque Mínimo*", min_value=0); obs=c4.text_area("Observações Adicionais")
        if st.form_submit_button("Adicionar Item", use_container_width=True, type="primary"):
            if not all([nome, cat, forn, un]): st.error("Preencha os campos obrigatórios (*).")
            else: adicionar_item(nome,marca,especificacao,cat,forn,qtd,est_min,un,pr,obs); st.success("✅ Item adicionado!")

def pagina_registrar_uso():
    st.markdown("<h3><i class='fa-solid fa-pen'></i> Registrar Uso de Material</h3>", unsafe_allow_html=True); c1, c2 = st.columns(2)
    with c1:
        st.subheader("Adicionar Itens Consumidos"); df = st.session_state.estoque_df
        if not df.empty:
            itens_fmt = df.apply(lambda r: f"ID {r['ID']}: {r['Nome do Item']} ({r['Marca/Modelo']})", axis=1).tolist()
            item_sel = st.selectbox("Buscar item no estoque:", ["Selecione..."] + itens_fmt)
            if item_sel != "Selecione...":
                item_id = int(item_sel.split(':')[0].replace('ID','').strip()); qtd = st.number_input("Quantidade utilizada:", 1.0, step=1.0, format="%.2f")
                if st.button("Adicionar à Sessão"):
                    item_info = df[df['ID'] == item_id].iloc[0]
                    st.session_state.sessao_uso.append({'id': item_id, 'nome': f"{item_info['Nome do Item']} ({item_info['Marca/Modelo']})", 'qtd': qtd}); st.rerun()
    with c2:
        st.subheader("Itens da Sessão")
        if not st.session_state.sessao_uso: st.info("Nenhum item adicionado.")
        else:
            for item in st.session_state.sessao_uso: st.markdown(f"- **{item['qtd']}x** {item['nome']}")
            if st.button("Confirmar Uso", use_container_width=True, type="primary"):
                for item in st.session_state.sessao_uso: registrar_uso(item['id'], item['qtd'])
                st.session_state.sessao_uso = []; st.toast('Baixa de estoque confirmada com sucesso!', icon='✅'); st.rerun()

def pagina_lista_compras():
    st.markdown("<h3><i class='fa-solid fa-cart-shopping'></i> Lista de Compras</h3>", unsafe_allow_html=True); st.write("Itens que atingiram o estoque mínimo.")
    if (lista := gerar_lista_de_compras()) is not None:
        st.dataframe(lista, use_container_width=True, hide_index=True)
        pdf_data = gerar_pdf_relatorio(lista, "Lista de Compras"); st.download_button("Baixar Lista PDF", pdf_data, f"lista_compras_{date.today()}.pdf", "application/pdf")
    else: st.success("🎉 Nenhum item precisa de reposição!")

def pagina_gerenciar_cadastros():
    st.markdown("<h3><i class='fa-solid fa-cogs'></i> Gerenciar Cadastros</h3>", unsafe_allow_html=True); c1, c2 = st.columns(2)
    with c1:
        st.subheader("Categorias")
        with st.form("nova_cat_form", clear_on_submit=True):
            nova = st.text_input("Nova Categoria")
            if st.form_submit_button("Adicionar"):
                if nova and nova not in st.session_state.categorias:
                    st.session_state.categorias.append(nova); salvar_dados(); st.rerun()
                else: st.error("Inválida ou já existe.")
        if st.session_state.categorias:
            sel = st.selectbox("Excluir", st.session_state.categorias, key="del_cat")
            if st.button("Excluir Categoria"): st.session_state.categorias.remove(sel); salvar_dados(); st.rerun()
    with c2:
        st.subheader("Fornecedores")
        with st.form("novo_forn_form", clear_on_submit=True):
            nova = st.text_input("Novo Fornecedor")
            if st.form_submit_button("Adicionar"):
                if nova and nova not in st.session_state.fornecedores:
                    st.session_state.fornecedores.append(nova); salvar_dados(); st.rerun()
                else: st.error("Inválido ou já existe.")
        if st.session_state.fornecedores:
            sel = st.selectbox("Excluir", st.session_state.fornecedores, key="del_forn")
            if st.button("Excluir Fornecedor"): st.session_state.fornecedores.remove(sel); salvar_dados(); st.rerun()

# --- INICIALIZAÇÃO E ROTEAMENTO ---
if 'pagina_atual' not in st.session_state:
    carregar_dados()
    st.session_state.pagina_atual = 'Painel Principal'
    st.session_state.sessao_uso = []
def set_page(page): st.session_state.pagina_atual = page

# --- RENDERIZAÇÃO DA INTERFACE ---
with st.sidebar:
    st.markdown('<div class="sidebar-header"><i class="fa-solid fa-pen-nib sidebar-icon"></i><h3>Tattoo Studio Estoque</h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)
    num_itens_comprar = len(gerar_lista_de_compras()) if gerar_lista_de_compras() is not None else 0
    carregar_componentes_visuais(num_itens_comprar)
    
    menu_items = ["Painel Principal", "Meu Estoque", "Adicionar Item", "Registrar Uso", "Lista de Compras", "Gerenciar Cadastros"]
    
    for item in menu_items:
        st.button(item, on_click=set_page, args=(item,), key=f"btn_{item}", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-footer"><span class="footer-brand">Rá Paixão Tattoo</span><span class="footer-version">Versão 15.2 Final</span></div>', unsafe_allow_html=True)

paginas = {
    "Painel Principal": pagina_painel_principal, "Meu Estoque": pagina_meu_estoque,
    "Adicionar Item": pagina_adicionar_item, "Registrar Uso": pagina_registrar_uso,
    "Lista de Compras": pagina_lista_compras, "Gerenciar Cadastros": pagina_gerenciar_cadastros
}
paginas[st.session_state.pagina_atual]()


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
APP_VERSION = "2.5"

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
        .sidebar-menu {{ flex-grow: 1; overflow-y: auto; padding: 0 10px; }}

        /* Header da Sidebar */
        .sidebar-header {{ text-align: center; padding: 1rem 0; }}
        .sidebar-header .main-icon {{ font-size: 2.5rem; color: #ffffff; margin-bottom: 0.5rem; }}
        .sidebar-header h3 {{ color: #ffffff; font-weight: bold; margin: 0; }}

        /* Novo Estilo dos Botões da Sidebar */
        .stButton > button {{
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            text-align: left !important;
            padding: 12px 15px !important;
            margin: 4px 0 !important;
            border-radius: 8px;
            border: 1px solid #2e2e54;
            background-color: transparent;
            transition: all 0.2s ease-in-out;
            width: 100%;
        }}
        .stButton > button:hover {{
            background-color: #162447;
            border-color: #4a4a8a;
        }}
        .stButton > button:focus:not(:hover) {{
            background-color: #2e2e54;
            color: white;
            border-color: #4a90e2;
            font-weight: bold;
        }}
        
        /* Ícones dos Botões da Sidebar */
        .stButton > button::before {{
            font-family: "Font Awesome 6 Free";
            font-weight: 900;
            font-size: 1em;
            margin-right: 15px;
            width: 20px; /* Garante alinhamento */
            text-align: center;
        }}
        .sidebar-menu .stButton:nth-child(1) > button::before {{ content: '\\f200'; }} /* Painel */
        .sidebar-menu .stButton:nth-child(2) > button::before {{ content: '\\f468'; }} /* Estoque */
        .sidebar-menu .stButton:nth-child(3) > button::before {{ content: '\\f055'; }} /* Adicionar */
        .sidebar-menu .stButton:nth-child(4) > button::before {{ content: '\\f2f5'; }} /* Registrar Uso */
        .sidebar-menu .stButton:nth-child(5) > button::before {{ content: '{lista_compras_icon}'; }} /* Compras (Dinâmico) */
        .sidebar-menu .stButton:nth-child(6) > button::before {{ content: '\\f013'; }} /* Gerenciar */
        
        /* Badge de Notificação */
        .sidebar-menu .stButton:nth-child(5) button {{ justify-content: space-between !important; }}
        .sidebar-menu .stButton:nth-child(5) button > div::after {{
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

        /* Cards de Métricas */
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
            # Codifica o cabeçalho para 'latin-1' para compatibilidade
            pdf.cell(largura_coluna, 10, str(header).encode('latin-1', 'replace').decode('latin-1'), 1, 0, "C", fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", "", 8)
        for _, row in dataframe.iterrows():
            for item in row:
                # Codifica cada célula para 'latin-1', substituindo caracteres não suportados
                pdf.cell(largura_coluna, 10, str(item).encode('latin-1', 'replace').decode('latin-1'), 1, 0, "C")
            pdf.ln()
            
    # CORREÇÃO: Retorna os dados do PDF como bytes, que é o formato correto.
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


