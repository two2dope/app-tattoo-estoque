import streamlit as st
import pandas as pd
from datetime import date, datetime
from fpdf import FPDF
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO INICIAL DA PÁGINA ---
st.set_page_config(
    page_title="Tattoo Studio Estoque",
    page_icon="✒️",
    layout="wide"
)

# --- CSS E COMPONENTES VISUAIS ---
def carregar_componentes_visuais(num_itens_alerta=0):
    st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">', unsafe_allow_html=True)
    st.markdown(f"""
    <style>
        /* ... (CSS completo da v14 aqui, sem alterações) ... */
        .block-container {{ padding-top: 3rem; }}
        body, .stApp {{ background-color: #0f0f1a; color: #e0e0e0; }}
        [data-testid="stSidebar"] > div:first-child {{
            display: flex; flex-direction: column; height: 100vh;
            padding: 1rem; overflow: hidden;
            background-color: #1a1a2e; border-right: 1px solid #2e2e54;
        }}
        .sidebar-menu .stButton:nth-child(5) > button::after {{
            content: '{num_itens_alerta if num_itens_alerta > 0 else ""}';
            background-color: #e53935; color: white; padding: 2px 8px;
            border-radius: 12px; font-size: 0.8em; font-weight: bold;
            display: { 'inline-block' if num_itens_alerta > 0 else 'none' };
        }}
        .metric-card {{
            background-color: #1a1a2e; padding: 20px; border-radius: 10px;
            border-left: 5px solid #4a4a8a; margin-bottom: 10px; height: 120px;
        }}
        /* ... (restante do CSS) ... */
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE CONEXÃO COM GOOGLE SHEETS ---
def connect_to_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        st.warning("Verifique se as credenciais [gcp_service_account] estão configuradas nos Segredos (Secrets) do seu app.")
        return None

def carregar_dados_gsheets(client):
    try:
        spreadsheet = client.open("BaseDeDados_Estoque")
        sheet = spreadsheet.worksheet("estoque")
        records = sheet.get_all_records()
        
        colunas_numericas = ["ID", "Quantidade em Estoque", "Estoque Mínimo", "Preço de Custo"]
        colunas_texto = ["Nome do Item", "Marca/Modelo", "Tipo/Especificação", "Categoria", "Fornecedor Principal", "Unidade de Medida", "Data da Última Compra", "Observações"]

        if records:
            df = pd.DataFrame(records)
            for col in colunas_numericas:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            for col in colunas_texto:
                df[col] = df[col].astype(str)
            st.session_state.estoque_df = df
        else:
            st.session_state.estoque_df = pd.DataFrame(columns=colunas_numericas + colunas_texto)
            
        st.session_state.categorias = ["Agulhas", "Tintas", "Descartáveis", "Higiene"]
        st.session_state.fornecedores = ["Art Prime", "Tattoo Loja", "Fornecedor Local"]
        st.session_state.colunas_visiveis = ['Nome do Item', 'Marca/Modelo', 'Categoria', 'Quantidade em Estoque']
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        st.stop()

def salvar_dados_gsheets(client):
    try:
        spreadsheet = client.open("BaseDeDados_Estoque")
        sheet = spreadsheet.worksheet("estoque")
        df_to_save = st.session_state.estoque_df.fillna('')
        data_to_upload = [df_to_save.columns.values.tolist()] + df_to_save.values.tolist()
        sheet.clear(); sheet.update(data_to_upload, 'A1')
    except Exception as e:
        st.error(f"Não foi possível salvar os dados na planilha: {e}")

# --- FUNÇÕES DE LÓGICA ---
def adicionar_item(nome, marca, especificacao, categoria, fornecedor, quantidade, estoque_minimo, unidade, preco_custo, observacoes=""):
    df = st.session_state.estoque_df; novo_id = 1 if df.empty else df["ID"].max() + 1
    novo_item = pd.DataFrame([{"ID": novo_id, "Nome do Item": nome, "Marca/Modelo": marca, "Tipo/Especificação": especificacao, "Categoria": categoria, "Fornecedor Principal": fornecedor, "Quantidade em Estoque": float(quantidade), "Estoque Mínimo": int(estoque_minimo), "Unidade de Medida": unidade, "Preço de Custo": float(preco_custo), "Data da Última Compra": date.today().strftime("%Y-%m-%d"), "Observações": observacoes}])
    st.session_state.estoque_df = pd.concat([df, novo_item], ignore_index=True)
    salvar_dados_gsheets(st.session_state.gsheets_client)

def registrar_uso(item_id, quantidade_usada):
    df = st.session_state.estoque_df; idx = df.index[df['ID'] == item_id][0]
    df.loc[idx, 'Quantidade em Estoque'] -= float(quantidade_usada)
    st.session_state.estoque_df = df
    salvar_dados_gsheets(st.session_state.gsheets_client)

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
    c1, c2 = st.columns([3, 1]); c1.header("Meu Estoque"); c2.button("Adicionar Novo Item", on_click=set_page, args=("Adicionar Item",), use_container_width=True, type="primary")
    with st.expander("Configurar Colunas Visíveis"):
        todas_colunas = [c for c in st.session_state.estoque_df.columns if c not in ['ID']]
        colunas_selecionadas = st.multiselect("Selecione as colunas:", options=todas_colunas, default=st.session_state.get('colunas_visiveis', todas_colunas))
        if colunas_selecionadas != st.session_state.get('colunas_visiveis'):
            st.session_state.colunas_visiveis = colunas_selecionadas; salvar_dados_gsheets(st.session_state.gsheets_client); st.rerun()
    
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
        salvar_dados_gsheets(st.session_state.gsheets_client); st.success("Alterações salvas com sucesso!"); st.rerun()
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
    # Gerenciar Categoria e Fornecedor precisa ser adaptado para GSheets se necessário
    # Por ora, mantemos em session_state (não persistente entre sessões)
    with c1:
        st.subheader("Categorias (Temporário)")
        st.write(st.session_state.categorias)
    with c2:
        st.subheader("Fornecedores (Temporário)")
        st.write(st.session_state.fornecedores)

# --- INICIALIZAÇÃO E ROTEAMENTO ---
def main():
    if 'pagina_atual' not in st.session_state:
        st.session_state.gsheets_client = connect_to_google_sheets()
        if st.session_state.gsheets_client:
            carregar_dados_gsheets(st.session_state.gsheets_client)
            st.session_state.pagina_atual = 'Painel Principal'
            st.session_state.sessao_uso = []
        else:
            st.stop()
    
    def set_page(page): st.session_state.pagina_atual = page
    
    with st.sidebar:
        st.markdown('<div class="sidebar-header"><h3>✒️ Tattoo Studio Estoque</h3></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)
        num_itens_comprar = len(gerar_lista_de_compras()) if gerar_lista_de_compras() is not None else 0
        carregar_componentes_visuais(num_itens_comprar)
        menu_items = ["Painel Principal", "Meu Estoque", "Adicionar Item", "Registrar Uso", "Lista de Compras", "Gerenciar Cadastros"]
        for item in menu_items:
            st.button(item, on_click=set_page, args=(item,), key=f"btn_{item}", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-footer"><span class="footer-brand">Rá Paixão Tattoo</span><span class="footer-version">Versão 14.1 Final</span></div>', unsafe_allow_html=True)
    
    paginas = {
        "Painel Principal": pagina_painel_principal, "Meu Estoque": pagina_meu_estoque,
        "Adicionar Item": pagina_adicionar_item, "Registrar Uso": pagina_registrar_uso,
        "Lista de Compras": pagina_lista_compras, "Gerenciar Cadastros": pagina_gerenciar_cadastros
    }
    paginas[st.session_state.pagina_atual]()

if __name__ == "__main__":
    main()

