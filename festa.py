import streamlit as st
import pandas as pd
import io
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Evento - Sociedade", layout="wide")

# --- Inicialização do Estado (Banco de Dados na Memória) ---
if 'despesas' not in st.session_state:
    st.session_state['despesas'] = pd.DataFrame(columns=['Item', 'Categoria', 'Valor Estimado', 'Valor Pago', 'Status'])

if 'socios' not in st.session_state:
    # Cria a lista inicial dos 8 sócios
    dados_iniciais = {'Nome': [f'Sócio {i+1}' for i in range(8)], 'Valor Pago': [0.0] * 8}
    st.session_state['socios'] = pd.DataFrame(dados_iniciais)

if 'receita' not in st.session_state:
    st.session_state['receita'] = pd.DataFrame(columns=['Origem', 'Qtd Vendida', 'Preço Unit.', 'Total Recebido'])

# --- Título ---
st.title(" Painel dos Sócios: Controle Total")
st.markdown("---")

# --- Barra Lateral: Resumo Rápido ---
st.sidebar.header(" Configurações")
num_socios = st.sidebar.number_input("Número de Sócios", min_value=1, value=8)

# Cálculos Globais para a Sidebar
df_desp = st.session_state['despesas']
df_soc = st.session_state['socios']
df_rec = st.session_state['receita']

total_despesas = df_desp['Valor Estimado'].sum()
total_pago_despesas = df_desp['Valor Pago'].sum()
total_arrecadado_socios = df_soc['Valor Pago'].sum()
total_bilheteria = df_rec['Total Recebido'].sum()

caixa_atual = (total_arrecadado_socios + total_bilheteria) - total_pago_despesas

# Valor da Cota Dinâmica
cota_ideal = total_despesas / num_socios if num_socios > 0 else 0

st.sidebar.markdown("### Resumo do Caixa")
st.sidebar.metric("Custo Total do Evento", f"R$ {total_despesas:,.2f}")
st.sidebar.metric("Bilheteria (Ingressos)", f"R$ {total_bilheteria:,.2f}", delta_color="normal")
st.sidebar.metric("Saldo em Caixa (Atual)", f"R$ {caixa_atual:,.2f}", 
                  delta="Lucro" if caixa_atual > 0 else "Falta Caixa")

st.sidebar.markdown("---")
st.sidebar.markdown(f"### Cota por Sócio: **R$ {cota_ideal:,.2f}**")
st.sidebar.caption("Valor que cada um deve dar para cobrir 100% das despesas atuais.")

# --- Estrutura de Abas ---
tab1, tab2, tab3, tab4 = st.tabs([" 1. Despesas", "2. Sócios (Rateio)", "🎟️ 3. Ingressos", "Relatórios"])

# ==========================
# ABA 1: DESPESAS
# ==========================
with tab1:
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Adicionar Gasto")
        with st.form("form_despesa", clear_on_submit=True):
            item = st.text_input("Descrição (Ex: DJ Pacato)")
            categoria = st.selectbox("Categoria", 
                ["DJ/Atrações", "Pulseiras/Credenciamento", "Espaço/Locação", 
                 "Decoração", "Marketing/Ads", "Bar/Bebidas", "Diversos/Outros"])
            valor_est = st.number_input("Valor Total (R$)", min_value=0.0, step=50.0)
            valor_pago = st.number_input("Já foi pago algo?", min_value=0.0, step=50.0)
            
            if st.form_submit_button("Lançar Despesa"):
                status = "Pago " if valor_pago >= valor_est else ("Parcial " if valor_pago > 0 else "Pendente ")
                nova_linha = pd.DataFrame([{
                    'Item': item, 'Categoria': categoria, 
                    'Valor Estimado': valor_est, 'Valor Pago': valor_pago, 'Status': status
                }])
                st.session_state['despesas'] = pd.concat([st.session_state['despesas'], nova_linha], ignore_index=True)
                st.rerun()

    with c2:
        st.subheader(" Lista de Contas")
        if not df_desp.empty:
            # Editor de dados para ajustes rápidos
            edited_df = st.data_editor(
                df_desp, 
                num_rows="dynamic",
                column_config={
                    "Valor Estimado": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Valor Pago": st.column_config.NumberColumn(format="R$ %.2f")
                },
                key="editor_despesas"
            )
            st.session_state['despesas'] = edited_df
        else:
            st.info("Nenhuma despesa cadastrada.")

