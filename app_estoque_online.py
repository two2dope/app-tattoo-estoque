import streamlit as st
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
        iframe {{ display: none; }} /* Oculta o iframe de componentes HTML */
        .block-container {{ padding-top: 3rem; }}
        body, .stApp {{ background-color: #0f0f1a; color: #e0e0e0; }}
        h1, h2, h3, h4 {{ color: #e0e0e0; }}
        
        /* Sidebar */
        [data-testid="stSidebar"] > div:first-child {{
            display: flex; flex-direction: column; height: 100vh;
            padding: 1rem; overflow: hidden;
            background-color: #1a1a2e; border-right: 1px solid #2e2e54;
        }}
        .sidebar-header {{ text-align: center; margin-bottom: 1rem; }}
        .sidebar-menu {{ flex-grow: 1; }}
        .sidebar-footer {{ text-align: center; color: #a9a9a9; }}
        .footer-brand {{ font-size: 0.9em; font-weight: bold; display: block; }}
        .footer-version {{ font-size: 0.8em; color: #666; display: block; }}
        
        /* Menu da Sidebar (HTML) */
        .nav-item {{
            display: flex; align-items: center; justify-content: space-between;
            padding: 10px 15px; margin-bottom: 4px; border-radius: 8px;
            font-size: 1.0em; color: #e0e0e0; text-decoration: none;
            transition: all 0.2s ease-in-out; cursor: pointer;
        }}
        .nav-item:hover {{ background-color: #162447; color: #ffffff; }}
        .nav-item.active {{ background-color: #2e2e54; color: white; font-weight: bold; }}
        .nav-item .icon {{ margin-right: 12px; font-size: 0.9em; width: 20px; text-align: center;}}
        .nav-item .text {{ flex-grow: 1; }}

        /* Badge de Notificação */
        .badge {{
            background-color: #e53935; color: white; padding: 2px 8px;
            border-radius: 12px; font-size: 0.8em; font-weight: bold;
        }}

        /* Painel Principal: Cards */
        .metric-card {{
            background-color: #1a1a2e; padding: 20px; border-radius: 10px;
            border-left: 5px solid #4a4a8a; margin-bottom: 10px; height: 120px;
        }}
        .metric-card p {{ margin: 0; font-size: 1.1em; color: #a9a9a9; }}
        .metric-card h3 {{ font-size: 2.2em; color: #ffffff; margin-top: 5px; }}
        
        /* Formulários */
        .stTextInput, .stNumberInput, .stTextArea, .stSelectbox {{
            background-color: #1a1a2e; border: 1px solid #2e2e54; border-radius: 8px; padding: 5px 10px;
        }}
        
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
    st.header("Painel Principal"); st.write("Resumo geral do seu inventário.")
    df = st.session_state.estoque_df; valor_total = (df['Quantidade em Estoque'] * df['Preço de Custo']).sum()
    itens_alerta = df[df['Quantidade em Estoque'] <= df['Estoque Mínimo']].shape[0]; total_itens = df.shape[0]
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><p>Valor Total do Estoque</p><h3>R$ {valor_total:,.2f}</h3></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><p>Itens em Alerta</p><h3>{itens_alerta}</h3></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><p>Total de Itens Únicos</p><h3>{total_itens}</h3></div>', unsafe_allow_html=True)
    st.subheader("Itens Precisando de Reposição Urgente")
    if (lista_urgente := gerar_lista_de_compras()) is not None:
        st.dataframe(lista_urgente, use_container_width=True, hide_index=True)
    else: st.success("🎉 Nenhum item precisa de reposição no momento!")

def pagina_meu_estoque():
    c1, c2 = st.columns([3, 1]); c1.header("Meu Estoque"); c2.button("Adicionar Novo Item", on_click=lambda: st.query_params.update(page="Adicionar_Item"), use_container_width=True, type="primary")
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
    st.header("Adicionar Novo Item")
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
    st.header("Registrar Uso de Material"); c1, c2 = st.columns(2)
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
                st.session_state.sessao_uso = []; st.success("Uso de todos os itens da sessão foi registrado!"); st.rerun()

def pagina_lista_compras():
    st.header("Lista de Compras"); st.write("Itens que atingiram o estoque mínimo.")
    if (lista := gerar_lista_de_compras()) is not None:
        st.dataframe(lista, use_container_width=True, hide_index=True)
        pdf_data = gerar_pdf_relatorio(lista, "Lista de Compras"); st.download_button("Baixar Lista PDF", pdf_data, f"lista_compras_{date.today()}.pdf", "application/pdf")
    else: st.success("🎉 Nenhum item precisa de reposição!")

def pagina_gerenciar_cadastros():
    st.header("Gerenciar Cadastros"); c1, c2 = st.columns(2)
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
if 'estoque_df' not in st.session_state:
    carregar_dados()
    st.session_state.sessao_uso = []

# --- RENDERIZAÇÃO DA INTERFACE ---
query_params = st.query_params.to_dict()
pagina_atual = query_params.get("page", ["Painel Principal"])[0].replace("_", " ")

with st.sidebar:
    st.markdown('<div class="sidebar-header"><h3>Tattoo Studio Estoque</h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)
    
    num_itens_comprar = len(gerar_lista_de_compras()) if gerar_lista_de_compras() is not None else 0
    carregar_componentes_visuais(num_itens_comprar)
    
    menu_items = {
        "Painel Principal": "fa-solid fa-chart-simple", "Meu Estoque": "fa-solid fa-box-archive",
        "Adicionar Item": "fa-solid fa-plus", "Registrar Uso": "fa-solid fa-pen",
        "Lista de Compras": "fa-solid fa-cart-shopping", "Gerenciar Cadastros": "fa-solid fa-cogs"
    }

    for page_name, icon_class in menu_items.items():
        is_active = "active" if pagina_atual == page_name else ""
        badge_html = f"<span class='badge'>{num_itens_comprar}</span>" if "Lista de Compras" in page_name and num_itens_comprar > 0 else ""
        page_link = page_name.replace(" ", "_")
        st.markdown(f'<a href="?page={page_link}" class="nav-item {is_active}" target="_self"><i class="{icon_class} icon"></i><span class="text">{page_name}</span>{badge_html}</a>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-footer"><span class="footer-brand">Rá Paixão Tattoo</span><span class="footer-version">Versão 15.0 Final</span></div>', unsafe_allow_html=True)

paginas = {
    "Painel Principal": pagina_painel_principal, "Meu Estoque": pagina_meu_estoque,
    "Adicionar Item": pagina_adicionar_item, "Registrar Uso": pagina_registrar_uso,
    "Lista de Compras": pagina_lista_compras, "Gerenciar Cadastros": pagina_gerenciar_cadastros
}
if pagina_atual in paginas:
    paginas[pagina_atual]()
else:
    # Página padrão caso o parâmetro da URL seja inválido
    paginas["Painel Principal"]()