# ==========================
# ABA 2: SÓCIOS (RATEIO)
# ==========================
with tab2:
    st.subheader(f"Controle dos {num_socios} Organizadores")
    st.info(f"O objetivo é que todos atinjam a cota de **R$ {cota_ideal:,.2f}**.")

    col_s1, col_s2 = st.columns([2, 1])

    with col_s1:
        # Tabela editável dos sócios
        st.markdown("##### Quem já pagou?")
        
        # Adiciona coluna de status calculada
        df_view_socios = st.session_state['socios'].copy()
        df_view_socios['Falta Pagar'] = cota_ideal - df_view_socios['Valor Pago']
        df_view_socios['Status'] = df_view_socios['Falta Pagar'].apply(lambda x: "Ok" if x <= 0 else " Devendo")
        
        # Edição apenas do valor pago e nome
        edited_socios = st.data_editor(
            st.session_state['socios'],
            column_config={
                "Valor Pago": st.column_config.NumberColumn(format="R$ %.2f"),
            },
            num_rows="fixed" # Mantém fixo nos 8 sócios (ou o numero configurado)
        )
        st.session_state['socios'] = edited_socios
    
    with col_s2:
        # Gráfico de quem pagou mais
        st.markdown("##### Ranking de Contribuição")
        if total_arrecadado_socios > 0:
            fig_socios = px.bar(st.session_state['socios'], x='Nome', y='Valor Pago', color='Valor Pago')
            st.plotly_chart(fig_socios, use_container_width=True)
        else:
            st.write("Nenhuma contribuição ainda.")

# ==========================
# ABA 3: INGRESSOS (RECEITA)
# ==========================
with tab3:
    c_rec1, c_rec2 = st.columns([1, 2])
    
    with c_rec1:
        st.subheader("Venda de Ingressos")
        with st.form("form_receita", clear_on_submit=True):
            origem = st.text_input("Origem (Ex: Lote 1, Bar Antecipado)")
            qtd = st.number_input("Quantidade", min_value=1, step=1)
            preco = st.number_input("Preço Unitário (R$)", min_value=0.0, step=5.0)
            
            if st.form_submit_button("Registrar Venda"):
                total = qtd * preco
                nova_rec = pd.DataFrame([{
                    'Origem': origem, 'Qtd Vendida': qtd, 
                    'Preço Unit.': preco, 'Total Recebido': total
                }])
                st.session_state['receita'] = pd.concat([st.session_state['receita'], nova_rec], ignore_index=True)
                st.rerun()
    
    with c_rec2:
        st.subheader(" Entradas")
        if not df_rec.empty:
            edited_rec = st.data_editor(
                df_rec,
                num_rows="dynamic",
                column_config={
                    "Total Recebido": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Preço Unit.": st.column_config.NumberColumn(format="R$ %.2f")
                }
            )
            st.session_state['receita'] = edited_rec
        else:
            st.info("Nenhuma venda registrada.")

# ==========================
# ABA 4: RELATÓRIOS
# ==========================
with tab4:
    st.header("Fechamento do Evento")
    
    # Função para baixar Excel com várias abas
    def to_excel_multi(dfs_dict):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in dfs_dict.items():
                df.to_excel(writer, index=False, sheet_name=sheet_name)
        return output.getvalue()

    dfs_to_save = {
        'Despesas': st.session_state['despesas'],
        'Controle_Socios': st.session_state['socios'],
        'Receitas': st.session_state['receita']
    }
    
    excel_data = to_excel_multi(dfs_to_save)
    
    st.download_button(
        label=" Baixar Planilha Completa (.xlsx)",
        data=excel_data,
        file_name='relatorio_final_evento.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    
    st.markdown("### Resumo Final")
    col_f1, col_f2, col_f3 = st.columns(3)
    lucro_prejuizo = (total_bilheteria - total_despesas)
    
    col_f1.metric("Total Gasto", f"R$ {total_despesas:,.2f}")
    col_f2.metric("Total Arrecadado (Bilheteria)", f"R$ {total_bilheteria:,.2f}")
    col_f3.metric("Lucro/Prejuízo Real", f"R$ {lucro_prejuizo:,.2f}", 
                  delta="Lucro" if lucro_prejuizo > 0 else "Prejuízo", delta_color="normal")
    
    if lucro_prejuizo > 0:
        st.success(f" Parabéns! O evento deu lucro. Cada um dos {num_socios} sócios recebe de volta: **R$ {lucro_prejuizo/num_socios:,.2f}** (além do investimento).")
    elif total_arrecadado_socios >= (total_despesas - total_bilheteria):
        st.warning("O evento está pago com o dinheiro dos sócios + bilheteria.")
    else:
        st.error(f"Falta dinheiro! Os sócios precisam aportar mais **R$ {(total_despesas - total_bilheteria - total_arrecadado_socios):,.2f}** no total.")