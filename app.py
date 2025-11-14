# Importa as bibliotecas necessárias
import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np 
# A biblioteca 'date' não é mais necessária, mas a 'timedelta' pode ser útil.
from datetime import date, timedelta 

# ==============================================================================
# IMPORTS DOS MÓDULOS (11 MÓDULOS)
# ==============================================================================

# Módulo 1: Constantes
from modulos.config import *

# Módulo 2: Funções de Tratamento e Formatação
from modulos.tratamento import (
    formatar_milhar_br, 
    style_total_pontuacao, 
    calcular_evolucao_pct,
    style_nome_categoria
) 

# Módulo 3: Lógica de Carregamento e Pré-tratamento
from modulos.dados import carregar_e_tratar_dados 

# Módulo 4: Cálculo de KPIs do Topo
from modulos.kpi import calcular_metricas

# Módulo 5: Comparativo de Desempenho por Temporada (Item 1)
from modulos.comparativo_temporada import calcular_metricas_temporais

# Módulo 6: Lógica de Categorias (Classificação e Evolução T-1)
from modulos.categoria import calcular_categorias, get_pontuacao_temporada_anterior, get_contagem_categoria 

# Módulo 7: Lógica de Análise de Lojas (Evolução e Terços)
from modulos.analise_lojas import calcular_analise_lojas

# Módulo 8: Lógica de Pivô Mensal de Pontos (Item 3)
from modulos.evolucao_pontos import calcular_pivo_pontos

# Módulo 9: Lógica de Pivôs de Pedidos e Novos Clientes (Itens 6B e 9)
from modulos.pedidos import calcular_pivo_pedidos, calcular_pivo_novos_clientes

# Módulo 10: Lógica de Retenção (Ativos vs. Inativos/Item 10)
from modulos.retencao import calcular_clientes_ativos_inativos

# Módulo 11: Lógica de Variação de Ranking (Item 11)
from modulos.ranking import calcular_ranking_ajustado

# ==============================================================================
# CONFIGURAÇÃO E CARREGAMENTO INICIAL
# ==============================================================================

# Configuração e Título
st.set_page_config(layout="wide")
st.title("📊 Dashboard de Análise Associação Gabriel Pro")

# Inicialização do Estado (Para interatividade de clique)
if 'filtro_status_ano' not in st.session_state:
    st.session_state['filtro_status_ano'] = {'ano': None, 'status': None, 'termo_pesquisa': ''}
    
# --- Funções de Callback para Resetar Estado ---
def reset_lojas_selection():
    """
    Função de callback para resetar o estado de seleção de lojas.
    """
    if 'item7_lojas_default' in st.session_state:
        st.session_state['item7_lojas_select'] = st.session_state['item7_lojas_default']


# Carrega e trata os dados (usando a função importada)
df_dados_original, df_novos_cadastrados_original = carregar_e_tratar_dados(Relatorio)


# --- Aplicação Streamlit (Interface) ---

if not df_dados_original.empty:
    
    # CRÍTICO: Garantir que 'Data da Venda' é datetime para evitar erros de comparação
    if 'Data da Venda' in df_dados_original.columns:
        df_dados_original['Data da Venda'] = pd.to_datetime(df_dados_original['Data da Venda'], errors='coerce')
        # Remove NaT após o carregamento (já deve ter sido feito em dados.py, mas como seguro)
        df_dados_original.dropna(subset=['Data da Venda'], inplace=True)
    
    # Cria uma cópia inicial que será usada como base para a filtragem de LOJA/SEGMENTO
    df_base_para_filtros = df_dados_original.copy()

    # Obtém a lista de todas as temporadas disponíveis para os seletores
    todas_temporadas_disponiveis_unicas = sorted(
        df_dados_original['Temporada_Exibicao']
        .loc[df_dados_original['Temporada_Exibicao'] != 'Temporada 0']
        .dropna()
        .unique()
    )


    # === BARRA LATERAL (FILTROS DE DATA E TEMPORADA) ===
    st.sidebar.header("Filtros Interativos")
    
    # CRÍTICO: Inicialização de todas as variáveis de seleção no bloco principal.
    temporadas_selecionadas_exib = []
    meses_selecionados_exib = [] # VARIÁVEL DE MÊS RESTAURADA
    
    lojas_selecionadas = []
    segmentos_selecionados = []
    
    # 1. Filtro por Temporada (Definido) - AGORA MULTISELECIONÁVEL
    if 'Temporada_Exibicao' in df_dados_original.columns:
        temporadas_selecionadas_exib = st.sidebar.multiselect(
            "Selecione a Temporada:",
            options=todas_temporadas_disponiveis_unicas,
            default=todas_temporadas_disponiveis_unicas # Manter todas selecionadas
        )
        
        # Filtra o DataFrame base pelo período de tempo selecionado
        if temporadas_selecionadas_exib:
            df_base_para_filtros = df_base_para_filtros[df_base_para_filtros['Temporada_Exibicao'].isin(temporadas_selecionadas_exib)].copy()
        
    # 2. Filtro por Mês (RESTAUROU O MULTISELECT DE MÊS)
    if 'Mês_Exibicao' in df_base_para_filtros.columns:
        # AQUI usamos dropna() para remover meses que não foram mapeados (os 'esquisitos')
        meses_unicos_exib = sorted(df_base_para_filtros['Mês_Exibicao'].dropna().unique())
        
        # Define a variável 'meses_selecionadas_exib'
        meses_selecionados_exib = st.sidebar.multiselect(
            "Selecione o Mês:",
            options=meses_unicos_exib,
            default=meses_unicos_exib
        )
        
        # Aplicação do Filtro de Mês (AGORA DENTRO DO BLOCO IF)
        if meses_selecionados_exib:
            df_base_para_filtros = df_base_para_filtros[df_base_para_filtros['Mês_Exibicao'].isin(meses_selecionados_exib)].copy()

    
    # O df_total_periodo agora contém os filtros de Temporada e Mês
    df_total_periodo = df_base_para_filtros.copy()
    
    
    # === FILTROS HIERÁRQUICOS (SEGMENTO > LOJA) - NOVO MODELO ===
    st.sidebar.subheader("Filtros de Entidade")

    # 3. Filtro SEGMENTO (Primeiro Nível - Independente de Loja)
    segmentos_unicos_todos = sorted(df_total_periodo['Segmento'].unique()) # Base de todos os segmentos no período
    segmentos_selecionados = st.sidebar.multiselect(
        "Selecione o Segmento:",
        options=segmentos_unicos_todos,
        default=segmentos_unicos_todos
    )

    # DataFrame APÓS filtro de SEGMENTO (mas ainda dentro do período)
    df_apos_segmento = df_total_periodo[df_total_periodo['Segmento'].isin(segmentos_selecionados)]
    
    # CRIAÇÃO DO DF DE SEGMENTO TOTAL (USADO EM ITEM 1)
    # df_segmento_total é igual a df_apos_segmento (Segmento + Data)
    df_segmento_total = df_apos_segmento.copy()

    # 4. Filtro LOJA (Segundo Nível - Opcional e dependente do Segmento/Período)
    # Mostra APENAS as lojas que estão no Segmento e Período selecionados
    lojas_unicas_segmento = sorted(df_apos_segmento['Loja'].unique())
    
    # Usamos todas as lojas que apareceram para o segmento/período como default
    lojas_selecionadas = st.sidebar.multiselect(
        "Selecione a Loja (Filtro Secundário):",
        options=lojas_unicas_segmento,
        default=lojas_unicas_segmento
    )

    # === CRIAÇÃO DO DATAFRAME FINAL FILTRADO (SEGMENTO/LOJA/DATA) ===
    # O df_filtrado contem todos os filtros aplicados (Data + Segmento + Loja)
    df_filtrado = df_apos_segmento[df_apos_segmento['Loja'].isin(lojas_selecionadas)].copy()
    
    # Se o filtro de Loja tiver sido desmarcado, voltamos à base de Segmento (df_apos_segmento)
    if not lojas_selecionadas:
        df_filtrado = df_apos_segmento.copy()

    
    # --------------------------------------------------------------------------
    # CÁLCULOS DE MÉTRICAS BASE (Para os KPIs do topo)
    # --------------------------------------------------------------------------
    
    # Segmento/Loja (Filtrado) - USA FUNÇÃO IMPORTADA
    pontos_filtro, pedidos_filtro, novos_clientes_filtro, valor_medio_filtro = calcular_metricas(df_filtrado)
    
    # Segmento (Total - Apenas filtros de Data e Segmento) - USA FUNÇÃO IMPORTADA
    pontos_segmento, pedidos_segmento, novos_clientes_segmento, valor_medio_segmento = calcular_metricas(df_segmento_total)
    
    # Gabriel Pro (Total - Apenas filtros de Data/Temporada) - USA FUNÇÃO IMPORTADA
    pontos_gabriel, pedidos_gabriel, novos_clientes_gabriel, valor_medio_gabriel = calcular_metricas(df_total_periodo)


    # --------------------------------------------------------------------------
    # MÉTRICAS CHAVE (KPIs no topo)
    # --------------------------------------------------------------------------
    st.subheader("Métricas Chave (KPIs)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Soma Total de Pontos (Filtrado)", 
            value=formatar_milhar_br(pontos_filtro)
        )
        
    with col2:
        st.metric(
            label="Total de Pedidos Lançados (Filtrado)", 
            value=formatar_milhar_br(pedidos_filtro)
        )

    with col3:
        st.metric(
            label="Total de Pessoas Pontuadas (Filtrado)", 
            value=formatar_milhar_br(df_filtrado['CNPJ_CPF_LIMPO'].nunique())
        )
        
    st.markdown("---")


    # =======================================================================
    # ITEM 1. Comparativo de Desempenho por Temporada
    # =======================================================================
    
    # 1. Obter a lista de todas as temporadas para os seletores
    # Já usamos 'todas_temporadas_disponiveis_unicas'
    
    # 2. Calcular Métricas Temporais para a Base Filtrada (df_filtrado) - USA FUNÇÃO IMPORTADA
    df_desempenho_filtrado = calcular_metricas_temporais(
        df_filtrado, # Usamos a base totalmente filtrada
        todas_temporadas_disponiveis_unicas, 
        'Gabriel Pro Total'
    )
    
    # 3. Combine o DataFrame para a exibição no Streamlit
    df_combinado = pd.concat([df_desempenho_filtrado], 
                            keys=['Gabriel Pro Filtrado'], 
                            axis=1)
    
    # Criar uma tabela formatada para a exibição
    st.subheader("1. Comparativo de Desempenho por Temporada")
    st.markdown("##### Performance por Temporada (Filtrada por Segmento e Loja)")
    
    # Estilização: Apenas uma coluna de nível 0 agora.
    st.dataframe(
        df_combinado.style
            .set_table_styles([
                {'selector': 'th.col_heading.level0.col_heading_level0_0', 'props': [('background-color', '#1E90FF'), ('color', 'white')]},
                {'selector': 'th.col_heading.level1', 'props': [('font-size', '10px')]},
                {'selector': 'th.row_heading', 'props': [('background-color', '#333333'), ('color', 'white'), ('font-weight', 'bold')]},
            ]),
        use_container_width=True
    )

    st.markdown("---")


    # =======================================================================
    # ITEM 2. Comparativo de Profissionais por Categoria (Gabriel Pro)
    # =======================================================================
    st.subheader("2. Comparativo de Profissionais por Categoria (Gabriel Pro)")

    # === NOVOS SELETORES NO TOPO DO ITEM 2 ===
    col_t2_1, col_t2_2 = st.columns(2)
    
    with col_t2_1:
        temporada_selecionada_t2 = st.selectbox(
            "Selecione a Temporada para Comparação:",
            options=['Todas'] + todas_temporadas_disponiveis_unicas,
            index=0,
            key='item2_temp_select'
        )
    with col_t2_2:
        segmento_selecionado_t2 = st.selectbox(
            "Selecione o Segmento de Referência:",
            options=['Todos'] + segmentos_unicos_todos,
            index=0,
            key='item2_seg_select'
        )

    # === FILTROS LOCAIS PARA OS CÁLCULOS ===

    # 1. Filtro da Base TOTAL (Gabriel Pro)
    if temporada_selecionada_t2 == 'Todas':
        df_base_gabriel = df_dados_original.copy()
    else:
        df_base_gabriel = df_dados_original[df_dados_original['Temporada_Exibicao'] == temporada_selecionada_t2].copy()

    # 2. Filtro da Base de SEGMENTO (Filtro Segmento local E Temporada local)
    if segmento_selecionado_t2 == 'Todos':
        df_base_segmento = df_base_gabriel.copy()
    else:
        df_base_segmento = df_base_gabriel[df_base_gabriel['Segmento'] == segmento_selecionado_t2].copy()

    
    # 2. CÁLCULO PARA O ESCOPO TOTAL (GABRIEL PRO)
    # NOVO AGRUPAMENTO: Agrupa pela CHAVE CONSOLIDADA
    df_gabriel_base = df_base_gabriel.groupby(COLUNA_CHAVE_CONSOLIDADA)['Pontos'].sum().reset_index()
    df_gabriel_base.columns = [COLUNA_CHAVE_CONSOLIDADA, 'Pontuacao_Total']
    # USA FUNÇÃO IMPORTADA
    df_desempenho_gabriel = calcular_categorias(df_base_gabriel, df_gabriel_base) 

    # 3. CÁLCULO PARA O ESCOPO SEGMENTO 
    # NOVO AGRUPAMENTO: Agrupa pela CHAVE CONSOLIDADA
    df_segmento_base = df_base_segmento.groupby(COLUNA_CHAVE_CONSOLIDADA)['Pontos'].sum().reset_index()
    df_segmento_base.columns = [COLUNA_CHAVE_CONSOLIDADA, 'Pontuacao_Total']
    # USA FUNÇÃO IMPORTADA
    df_desempenho_segmento = calcular_categorias(df_base_segmento, df_segmento_base)
    
    # 4. AGRUPAMENTO FINAL DAS CATEGORIAS (Contagem de Profissionais) - USA FUNÇÃO IMPORTADA
    
    # Renomeia temporariamente para COLUNA_ESPECIFICADOR para a função get_contagem_categoria
    # contar o número de CHAVES CONSOLIDADAS, e não o número de CPFs/CNPJs não agrupados
    df_desempenho_gabriel_ajustado = df_desempenho_gabriel.rename(columns={COLUNA_CHAVE_CONSOLIDADA: COLUNA_ESPECIFICADOR})
    df_desempenho_segmento_ajustado = df_desempenho_segmento.rename(columns={COLUNA_CHAVE_CONSOLIDADA: COLUNA_ESPECIFICADOR})

    contagem_segmento_cat = get_contagem_categoria(df_desempenho_segmento_ajustado, CATEGORIAS_NOMES)
    contagem_gabriel_cat = get_contagem_categoria(df_desempenho_gabriel_ajustado, CATEGORIAS_NOMES)
    
    
    # 5. CONSTRUÇÃO DA TABELA FINAL + CÁLCULO DA PARTICIPAÇÃO (ITEM 1)
    categorias_ordenadas = CATEGORIAS_NOMES 
    tabela_categorias = []
    
    for categoria in categorias_ordenadas:
        qtd_segmento = contagem_segmento_cat[categoria]
        qtd_gabriel = contagem_gabriel_cat[categoria]
        
        # CÁLCULO DA PARTICIPAÇÃO (ITEM 1)
        participacao_raw = qtd_segmento / qtd_gabriel if qtd_gabriel > 0 else 0.0
        
        # Formatação do valor para exibição (string)
        participacao_texto = f"{participacao_raw:.1%}"
        
        tabela_categorias.append({
            'Profissional Ativo': categoria,
            'Qtd Segmento': qtd_segmento,
            'Qtd Gabriel Pro': qtd_gabriel,
            'Participacao': participacao_raw, # Armazenamos o valor raw para estilização
            'Participacao Texto': participacao_texto # Armazenamos o texto formatado para exibição
        })

    df_categorias_comparativo = pd.DataFrame(tabela_categorias)
    
    # 6. Adicionar Linha Total
    total_row = {
        'Profissional Ativo': 'Total',
        # Soma a contagem total de entidades, incluindo 'Sem Categoria' (que deve estar em contagem_segmento_cat)
        'Qtd Segmento': contagem_segmento_cat.get('Sem Categoria', 0) + df_categorias_comparativo['Qtd Segmento'].sum(),
        'Qtd Gabriel Pro': contagem_gabriel_cat.get('Sem Categoria', 0) + df_categorias_comparativo['Qtd Gabriel Pro'].sum(),
        'Participacao': 0, 
        'Participacao Texto': '' 
    }

    # CÁLCULO DA PARTICIPAÇÃO TOTAL (Linha Total)
    qtd_loja_total = total_row['Qtd Segmento']
    qtd_segmento_total = total_row['Qtd Gabriel Pro']
    
    participacao_total_raw = qtd_loja_total / qtd_segmento_total if qtd_segmento_total > 0 else 0.0
    participacao_total_formatado = f"{participacao_total_raw:.1%}"
    
    total_row['Participacao Texto'] = participacao_total_formatado
    total_row['Participacao'] = participacao_total_raw

    df_categorias_comparativo = pd.concat([df_categorias_comparativo, pd.DataFrame([total_row])], ignore_index=True)
    
    # =======================================================================
    # CORREÇÃO PARA O KEY ERROR DO ITEM 2
    # =======================================================================
    
    # *CRÍTICO: Resetar o índice para garantir que seja único antes de aplicar a estilização*
    df_exibir_categorias = df_categorias_comparativo.copy().reset_index(drop=True)
    
    # Função de Estilização (Item 2)
    def style_participacao(val):
        # Agora, a linha 'Total' é sempre o último índice do DataFrame resetado (df_exibir_categorias.index[-1])
        if val.name == df_exibir_categorias.index[-1]:
            return ['font-weight: bold; background-color: #333333; color: white'] * len(val)

        return ['color: #d1d1d1; font-weight: bold'] * len(val)
        
    # 7. Exibição da Tabela
    # USA FUNÇÃO IMPORTADA style_nome_categoria
    st.dataframe(
        df_exibir_categorias[['Profissional Ativo', 'Qtd Segmento', 'Qtd Gabriel Pro', 'Participacao Texto']].style
            
            .applymap(style_nome_categoria, subset=['Profissional Ativo']) 
            .apply(style_participacao, subset=['Participacao Texto'], axis=1) # Usa a função ajustada
            .format({col: '{:,.0f}' for col in ['Qtd Segmento', 'Qtd Gabriel Pro']})
            # Usa a referência para a linha Total na nova cópia do DF
            .set_properties(**{'font-weight': 'bold'}, subset=pd.IndexSlice[df_exibir_categorias['Profissional Ativo'] == 'Total', :])
            .set_properties(**{'text-align': 'center'}, subset=pd.IndexSlice[:, ['Qtd Segmento', 'Qtd Gabriel Pro', 'Participacao Texto']]), 
        use_container_width=True,
        column_config={
            "Participacao Texto": st.column_config.
                                    Column("Participação Loja/Segmento", 
                                            help="Participação da Contagem de Profissionais da Loja na Contagem de Profissionais do Segmento.",
                                            width="medium")
        }
    )
    
    # =======================================================================
    # FIM DA CORREÇÃO PARA O KEY ERROR DO ITEM 2
    # =======================================================================
    
    st.markdown("---")


    # =======================================================================
    # ITEM 3. Evolução da Pontuação por Mês e Temporada (Filtrado)
    # =======================================================================
    st.subheader("3. Evolução da Pontuação por Mês e Temporada (Filtrado)")
    
    if 'Mês_Exibicao' in df_filtrado.columns and 'Temporada_Exibicao' in df_filtrado.columns:
        
        # 1. Calcular Pivô e Colunas - USA FUNÇÃO IMPORTADA
        df_pivot_pontos, colunas_a_exibir = calcular_pivo_pontos(
            df_dados_original, df_filtrado, meses_selecionados_exib, temporadas_selecionadas_exib
        )
        
        # 5. Cálculo da Evolução em Porcentagem (Apenas se houver 2 ou mais selecionadas)
        
        if len(temporadas_selecionadas_exib) >= 2:
            
            t_atual_col = sorted(temporadas_selecionadas_exib, key=lambda x: int(x.split(' ')[1]))[-1]
            t_anterior_col = sorted(temporadas_selecionadas_exib, key=lambda x: int(x.split(' ')[1]))[-2]
            nome_coluna_evolucao = f"Evolução Pontos ({t_atual_col.replace('Temporada ', 'T')} vs {t_anterior_col.replace('Temporada ', 'T')})"
            # Lista as colunas de temporada sem a coluna de Evolução
            colunas_temporada_sorted_num = [col for col in colunas_a_exibir if not col.startswith('Evolução')]
            
            def style_evolucao_percentual_texto(series):
                raw_values = df_pivot_pontos['Evolução Pontos Valor']
                
                cor_pos = 'color: #a3ffb1; font-weight: bold' # Verde ajustado
                cor_neg = 'color: #ff9999; font-weight: bold' 
                cor_est = 'color: #b3e6ff; font-weight: bold' 

                styles = []
                for index, val in raw_values.items():
                    if index == 'Total':
                        style = 'font-weight: bold; background-color: #333333; '
                        if val > 0.0001:
                            styles.append(style + 'color: #a3ffb1') 
                        elif val < -0.0001:
                            styles.append(style + 'color: #ff9999') 
                        else:
                            styles.append(style + 'color: #b3e6ff') 
                    else:
                        if val > 0.0001:
                            styles.append(cor_pos)
                        elif val < -0.0001:
                            styles.append(cor_neg)
                        else:
                            styles.append(cor_est)
                    
                return styles
            
            st.dataframe(
                df_pivot_pontos[colunas_a_exibir].style.format({col: lambda x: formatar_milhar_br(x) 
                                                               for col in colunas_temporada_sorted_num})
                                                .apply(style_evolucao_percentual_texto, subset=[nome_coluna_evolucao], axis=0) 
                                                .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}, 
                                                              subset=pd.IndexSlice[:, colunas_temporada_sorted_num]),
                use_container_width=True
            )

            df_pivot_pontos = df_pivot_pontos.drop(columns=['Evolução Pontos Valor'])
            
            st.markdown(f"**Nota:** A coluna de Evolução Pontos compara o crescimento mensal entre a **{t_atual_col.replace('Temporada ', 'T')}** (Atual) e a **{t_anterior_col.replace('Temporada ', 'T')}** (Anterior) seleccionadas.")

        else:
            
            # A coluna de exibição agora é o que veio do módulo
            colunas_temporada_sorted_num = colunas_a_exibir
            
            # 1. Aplicamos o reset_index() aqui, para a estilização funcionar na coluna 'Mês'
            df_pivot_pontos_clean = df_pivot_pontos.reset_index()
            
            # 2. Definir a função local de estilo da linha Total para o DataFrame resetado
            def style_total_pontuacao_resetado(row):
                # A linha 'Total' é identificada pelo valor na coluna 'Mês'
                if row['Mês'] == 'Total': 
                    return ['font-weight: bold; background-color: #333333; color: white'] * len(row)
                return [''] * len(row)
                
            st.dataframe(
                df_pivot_pontos_clean[colunas_temporada_sorted_num + ['Mês']].style
                                                                .apply(style_total_pontuacao_resetado, axis=1) # Aplica o estilo na linha 'Total'
                                                                .format({col: lambda x: formatar_milhar_br(x)
                                                                    for col in colunas_temporada_sorted_num})
                                                                .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'})
                                                                ,
                use_container_width=True
            )

    st.markdown("---")


    # =======================================================================
    # ITEM 4. Pontuação Total por Temporada (Comparativo de Volume)
    # =======================================================================
    st.subheader("4. Pontuação Total por Temporada (Comparativo de Volume)")
    
    if temporadas_selecionadas_exib:
        
        # 1. Agrupar Pontuação Total por Temporada 
        df_pontos_por_temporada = df_filtrado.groupby('Temporada_Exibicao')['Pontos'].sum().reset_index()
        df_pontos_por_temporada.columns = ['Temporada', 'Pontuação Total']
        
        # 2. Ordenar as temporadas numericamente (T7, T8, T9, T10...)
        df_pontos_por_temporada['Ordem'] = df_pontos_por_temporada['Temporada'].apply(lambda x: int(x.split(' ')[1]))
        df_pontos_por_temporada.sort_values(by='Ordem', inplace=True)
        
        if df_pontos_por_temporada.empty:
            st.info("Nenhuma pontuação encontrada nas temporadas selecionadas para a entidade filtrada.")
        else:
            # 3. Gerar o gráfico de barras
            fig = px.bar(
                df_pontos_por_temporada, 
                x='Temporada', 
                y='Pontuação Total', 
                color='Temporada', 
                title='Pontuação Total por Temporada (Segmento/Loja Filtrado)',
                labels={'Pontuação Total': 'Pontuação Total'},
                height=400,
                text='Pontuação Total' 
            )
            
            fig.update_traces(texttemplate='%{text:,.0f}') 
            fig.update_layout(
                yaxis_title="Pontuação Total",
                xaxis_title="Temporada",
                title_font_size=14,
                showlegend=False 
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        
    elif not temporadas_selecionadas_exib:
        st.info("Selecione pelo menos uma Temporada no filtro lateral para ver a pontuação total.")

    st.markdown("---")


    # =======================================================================
    # ITEM 5. Análise de Distribuição Total (Segmento - Pontos e Pedidos no Período Selecionado)
    # =======================================================================
    st.subheader("5. Análise de Distribuição Total (Segmento - Pontos e Pedidos no Período Selecionado)")
    
    # === NOVO SELETOR DE MÉTRICA ===
    metrica_selecionada = st.selectbox(
        'Selecione a Métrica para Distribuição Total:',
        ('Pontos Totais', 'Pedidos Únicos')
    )
    
    # === CÁLCULO DINÂMICO DA MÉTRICA ===
    if metrica_selecionada == 'Pontos Totais':
        # Cálculo para Pontos
        df_segmento_metrica = df_total_periodo.groupby('Segmento')['Pontos'].sum().reset_index()
        df_segmento_metrica.columns = ['Segmento', 'Metrica_Somada']
        eixo_y_titulo = "Total de Pontos"
        titulo_grafico = 'Pontos Totais por Segmento (Geral do Período)'
    else:
        # Cálculo para Pedidos
        df_segmento_metrica = df_total_periodo.groupby('Segmento')[COLUNA_PEDIDO].nunique().reset_index()
        df_segmento_metrica.columns = ['Segmento', 'Metrica_Somada']
        eixo_y_titulo = "Total de Pedidos"
        titulo_grafico = 'Pedidos Únicos por Segmento (Geral do Período)'


    # === GRÁFICO ÚNICO (COMPARAÇÃO POR ALTERNÂNCIA) ===
    fig_segmento_total = px.bar(
        df_segmento_metrica, 
        x='Segmento', 
        y='Metrica_Somada', 
        title=titulo_grafico,
        color='Segmento',
        text='Metrica_Somada'
    )
    fig_segmento_total.update_traces(texttemplate='%{text:,.0f}') 
    fig_segmento_total.update_layout(xaxis_title="Segmento", yaxis_title=eixo_y_titulo) 
    st.plotly_chart(fig_segmento_total, use_container_width=True)
    
    
    st.markdown("---")
    # =======================================================================
    # ITEM 6. Tendência de Pontos (Pontos Totais) & 6.A Pedidos Únicos por Mês
    # =======================================================================
    
    st.subheader("6. Análise de Tendência Mensal")
    
    # === NOVO SELETOR NO TOPO DO ITEM 6 / 6A ===
    temporada_selecionada_t6 = st.selectbox(
        "Selecione a Temporada para a Análise Mensal:",
        options=['Todas'] + todas_temporadas_disponiveis_unicas,
        index=0,
        key='item6_temp_select'
    )

    # Filtro da Base Local
    if temporada_selecionada_t6 == 'Todas':
        df_base_tendencia = df_filtrado.copy()
    else:
        df_base_tendencia = df_filtrado[df_filtrado['Temporada_Exibicao'] == temporada_selecionada_t6].copy()
        
    
    # 6. Tendência de Pontos (Pontos Totais)
    if 'Data da Venda' in df_base_tendencia.columns:
        st.markdown("###### 6. Tendência de Pontos (Pontos Totais)")
        
        # Agrupa os dados por mês/ano e soma os Pontos
        df_tendencia = df_base_tendencia.set_index('Data da Venda').resample('M')['Pontos'].sum().reset_index()
        df_tendencia.columns = ['Data', 'Pontos Totais']
        
        fig_tendencia = px.line(
            df_tendencia,
            x='Data',
            y='Pontos Totais',
            title=f'Pontos Totais por Mês/Ano (Filtro: {temporada_selecionada_t6})',
            markers=True
        )
        fig_tendencia.update_layout(yaxis_title="Pontos Totais")
        st.plotly_chart(fig_tendencia, use_container_width=True)

    st.markdown("---")
    # 6. A. Pedidos Únicos por Mês
    if 'Mês_Exibicao' in df_base_tendencia.columns and COLUNA_PEDIDO in df_base_tendencia.columns:
        st.markdown("###### 6 A. Pedidos Únicos por Mês")
        
        # Agrupa o DataFrame FILTRADO pelo Mês de Exibição e conta os pedidos únicos
        df_pedidos_por_mes = df_base_tendencia.groupby('Mês_Exibicao')[COLUNA_PEDIDO].nunique().reset_index()
        df_pedidos_por_mes.columns = ['Mês', 'Pedidos']
        
        # Para garantir a ordem correta dos meses (Jul, Ago, Set, etc.), precisamos ordenar pelo Mês_num original
        df_pedidos_por_mes['Mês_Ordem'] = df_pedidos_por_mes['Mês'].map(MES_ORDEM_FISCAL)
        df_pedidos_por_mes.sort_values(by='Mês_Ordem', inplace=True)
        df_pedidos_por_mes.drop(columns=['Mês_Ordem'], inplace=True)
        
        fig_pedidos_mes = px.bar(
            df_pedidos_por_mes,
            x='Mês',
            y='Pedidos',
            title=f'Contagem de Pedidos Únicos por Mês (Filtro: {temporada_selecionada_t6})',
            color='Mês',
            text='Pedidos'
        )
        fig_pedidos_mes.update_traces(texttemplate='%{text:,.0f}') 
        fig_pedidos_mes.update_layout(xaxis_title="Mês", yaxis_title="Pedidos Únicos")
        st.plotly_chart(fig_pedidos_mes, use_container_width=True)


    st.markdown("---")
    # =======================================================================
    # ITEM 6 B. Evolução de Pedidos Únicos por Mês e Temporada (Detalhe)
    # =======================================================================
    if 'Mês_Exibicao' in df_filtrado.columns and 'Temporada_Exibicao' in df_filtrado.columns and COLUNA_PEDIDO in df_filtrado.columns:
        st.subheader("6 B. Evolução de Pedidos Únicos por Mês e Temporada (Detalhe por Segmento)")
        st.markdown("##### Pedidos Únicos por Mês e Temporada (Entidade Filtrada)")

        # 1. Preparação dos dados do Pivô (Pedidos Únicos) - USA FUNÇÃO IMPORTADA
        df_pivot_pedidos_display, colunas_temporada_tx = calcular_pivo_pedidos(df_filtrado, temporadas_selecionadas_exib)

        
        # 2. Adicionar linha de TOTAL e Estilização (a lógica já está em pedidos.py, só precisamos da função de estilo)
        
        # Estilização: linha Total (fundo escuro e texto branco)
        def style_total_row_pedidos(row):
            if row.name == 'Total':
                return ['font-weight: bold; background-color: #333333; color: white'] * len(row)
            return [''] * len(row)
            
        # Configuração das colunas para permitir a formatação
        colunas_config_pedidos = {
            'Mês': st.column_config.Column("Mês", width="small"),
        }
        
        # Exibe a tabela pivô (sem interatividade de clique)
        st.dataframe(
            df_pivot_pedidos_display.style
                .apply(style_total_row_pedidos, axis=1) # Estiliza a linha Total
                .format({col: formatar_milhar_br for col in colunas_temporada_tx}) # Formatação dos valores
                .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}, 
                                subset=pd.IndexSlice[:, colunas_temporada_tx]),
            column_config=colunas_config_pedidos,
            use_container_width=True,
        )

        st.markdown("---")
        
        # 3. Lógica de Detalhe por Segmento (Usando Seletores)
        
        # Obter a lista de meses e temporadas disponíveis no pivô exibido
        meses_detalhe = [m for m in df_pivot_pedidos_display.index if m != 'Total']
        temporadas_detalhe = colunas_temporada_tx

        if meses_detalhe and temporadas_detalhe:
            
            st.markdown("##### 6 B. Detalhe da Distribuição por Segmento")
            col_sel_mes, col_sel_temp = st.columns(2)
            
            with col_sel_mes:
                mes_selecionado_exib = st.selectbox(
                    "Selecione o Mês para Detalhe:",
                    options=meses_detalhe,
                    key='detalhe_mes_sel',
                    index=0 # Inicia no primeiro mês
                )
                
            with col_sel_temp:
                temporada_selecionada_tx = st.selectbox(
                    "Selecione a Temporada para Detalhe:",
                    options=temporadas_detalhe,
                    key='detalhe_temp_sel',
                    index=len(temporadas_detalhe) - 1 # Inicia na última temporada
                )
                
            # CRÍTICO: CORREÇÃO AQUI - Converte o valor da célula para string antes de limpar a formatação
            valor_celula_str = str(df_pivot_pedidos_display.loc[mes_selecionado_exib, temporada_selecionada_tx])

            # Verifica se há dados na célula selecionada antes de prosseguir
            valor_numerico = pd.to_numeric(valor_celula_str.replace('.', '').replace(',', '.'), errors='coerce')

            if valor_numerico > 0:
                
                # Transforma Tx de volta para o nome completo 'Temporada X'
                t_num = temporada_selecionada_tx.replace('T', '')
                temporada_selecionada_exib = f'Temporada {t_num}'
                
                # 3.1. Filtro da Base Completa (df_filtrado já contém Loja/Segmento)
                df_detalhe = df_filtrado[
                    (df_filtrado['Mês_Exibicao'] == mes_selecionado_exib) &
                    (df_filtrado['Temporada_Exibicao'] == temporada_selecionada_exib)
                ].copy()
                
                # 3.2. Agrupamento por Segmento (Contagem de Pedidos Únicos)
                df_segmentos_detalhe = df_detalhe.groupby('Segmento')[COLUNA_PEDIDO].nunique().reset_index()
                df_segmentos_detalhe.columns = ['Segmento', 'Qtd_Pedidos_Unicos']
                
                # Calcular Porcentagem de Participação no total da célula
                total_pedidos_na_celula = df_segmentos_detalhe['Qtd_Pedidos_Unicos'].sum()
                df_segmentos_detalhe['Participação (%)'] = df_segmentos_detalhe['Qtd_Pedidos_Unicos'].apply(
                    lambda x: x / total_pedidos_na_celula if total_pedidos_na_celula > 0 else 0.0
                )
                
                df_segmentos_detalhe.sort_values(by='Qtd_Pedidos_Unicos', ascending=False, inplace=True)
                
                    # Gráfico
                fig_detalhe = px.bar(
                            df_segmentos_detalhe,
                            x='Segmento',
                            y='Qtd_Pedidos_Unicos',
                            title=f"Distribuição de Pedidos por Segmento em {mes_selecionado_exib} ({temporada_selecionada_exib})",
                            color='Segmento',
                            text='Qtd_Pedidos_Unicos'
                        )
                fig_detalhe.update_traces(texttemplate='%{text:,.0f}')
                st.plotly_chart(fig_detalhe, use_container_width=True)
                    
                    # Tabela
                st.markdown("##### Tabela Detalhada por Segmento")
                st.dataframe(
                        df_segmentos_detalhe.style
                            .format({
                                # USA FUNÇÃO IMPORTADA formatar_milhar_br
                                'Qtd_Pedidos_Unicos': formatar_milhar_br,
                                'Participação (%)': '{:.1%}'
                            })
                            .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}),
                        use_container_width=True
                    )
            else:
                st.info(f"O valor de pedidos é zero ou N/A para o período {mes_selecionado_exib} / {temporada_selecionada_tx}. Selecione outro período.")

        else:
            st.info("Não há meses ou temporadas suficientes para exibir o detalhe. Verifique os filtros laterais.")
            
        st.markdown("---") 

    # =======================================================================
    # ITEM 6 C. Evolução de Pontuação por Segmento (T_ATUAL vs T_ANTERIOR)
    # =======================================================================

    # 1. Identificar as duas últimas temporadas selecionadas no filtro lateral
    temporadas_ordenadas = sorted([t for t in temporadas_selecionadas_exib if t.startswith('Temporada')],
                                     key=lambda x: int(x.split(' ')[1]))

    if len(temporadas_ordenadas) >= 2: 
        
        # T_Atual e T_Anterior são as duas últimas selecionadas
        t_atual_nome = temporadas_ordenadas[-1]
        t_anterior_nome = temporadas_ordenadas[-2]
        t_atual_tx = t_atual_nome.replace('Temporada ', 'T')
        t_anterior_tx = t_anterior_nome.replace('Temporada ', 'T')
        
        st.subheader(f"6 C. Evolução de Pontuação por Segmento ({t_atual_tx} vs {t_anterior_tx})")
        
        # 2. Filtrar o DF para conter apenas os dados dessas duas temporadas e os meses selecionados
        # df_filtrado já contém os filtros de Loja/Segmento e Mês
        df_base_t_vs_t = df_filtrado[
            df_filtrado['Temporada_Exibicao'].isin([t_atual_nome, t_anterior_nome])
        ].copy()
        
        # 3. Agrupamento da Pontuação por Segmento e Temporada
        df_pivot_pontos_segmento = df_base_t_vs_t.groupby(['Segmento', 'Temporada_Exibicao'])['Pontos'].sum().reset_index()
        
        # 4. Pivotear a tabela para ter Pontuação T_Atual e Pontuação T_Anterior
        df_segmento_evolucao = df_pivot_pontos_segmento.pivot_table(
            index='Segmento',
            columns='Temporada_Exibicao',
            values='Pontos',
            fill_value=0
        ).reset_index()
        
        # Renomear as colunas da pontuação
        df_segmento_evolucao.rename(columns={
            t_atual_nome: f'Pontuação {t_atual_tx}',
            t_anterior_nome: f'Pontuação {t_anterior_tx}'
        }, inplace=True)
        
        # Colunas renomeadas para fácil acesso
        col_pontos_atual = f'Pontuação {t_atual_tx}'
        col_pontos_anterior = f'Pontuação {t_anterior_tx}'
        
        # 5. Cálculo da Evolução (%) - USA FUNÇÃO IMPORTADA
        df_segmento_evolucao['Evolução %'] = df_segmento_evolucao.apply(
            lambda row: calcular_evolucao_pct(row[col_pontos_atual], row[col_pontos_anterior]), axis=1
        )
        
        
        # 6. Cálculo da Participação (%) (Sempre sobre a T_Atual)
        total_pontos_atual = df_segmento_evolucao[col_pontos_atual].sum()
        df_segmento_evolucao['Participação %'] = df_segmento_evolucao[col_pontos_atual].apply(
            lambda x: x / total_pontos_atual if total_pontos_atual > 0 else 0.0
        )
        
        # 7. Ordenar por Pontuação T_Atual
        df_segmento_evolucao.sort_values(by=col_pontos_atual, ascending=False, inplace=True)
        
        # 8. Adicionar Linha Total
        total_pontuacao_anterior = df_segmento_evolucao[col_pontos_anterior].sum()
        # Usa a função importada para calcular a evolução do total
        total_evolucao = calcular_evolucao_pct(total_pontos_atual, total_pontuacao_anterior)
        
        total_row_pontos = pd.DataFrame([{
            'Segmento': 'Total',
            col_pontos_atual: total_pontos_atual,
            col_pontos_anterior: total_pontuacao_anterior,
            'Evolução %': total_evolucao,
            'Participação %': 1.0 # Sempre 100% no total
        }])
        
        df_segmento_evolucao = pd.concat([df_segmento_evolucao, total_row_pontos], ignore_index=True)
        
        # 9. Estilização
        
        def style_evolucao_pontuacao(val):
            # Cores para a coluna Evolução %
            if not isinstance(val, (int, float)): return ''
            if val > 0.0001:
                return 'color: #a3ffb1; font-weight: bold' # Verde ajustado
            elif val < -0.0001:
                return 'color: #ff9999; font-weight: bold' # Vermelho
            return 'color: #b3e6ff; font-weight: bold' # Estável/Zero

        # Definir a função local de estilo da linha Total (necessário para a lógica do iloc[0])
        def style_total_pontuacao_local(row):
            if row.iloc[0] == 'Total':
                return ['font-weight: bold; background-color: #333333; color: white'] * len(row)
            return [''] * len(row)
            
        # 10. Exibição da Tabela
        st.dataframe(
            df_segmento_evolucao.style
                .apply(style_total_pontuacao_local, axis=1) # Linha Total
                .applymap(style_evolucao_pontuacao, subset=['Evolução %']) # Cores na Evolução
                .format({
                    # USA FUNÇÃO IMPORTADA formatar_milhar_br
                    col_pontos_atual: formatar_milhar_br,
                    col_pontos_anterior: formatar_milhar_br,
                    'Evolução %': '{:.1%}', # Formato percentual para Evolução
                    'Participação %': '{:.1%}' # Formato percentual para Participação
                })
                .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}, 
                                subset=pd.IndexSlice[:, [col_pontos_atual, col_pontos_anterior, 'Evolução %', 'Participação %']]),
            use_container_width=True
        )
        
        st.markdown(f"""
        **Nota:** A coluna de Evolução % compara a soma total de pontos por segmento entre **{t_atual_tx}** (Atual) e **{t_anterior_tx}** (Anterior), usando os mesmos meses e filtros de entidade selecionados no filtro lateral.
        """)

    else:
        st.info("⚠️ São necessárias pelo menos duas Temporadas selecionadas no filtro lateral para calcular a Evolução de Pontuação por Segmento (Item 6 C).")

    st.markdown("---")


    # =======================================================================
    # NOVO ITEM 7: ANÁLISE CONSOLIDADA DE LOJAS (EVOLUÇÃO E TERÇOS)
    # =======================================================================
    
    # 1. Identificar as duas últimas temporadas selecionadas no filtro lateral
    temporadas_ordenadas = sorted([t for t in temporadas_selecionadas_exib if t.startswith('Temporada')],
                                     key=lambda x: int(x.split(' ')[1]))

    if len(temporadas_ordenadas) >= 2: 
        t_atual_nome = temporadas_ordenadas[-1]
        t_anterior_nome = temporadas_ordenadas[-2]
        t_atual_tx = t_atual_nome.replace('Temporada ', 'T')
        t_anterior_tx = t_anterior_nome.replace('Temporada ', 'T')

        st.subheader(f"7. Análise Consolidada de Lojas ({t_atual_tx} vs {t_anterior_tx})")
        
        # --- FILTRO DE LOJAS BASE (SIMPLIFICADO) ---
        
        # 1. Determina a lista de lojas ativas no período filtrado pela sidebar
        lojas_ativas_na_base = sorted(df_filtrado['Loja'].unique())
        
        # 2. Multiselect de Lojas
        # --- INÍCIO DO TRATAMENTO CRÍTICO DE DEFAULT ---
        # 1. Tenta pegar a seleção anterior do estado
        current_selection_state = st.session_state.get('item7_lojas_select', [])
        
        # 2. Define o valor padrão:
        if 'item7_lojas_select' not in st.session_state or not current_selection_state:
            # Inicializa com a lista completa de lojas ativas na base selecionada
            st.session_state['item7_lojas_select'] = lojas_ativas_na_base
        
        # 3. Garante que a seleção atual respeite as opções DISPONÍVEIS
        lojas_para_usar = [
            loja for loja in st.session_state['item7_lojas_select'] if loja in lojas_ativas_na_base
        ]
        
        # Se a lista atual no estado for maior que a lista filtrada (o filtro da sidebar
        # mudou e removeu lojas), atualizamos o estado.
        if len(lojas_para_usar) < len(st.session_state['item7_lojas_select']):
            st.session_state['item7_lojas_select'] = lojas_para_usar
        
        # O valor a ser usado pelo multiselect é o valor atualizado na sessão.
        default_multiselect = st.session_state['item7_lojas_select']

        lojas_selecionadas_analise = st.multiselect(
            "Selecione a Base de Lojas para Análise (Ativas/Inativas na T9/T10):",
            options=lojas_ativas_na_base, # As opções disponíveis são APENAS as lojas que pontuaram na SIDEBAR
            default=default_multiselect, 
            key='item7_lojas_select'
        )
        # --- FIM DO TRATAMENTO CRÍTICO DE DEFAULT ---


        # Garantir que se o usuário desmarcar todas, a lista não seja vazia
        if not lojas_selecionadas_analise:
            st.info("A base de lojas para a Análise Consolidada está vazia. Selecione as lojas no filtro acima.")
            lojas_selecionadas_analise = [] # Garante que o cálculo não falhe com lista vazia

        
        st.markdown(f"##### Base de Análise: {len(lojas_selecionadas_analise)} Lojas selecionadas, nos meses filtrados ({meses_selecionados_exib})")

        # Chama a função principal de cálculo - USA FUNÇÃO IMPORTADA
        df_evolucao_loja, df_rank_quantitativo, df_rank_pontuacao, df_piramide_sumario = calcular_analise_lojas(
            df_filtrado, t_atual_nome, t_anterior_nome, lojas_selecionadas_analise
        )
        
        # --- PARTE 1: Comparativo de Lojas T vs T-1 (Evolução %) ---
        st.markdown("###### 7.1. Comparativo de Lojas por Evolução de Pontos")

        def style_evolucao_loja(val):
            if not isinstance(val, (int, float)): return ''
            if val > 0.0001:
                return 'color: #a3ffb1; font-weight: bold; background-color: #00800020' # Verde ajustado
            elif val < -0.0001:
                return 'color: #ff9999; font-weight: bold; background-color: #ff000020' # Vermelho Claro
            return 'color: #b3e6ff; font-weight: bold' # Estável/Zero

        df_display_evolucao = df_evolucao_loja.copy()

        # PONTO 1: Ordenação já foi feita no módulo pela T_Anterior
        
        # Renomear e selecionar colunas para exibição
        df_display_evolucao.rename(columns={
            t_anterior_nome: f'Pontos {t_anterior_tx}',
            t_atual_nome: f'Pontos {t_atual_tx}',
        }, inplace=True)
        
        df_display_evolucao = df_display_evolucao[['Loja', f'Pontos {t_anterior_tx}', f'Pontos {t_atual_tx}', 'Evolução %']].copy()
        
        st.dataframe(
            df_display_evolucao.style
                .applymap(style_evolucao_loja, subset=['Evolução %'])
                .format({
                    # USA FUNÇÃO IMPORTADA formatar_milhar_br
                    f'Pontos {t_anterior_tx}': formatar_milhar_br,
                    f'Pontos {t_atual_tx}': formatar_milhar_br,
                    'Evolução %': '{:.1%}',
                })
                .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}, subset=['Evolução %']),
            use_container_width=True
        )

        st.markdown("---")

        # --- PARTE 2: Separação por Terços ---
        
        # Acessa a coluna 'Total de Lojas' e pega o valor total da base de análise
        # CORREÇÃO: O valor de Total de Lojas já é a contagem de lojas por terço, não precisa multiplicar por 3.
        total_lojas_base_tercos = df_rank_quantitativo['Total de Lojas'].sum()
        
        # Ranking Quantitativo (Contagem de Lojas) - PONTO 2: Contagem igualitária de lojas
        st.markdown(f"###### 7.2. Ranking por Terços (Quantitativo de Lojas) - Base: {formatar_milhar_br(total_lojas_base_tercos)} Lojas")
        
        # Prepara o DF para exibição
        df_rank_quantitativo.index = df_rank_quantitativo['Terço']
        df_rank_quantitativo.drop(columns=['Terço', 'Total de Lojas'], inplace=True) # Remove a coluna auxiliar
        
        # Adicionar linha total
        total_lojas_row = df_rank_quantitativo.sum().to_frame(name='Total').T
        total_lojas_row.index.name = 'Total'
        df_rank_quantitativo = pd.concat([df_rank_quantitativo, total_lojas_row])


        st.dataframe(
            df_rank_quantitativo.style
                .format({col: formatar_milhar_br for col in df_rank_quantitativo.columns})
                # Estiliza a linha Total
                .apply(lambda row: ['font-weight: bold; background-color: #333333; color: white'] * len(row) if row.name == 'Total' else [''] * len(row), axis=1) 
                .set_properties(**{'text-align': 'center'}),
            use_container_width=True
        )

        # Ranking da Pontuação (Soma dos Pontos por Terço) - PONTO 3: Pontuação por corte de terços
        st.markdown("###### 7.3. Ranking por Terços (Pontuação Acumulada)")
        df_rank_pontuacao.index = df_rank_pontuacao['Terço']
        df_rank_pontuacao.drop(columns=['Terço'], inplace=True)

        # Total da Pontuação
        total_pontos_row = pd.Series({
            f'Pontuação {t_anterior_tx}': df_rank_pontuacao[t_anterior_nome].sum(),
            f'Pontuação {t_atual_tx}': df_rank_pontuacao[t_atual_nome].sum(),
            # USA FUNÇÃO IMPORTADA calcular_evolucao_pct
            'Evolução %': calcular_evolucao_pct(df_rank_pontuacao[t_atual_nome].sum(), df_rank_pontuacao[t_anterior_nome].sum())
        }, name='Total')
        df_rank_pontuacao.columns = [f'Pontuação {t_anterior_tx}', f'Pontuação {t_atual_tx}', 'Evolução %'] # Corrige nomes
        df_rank_pontuacao = pd.concat([df_rank_pontuacao, pd.DataFrame(total_pontos_row).T])
        
        # Estiliza a Evolução % na tabela de pontuação
        st.dataframe(
            df_rank_pontuacao.style
                .applymap(style_evolucao_loja, subset=['Evolução %'])
                # Estiliza a linha Total
                .apply(lambda row: ['font-weight: bold; background-color: #333333; color: white'] * len(row) if row.name == 'Total' else [''] * len(row), axis=1) 
                .format({
                    # USA FUNÇÃO IMPORTADA formatar_milhar_br
                    f'Pontuação {t_anterior_tx}': formatar_milhar_br,
                    f'Pontuação {t_atual_tx}': formatar_milhar_br,
                    'Evolução %': '{:.1%}'
                })
                .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}),
            use_container_width=True
        )

        st.markdown("---")
        
        # --- PARTE 3: Pirâmide de Evolução das Lojas (Status) ---
        st.markdown("###### 7.4. Pirâmide de Evolução das Lojas (Status)")
        
        st.dataframe(
            df_piramide_sumario.style
                .set_properties(**{'border': '1px solid #333333', 'font-weight': 'bold'})
                .format({'Contagem': formatar_milhar_br}),
            use_container_width=True
        )

        st.markdown("---")

    else:
        st.subheader("7. Análise Consolidada de Lojas (Evolução e Terços)")
        st.info("⚠️ Selecione pelo menos duas Temporadas no filtro lateral para realizar a Análise Consolidada de Lojas.")

    # =======================================================================
    # ITEM 8. DESEMPENHO POR PROFISSIONAL E CATEGORIA (AGRUPADO POR CHAVE CONSOLIDADA)
    # =======================================================================
    if COLUNA_ESPECIFICADOR in df_filtrado.columns:
        st.subheader("8. Desempenho por Entidade/Profissional e Categoria (CONSOLIDADO)")
        
        # === NOVO SELETOR NO TOPO DO ITEM 8 ===
        temporada_selecionada_t8 = st.selectbox(
            "Selecione a Temporada de Análise:",
            options=['Todas'] + todas_temporadas_disponiveis_unicas,
            index=0,
            key='item8_temp_select'
        )

        # Filtro da Base Local
        if temporada_selecionada_t8 == 'Todas':
            # Usa a base filtrada pela SIDEBAR (df_filtrado) para preservar o Segmento/Loja
            df_base_item8 = df_filtrado.copy() 
        else:
            # Filtra a base original pelos filtros de Segmento/Loja e depois pela Temporada local
            df_base_item8 = df_filtrado[df_filtrado['Temporada_Exibicao'] == temporada_selecionada_t8].copy()

        # Helper function to separate CPFs and CNPJs from a list of documents
        def separate_documents(document_list_original):
            cpfs = []
            cnpjs = []
            
            for doc_original in document_list_original:
                if pd.isna(doc_original) or doc_original == 'nan': continue
                
                # 1. Clean document for reliable length check
                doc_limpo = str(doc_original).replace('.', '').replace('-', '').replace('/', '').replace(' ', '')
                
                # 2. Heuristic based on typical Brazilian document length
                # CNPJ: 14 digits (or more if not perfectly cleaned)
                # CPF: 11 digits
                
                if len(doc_limpo) >= 14: # Assume CNPJ if 14+ clean digits
                    cnpjs.append(doc_original)
                elif len(doc_limpo) >= 10: # Assume CPF if 10-13 clean digits (11 standard)
                    cpfs.append(doc_original)
                # Documents shorter than 10 clean digits are likely noise and are ignored.
                     
            return ', '.join(cpfs), ', '.join(cnpjs)


        # 1. Agrupamento pela CHAVE DE CONSOLIDAÇÃO (Pontuação Total E Qtd de Pedidos)
        df_desempenho = df_base_item8.groupby(COLUNA_CHAVE_CONSOLIDADA).agg(
            Pontuacao_Total=('Pontos', 'sum'),
            Qtd_Pedidos=(COLUNA_PEDIDO, 'nunique')
        ).reset_index()
        
        # 2. Agrupamento para obter os VÍNCULOS para a Chave Consolidada
        df_vinculos = df_base_item8.groupby(COLUNA_CHAVE_CONSOLIDADA).agg(
            # Obtém todos os Especificadores/Empresas vinculadas
            Especificadores_Vinculados=(COLUNA_ESPECIFICADOR, lambda x: ', '.join(x.astype(str).unique())),
            # Agrega uma lista de documentos originais UNICOS para separação
            Documentos_Para_Separar=(COLUNA_CNPJ_CPF, lambda x: x.astype(str).unique().tolist()),
        ).reset_index()

        # CRÍTICO: Uso de Series para garantir 2 colunas e tratar o erro de "Columns must be same length as key"
        # O resultado é uma tupla de (str_cpfs, str_cnpjs) para cada linha
        df_vinculos[['CPFs Vinculados', 'CNPJs Vinculados']] = df_vinculos['Documentos_Para_Separar'].apply(
            lambda x: pd.Series(separate_documents(x))
        )
        
        df_vinculos.drop(columns=['Documentos_Para_Separar'], inplace=True) # Remove a coluna intermediária

        df_desempenho = pd.merge(df_desempenho, df_vinculos, on=COLUNA_CHAVE_CONSOLIDADA, how='left')
        
        # 3. Definição da Lógica de Categorias
        df_desempenho_com_categoria = calcular_categorias(df_base_item8, df_desempenho)
        df_desempenho = df_desempenho_com_categoria.copy()
        
        # Ordenar por Pontuação Total (do maior para o menor)
        df_desempenho.sort_values(by='Pontuacao_Total', ascending=False, inplace=True)
        
        # 4. CÁLCULO DE EVOLUÇÃO POR CATEGORIA (BASEADO NA T_ANTERIOR)
        
        temporadas_nums_selecionadas = sorted(df_base_item8[COLUNA_NUMERO_TEMPORADA].unique())
        temporada_atual_num_t8 = max(temporadas_nums_selecionadas) if temporadas_nums_selecionadas else 0
        temporada_anterior_num_t8 = int(temporada_atual_num_t8) - 1 if int(temporada_atual_num_t8) > 0 else 0
        
        # Criamos a tabela de resumo para o topo
        df_resumo_cat = df_desempenho.groupby('Categoria').agg(
            Contagem=(COLUNA_CHAVE_CONSOLIDADA, 'size'), # Contagem agora é feita pela CHAVE CONSOLIDADA
            Pontuacao_Categoria=('Pontuacao_Total', 'sum')
        ).reset_index()
        
        # Inserir as colunas de EVOLUÇÃO (USA FUNÇÃO IMPORTADA get_pontuacao_temporada_anterior)
        evolucao_pontos_list = []
        evolucao_pontos_texto_list = []
        
        for index, row in df_resumo_cat.iterrows():
            categoria = row['Categoria']
            pontuacao_atual = row['Pontuacao_Categoria']
            
            # CRÍTICO: CHAMA A FUNÇÃO CORRIGIDA COM OS FILTROS DE LOJA/SEGMENTO E MÊS (USANDO KEYWORD)
            pontuacao_anterior = get_pontuacao_temporada_anterior(
                df_dados_original, 
                temporada_anterior_num_t8, 
                lojas_selecionadas, 
                segmentos_selecionados, 
                meses_selecionados_exib, 
                categoria=categoria # FORÇANDO KEYWORD
            )
            
            # Calcula o crescimento raw (USA FUNÇÃO IMPORTADA calcular_evolucao_pct)
            crescimento_raw = calcular_evolucao_pct(pontuacao_atual, pontuacao_anterior)

            # Formatação do valor para exibição (string)
            if pontuacao_anterior > 0:
                crescimento_formatado = f"{crescimento_raw:.1%}"
                if crescimento_raw > 0.0001:
                    evolucao_texto = f"{crescimento_formatado} ↑" 
                elif crescimento_raw < -0.0001:
                    evolucao_texto = f"{crescimento_formatado} ↓" 
                else:
                    evolucao_texto = "0.0% ≈" 
            elif pontuacao_atual > 0:
                evolucao_texto = "+100% ↑"
            else:
                evolucao_texto = "N/A"
                
            evolucao_pontos_list.append(crescimento_raw)
            evolucao_pontos_texto_list.append(evolucao_texto)
            
        df_resumo_cat['Evolução Pontos'] = evolucao_pontos_list
        df_resumo_cat['Evolução Pontos Texto'] = evolucao_pontos_texto_list

        # 5. TRATAMENTO DA LINHA 'TOTAL' (SUBSTITUINDO 'SEM CATEGORIA')
        
        # Calculando o Total Geral de Pontos e Contagem (excluindo 'Sem Categoria' do df_resumo_cat para somar)
        df_soma_categorias = df_resumo_cat[df_resumo_cat['Categoria'] != 'Sem Categoria']
        
        total_contagem = df_soma_categorias['Contagem'].sum()
        total_pontuacao = df_soma_categorias['Pontuacao_Categoria'].sum()
        
        # CÁLCULO DA EVOLUÇÃO TOTAL (Todos os profissionais no filtro de Segmento/Loja)
        pontuacao_total_atual = df_base_item8['Pontos'].sum() 
        
        # CRÍTICO: Usamos a T_Atual para achar o valor da T_Anterior (corrigido no módulo)
        pontuacao_total_anterior = get_pontuacao_temporada_anterior(
             df_dados_original, 
             temporada_atual_num_t8, 
             lojas_selecionadas, 
             segmentos_selecionados, 
             meses_selecionados_exib # Argumento meses_selecionados_exib passado
           )
        
        # Calcula o crescimento total raw (USA FUNÇÃO IMPORTADA calcular_evolucao_pct)
        crescimento_total_raw = calcular_evolucao_pct(pontuacao_total_atual, pontuacao_total_anterior)
        
        # Formatação do texto da evolução total
        if pontuacao_total_anterior > 0:
            crescimento_formatado = f"{crescimento_total_raw:.1%}"
            if crescimento_total_raw > 0.0001:
                evolucao_texto_total = f"{crescimento_formatado} ↑" 
            elif crescimento_total_raw < -0.0001:
                evolucao_texto_total = f"{crescimento_formatado} ↓" 
            else:
                evolucao_texto_total = "0.0% ≈" 
        elif pontuacao_total_atual > 0:
            evolucao_texto_total = "+100% ↑"
        else:
            evolucao_texto_total = "N/A"
            
        # Linha Total (Substitui 'Sem Categoria')
        df_total_row = pd.DataFrame([{
            'Categoria': 'Total',
            'Contagem': total_contagem,
            'Pontuacao_Categoria': total_pontuacao,
            'Evolução Pontos': crescimento_total_raw,
            'Evolução Pontos Texto': evolucao_texto_total
        }])
        
        # Filtra 'Sem Categoria' do resumo original e adiciona o 'Total'
        df_resumo_cat = df_resumo_cat[df_resumo_cat['Categoria'] != 'Sem Categoria']
        df_resumo_cat = pd.concat([df_resumo_cat, df_total_row], ignore_index=True)


        # 6. MATRIZ DE RESUMO (KPIs no topo)
        st.markdown("##### Resumo das Categorias (Contagem e Pontuação)")
        
        # Criando o dicionário de cores para os nomes das categorias (para st.markdown)
        cores_map_kpi = {
            'Diamante': '#b3e6ff', 
            'Esmeralda': '#a3ffb1', 
            'Ruby': '#ff9999', 
            'Topázio': '#ffe08a', 
            'Pro': '#d1d1d1', 
            'Total': '#ffffff' 
        }
        
        # Cria a lista de colunas para o display 
        colunas_matriz_display = ['Diamante', 'Esmeralda', 'Ruby', 'Topázio', 'Pro', 'Total']
        
        colunas_kpi_contagem = st.columns(len(colunas_matriz_display))
        colunas_kpi_pontuacao = st.columns(len(colunas_matriz_display))
        
        # Loop para exibir a contagem por categoria
        for i, categoria in enumerate(colunas_matriz_display):
            temp_df = df_resumo_cat.loc[df_resumo_cat['Categoria'] == categoria]
            
            if not temp_df.empty:
                row = temp_df.iloc[0]
                contagem = row['Contagem']
                cor = cores_map_kpi.get(categoria, '#ffffff')
            else:
                contagem = 0
                cor = '#d1d1d1' 
            
            with colunas_kpi_contagem[i]:
                st.markdown(f"<p style='color: {cor}; font-weight: bold; font-size: 14px;'>{categoria}</p>", unsafe_allow_html=True)
                st.metric(label=' ', value=f"{contagem:,.0f}")
                
        # Loop para exibir a pontuação total por categoria
        for i, categoria in enumerate(colunas_matriz_display):
            temp_df = df_resumo_cat.loc[df_resumo_cat['Categoria'] == categoria]
            
            if not temp_df.empty:
                row = temp_df.iloc[0]
                pontuacao = row['Pontuacao_Categoria']
            else:
                pontuacao = 0

            with colunas_kpi_pontuacao[i]:
                st.metric(
                    label=f"Pontos {categoria}", 
                    value=formatar_milhar_br(pontuacao)
                )
        
        colunas_kpi_evolucao = st.columns(len(colunas_matriz_display))
        
        def style_kpi_evolucao(crescimento_raw):
            if isinstance(crescimento_raw, (float, int)):
                if crescimento_raw > 0.0001:
                    color = '#a3ffb1' 
                elif crescimento_raw < -0.0001:
                    color = '#ff9999' 
                else:
                    color = '#b3e6ff' 
                return color
            return '#d1d1d1' 


        for i, categoria in enumerate(colunas_matriz_display):
            temp_df = df_resumo_cat.loc[df_resumo_cat['Categoria'] == categoria]

            if not temp_df.empty:
                row = temp_df.iloc[0]
                evolucao_texto = row['Evolução Pontos Texto']
                crescimento_raw = row['Evolução Pontos']
            else:
                evolucao_texto = "N/A"
                crescimento_raw = 0.0
            
            with colunas_kpi_evolucao[i]:
                cor = style_kpi_evolucao(crescimento_raw)
                st.markdown(f"<p style='color: {cor}; font-weight: bold; font-size: 14px;'>{evolucao_texto}</p>", unsafe_allow_html=True)


        st.markdown("---") # Divisor para separar os KPIs da Tabela
        
        # --- NOVO CAMPO DE PESQUISA ---
        termo_pesquisa = st.text_input(
            "Pesquisar Entidade (Chave Consolidada, Nome, Categoria ou CPF/CNPJ):",
            key='search_profissional',
            placeholder="Digite o nome da empresa, a chave de consolidação ou o CPF/CNPJ vinculado"
        )
        
        df_tabela_exibicao = df_desempenho.copy()
        
        if termo_pesquisa:
            termo_pesquisa_lower = termo_pesquisa.lower()
            
            # Filtra o DataFrame usando 3 colunas (Chave, Especificadores Vinculados e CPFs Vinculados)
            df_tabela_exibicao = df_tabela_exibicao[
                df_tabela_exibicao[COLUNA_CHAVE_CONSOLIDADA].astype(str).str.lower().str.contains(termo_pesquisa_lower) |
                df_tabela_exibicao['Categoria'].astype(str).str.lower().str.contains(termo_pesquisa_lower) |
                df_tabela_exibicao['Especificadores_Vinculados'].astype(str).str.lower().str.contains(termo_pesquisa_lower) |
                (
                    (df_tabela_exibicao['CNPJs Vinculados'].astype(str).str.lower().str.contains(termo_pesquisa_lower, na=False)) |
                    (df_tabela_exibicao['CPFs Vinculados'].astype(str).str.lower().str.contains(termo_pesquisa_lower, na=False))
                )
            ].copy()
            
            if df_tabela_exibicao.empty:
                st.info(f"Nenhuma entidade/profissional consolidado encontrado para o termo: **{termo_pesquisa}**.")
                
        # 7. TABELA DE DESEMPENHO INDIVIDUAL (Matriz)
        st.markdown("##### Tabela de Desempenho Individual (Agrupado por Entidade Consolidada)")
        
        # --- LÓGICA DA EVOLUÇÃO T VS T-1 (NOVO CÁLCULO) ---
        
        # 1. Identificar T-1 para busca de pontuação, respeitando o filtro de Segmento/Loja da sidebar
        temporada_anterior_num = int(temporada_atual_num_t8) - 1 if int(temporada_atual_num_t8) > 0 else 0
        temporada_anterior_nome = f"Temporada {temporada_anterior_num}"
        
        df_base_t_anterior = df_dados_original[
            (df_dados_original['Temporada_Exibicao'] == temporada_anterior_nome) &
            (df_dados_original['Loja'].isin(lojas_selecionadas)) & 
            (df_dados_original['Segmento'].isin(segmentos_selecionados)) &
            (df_dados_original['Mês_Exibicao'].isin(meses_selecionados_exib)) # NOVO FILTRO DE MÊS
        ].copy()

        # 2. Agrupar a pontuação da T-1 pela CHAVE CONSOLIDADA
        df_pontos_t_anterior = df_base_t_anterior.groupby(COLUNA_CHAVE_CONSOLIDADA)['Pontos'].sum().reset_index()
        df_pontos_t_anterior.columns = [COLUNA_CHAVE_CONSOLIDADA, 'Pontuacao_T_Anterior']
        
        # 3. Merge dos pontos T-1 no DataFrame de exibição
        df_tabela_exibicao = pd.merge(
            df_tabela_exibicao,
            df_pontos_t_anterior,
            on=COLUNA_CHAVE_CONSOLIDADA,
            how='left'
        ).fillna({'Pontuacao_T_Anterior': 0})
        
        # 4. Calcular a Evolução %
        df_tabela_exibicao['Evolução %'] = df_tabela_exibicao.apply(
            lambda row: calcular_evolucao_pct(row['Pontuacao_Total'], row['Pontuacao_T_Anterior']), axis=1
        )
        
        # 5. Formatar a coluna de Evolução % (Texto e Cor)
        
        # Mapeamento do nome da coluna de evolução
        nome_coluna_evolucao_item8 = f"Evolução T{temporada_atual_num_t8} vs T{temporada_anterior_num_t8}"
        df_tabela_exibicao.rename(columns={'Evolução %': nome_coluna_evolucao_item8}, inplace=True)
        
        def format_evolucao_texto(val):
            if val > 0.0001:
                return f"{val:.1%} ↑"
            elif val < -0.0001:
                return f"{val:.1%} ↓"
            else:
                return "0.0% ≈"
                
        df_tabela_exibicao[nome_coluna_evolucao_item8 + ' Texto'] = df_tabela_exibicao[nome_coluna_evolucao_item8].apply(format_evolucao_texto)

        # 6. Preparar a tabela para exibição final (Selecionar Colunas)
        
        # Colunas internas que existem em df_tabela_exibicao
        colunas_internas_existentes = [
            COLUNA_CHAVE_CONSOLIDADA, 
            'CNPJs Vinculados', 'CPFs Vinculados', 
            'Especificadores_Vinculados', # MUDANÇA DE NOME AQUI
            'Pontuacao_Total', nome_coluna_evolucao_item8 + ' Texto', 'Qtd_Pedidos', 'Categoria'
        ]
        
        df_tabela_exibicao = df_tabela_exibicao[colunas_internas_existentes].copy()

        # Renomear as colunas para o Português para exibição
        df_tabela_exibicao.columns = ['Chave de Consolidação', 'CNPJs Vinculados', 'CPFs Vinculados', 'Nomes Vinculados', 'Pontuação', 'Evolução T vs T-1', 'Qtd de Pedidos', 'Categoria'] 

        # Função de estilização para a coluna de Evolução
        def style_evolucao_individual(val):
            # Obtém o valor numérico (raw) da evolução
            raw_value = val.replace('↑', '').replace('↓', '').replace('%', '').replace('≈', '')
            raw_value = pd.to_numeric(raw_value.replace(',', '.'), errors='coerce') / 100 
            
            if not isinstance(raw_value, (int, float)): return ''
            if raw_value > 0.0001:
                return 'color: #a3ffb1; font-weight: bold' # Verde ajustado
            elif raw_value < -0.0001:
                return 'color: #ff9999; font-weight: bold' # Vermelho
            return 'color: #b3e6ff; font-weight: bold' # Estável/Zero
        
        # Formatar a coluna Pontuação 
        df_tabela_exibicao['Pontuação'] = df_tabela_exibicao['Pontuação'].apply(
             lambda x: formatar_milhar_br(x)
        )
        # Formatar a coluna Qtd de Pedidos
        df_tabela_exibicao['Qtd de Pedidos'] = df_tabela_exibicao['Qtd de Pedidos'].apply(
             lambda x: formatar_milhar_br(x)
        )
        
        # Exibição Final
        st.dataframe(
            df_tabela_exibicao.style
                .applymap(style_nome_categoria, subset=['Categoria']) 
                .applymap(style_evolucao_individual, subset=['Evolução T vs T-1'])
                .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}, 
                                subset=pd.IndexSlice[:, ['Pontuação', 'Qtd de Pedidos', 'Categoria', 'Evolução T vs T-1']]),
            use_container_width=True
        )
        
        # NOTA DE ESCLARECIMENTO
        st.markdown(f"""
        **Nota:** A coluna **Evolução T vs T-1** compara a pontuação consolidada da Entidade na temporada atual selecionada ({temporada_selecionada_t8}) com a pontuação que ela teve na temporada anterior ({temporada_anterior_nome}) **dentro do mesmo Segmento/Loja filtrado**.
        """)
        
        # 10. DESEMPENHO DE NOVOS CADASTROS (Antigo 9)
        if COLUNA_ESPECIFICADOR in df_filtrado.columns:
            
            st.markdown("---")


            st.subheader("9. Análise de Novos Cadastrados (Aquisição)")
            
            # Filtra apenas os novos cadastrados no período e filtros de Segmento/Loja
            df_novos_filtrados = df_filtrado[df_filtrado['Novo_Cadastrado'] == True]
            
            # --- 9A. KPIs de Pontuação de Novos Cadastrados ---
            colunas_temporada_str = [col for col in df_filtrado.columns if col.startswith('Temporada ')]
            colunas_temporada_str = sorted([col for col in colunas_temporada_str if col != 'Temporada_Exibicao'])
            
            num_temporadas_kpi = max(1, len(colunas_temporada_str))
            cols_kpi_pontos = st.columns(num_temporadas_kpi)
            cols_kpi_contagem = st.columns(num_temporadas_kpi)
            
            pontos_por_temporada = {}
            contagem_por_temporada = {}
            
            
            # 1. Loop para calcular e exibir Pontos por Temporada 
            for i, t_col in enumerate(colunas_temporada_str):
                pontos = df_novos_filtrados.loc[df_novos_filtrados['Temporada_Exibicao'] == t_col, 'Pontos'].sum()
                contagem_clientes = df_novos_filtrados.loc[df_novos_filtrados['Temporada_Exibicao'] == t_col, 'CNPJ_CPF_LIMPO'].nunique()
                
                pontos_por_temporada[t_col] = pontos
                contagem_por_temporada[t_col] = contagem_clientes
                
                # KPI de Pontos
                with cols_kpi_pontos[i]:
                    st.metric(f"Pontos Novos {t_col.replace('Temporada ', 'T')}", 
                              formatar_milhar_br(pontos))

            # 2. Loop para exibir Contagem por Temporada 
            for i, t_col in enumerate(colunas_temporada_str):
                with cols_kpi_contagem[i]:
                    st.metric(f"Clientes Novos {t_col.replace('Temporada ', 'T')}", 
                              formatar_milhar_br(contagem_por_temporada[t_col]))
                    
            
            
            
            # --- 9 B. TABELA PIVÔ: Clientes Novos por Mês e Temporada + EVOLUÇÃO (QUALITATIVA) ---
            st.markdown("##### 9 A. Contagem de Novos Profissionais Pontuados por Mês e Temporada")

            if 'Mês_Exibicao' in df_novos_filtrados.columns:
                
                # 1. Agrupamento e Cálculo do Pivô - USA FUNÇÃO IMPORTADA
                df_pivot_novos, colunas_display_final_cli, nome_coluna_evolucao_cli = calcular_pivo_novos_clientes(
                    df_dados_original, df_novos_filtrados, meses_selecionados_exib, temporadas_selecionadas_exib
                )

                colunas_clientes_renomeadas = [col for col in df_pivot_novos.columns if col.startswith('Clientes T')]
                
                
                # Função de Estilização (Item 10B)
                def style_evolucao_qualitativa_clientes(series):
                    if 'Evolução Qualitativa Valor' not in df_pivot_novos.columns:
                        return [''] * len(series)

                    raw_values = df_pivot_novos['Evolução Qualitativa Valor']
                    
                    cor_pos = 'color: #a3ffb1; font-weight: bold' # Verde ajustado
                    cor_neg = 'color: #ff9999; font-weight: bold' 
                    cor_est = 'color: #b3e6ff; font-weight: bold' 

                    styles = []
                    for index, val in raw_values.items():
                        if index == 'Total':
                            style = 'font-weight: bold; background-color: #333333; '
                            if val == 1:
                                styles.append(style + 'color: #a3ffb1') 
                            elif val == -1:
                                styles.append(style + 'color: #ff9999') 
                            else:
                                styles.append(style + 'color: #b3e6ff') 
                        elif val == 1:
                            styles.append(cor_pos)
                        elif val == -1:
                            styles.append(cor_neg)
                        else:
                            styles.append(cor_est)
                    
                    return styles
                
                # Estilização e Exibição
                if not df_pivot_novos.empty: # Adiciona um último check antes de renderizar
                    st.dataframe(
                        df_pivot_novos[colunas_display_final_cli].style.format({col: formatar_milhar_br for col in colunas_clientes_renomeadas + ['Total']})
                                                                .apply(style_evolucao_qualitativa_clientes, subset=[nome_coluna_evolucao_cli] if len(temporadas_selecionadas_exib) >= 2 else [], axis=0) 
                                                                .set_properties(**{'border': '1px solid #333333'}),
                        use_container_width=True
                    )
                else:
                    st.info("Nenhum cliente novo encontrado com os filtros de data selecionados para exibir o pivô.")

                # Remove a coluna de valores brutos se existir
                if 'Evolução Qualitativa Valor' in df_pivot_novos.columns:
                    df_pivot_novos = df_pivot_novos.drop(columns=['Evolução Qualitativa Valor'])

                
                if len(temporadas_selecionadas_exib) >= 2:
                    st.markdown(f"**Nota:** A coluna de Evolução Qualitativa de Clientes compara a contagem de novos profissionais mês a mês entre a **{nome_coluna_evolucao_cli.split(' ')[2].replace('vs', 'T')}** (Atual) e a **{nome_coluna_evolucao_cli.split(' ')[-1].replace(')', 'T')}** (Anterior) seleccionadas.")

                
                # --- 9 C. Tabela de Nomes (Detalhe dos Clientes Novos) ---
                st.markdown("##### 9 B. Nomes dos Profissionais Novos (Com Compra na Temporada)")

                # Agrupa os novos clientes e mostra a primeira compra histórica para detalhe
                if not df_novos_filtrados.empty:
                    df_nomes_novos = df_novos_filtrados.groupby(
                        [COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO']
                    ).agg(
                        Primeira_Compra_Historica=('Data_Primeira_Compra_Historica', 'min'),
                        Temporada_Cadastro=(COLUNA_NUMERO_TEMPORADA, 'first'),
                        Pontos=('Pontos', 'sum')
                    ).reset_index()
                    
                    # Renomeia e formata
                    df_nomes_novos.columns = ['Nome', 'CPF/CNPJ', 'Primeira Compra', 'Temporada', 'Pontos']
                    df_nomes_novos['Temporada'] = 'T' + df_nomes_novos['Temporada'].astype(str)
                    df_nomes_novos['Pontos'] = df_nomes_novos['Pontos'].apply(lambda x: formatar_milhar_br(x))
                    df_nomes_novos['Primeira Compra'] = df_nomes_novos['Primeira Compra'].dt.strftime('%d/%m/%Y')
                    
                    st.dataframe(df_nomes_novos.style.set_properties(**{'border': '1px solid #333333'}), 
                                                     use_container_width=True)
                else:
                    st.info("Nenhum novo profissional encontrado para detalhe com os filtros aplicados.")
                        
            # =======================================================================
            # ITEM 10. ANÁLISE DE CLIENTES ATIVOS E INATIVOS (Retenção)
            # =======================================================================
            if not df_dados_original.empty:
                
                st.markdown("---")

                # 1. Tabela de Resumo Anual (Item 10A) - ATENDE FILTROS DE Segmento/Loja
                st.subheader("10. Análise de Clientes Ativos vs Inativos (Retenção)")
                
                # CRÍTICO: Recalcula a retenção APENAS para a Entidade/Segmento selecionado - USA FUNÇÃO IMPORTADA
                df_anual_metricas, clientes_historicos_na_entidade = calcular_clientes_ativos_inativos(
                    df_dados_original, 
                    lojas_selecionadas, 
                    segmentos_selecionados
                )
                
                # CRÍTICO: Título alterado para refletir 'Temporada'
                st.markdown("##### 10 A. Resumo por Temporada de Clientes Ativos e Inativos (Entidade Filtrada)")
                
                # Função de Estilização para a coluna % Ativo (Item 10A)
                def style_percentual_ativo(val):
                    if not isinstance(val, (float, int)): return ''
                    if val >= 0.5: # 50% ou mais de Ativos
                        return 'color: #a3ffb1; font-weight: bold; background-color: #00800020' # Verde ajustado
                    elif val > 0:
                        return 'color: #ffe08a; font-weight: bold; background-color: #ffd70020'
                    else:
                        return 'color: #ff9999; font-weight: bold; background-color: #ff000020'
                        
                # Aplicando a interatividade e estilização na tabela A
                colunas_config = {
                    'Temporada': st.column_config.Column("Temporada", width="small"),
                    'Contagem de Clientes Pontuando (Ativos)': st.column_config.Column(
                        "Clientes Pontuando (Ativos)", 
                        help="Total de clientes que pontuaram na temporada na Entidade. Clique na linha para filtrar."
                    ),
                    'Contagem de Clientes Não Pontuando (Inativos)': st.column_config.Column(
                        "Clientes Não Pontuando (Inativos)", 
                        help="Total de clientes que pontuaram historicamente na Entidade, mas não nesta temporada. Clique na linha para filtrar."
                    ),
                    'Total de Clientes': st.column_config.Column(
                        "Total de Clientes",
                        help="Soma de Clientes Ativos + Inativos (Clientes que já pontuaram na Entidade)"
                    ),
                    # CORREÇÃO: Removido o argumento 'format'
                    '% Ativo': st.column_config.Column(
                        "% Ativo",
                        help="Porcentagem de Clientes Ativos sobre o Total de Clientes (Ativos + Inativos)",
                    ),
                }

                # Colunas a exibir 
                colunas_display_10A = [
                    'Temporada', 
                    'Contagem de Clientes Pontuando (Ativos)', 
                    'Contagem de Clientes Não Pontuando (Inativos)', 
                    'Total de Clientes',
                    '% Ativo'
                ]
                
                # Exibe o dataframe com a funcionalidade de seleção de linha (para substituir o on_click)
                evento = st.dataframe(
                    df_anual_metricas[colunas_display_10A].style
                        .applymap(style_percentual_ativo, subset=['% Ativo'])
                        .format({
                            # USA FUNÇÃO IMPORTADA formatar_milhar_br
                            'Contagem de Clientes Pontuando (Ativos)': formatar_milhar_br,
                            'Contagem de Clientes Não Pontuando (Inativos)': formatar_milhar_br,
                            'Total de Clientes': formatar_milhar_br,
                            '% Ativo': '{:.1%}' # Formatando como porcentagem (mantido no .style.format)
                        }).set_properties(**{'border': '1px solid #333333'}),
                    column_config=colunas_config,
                    use_container_width=True,
                    selection_mode="single-row", # Habilita a seleção de uma única linha
                    on_select="rerun" # Adicionado para garantir o callback e capturar a seleção
                )
                
                # Lógica de processamento do clique (seleção de linha)
                if evento.selection['rows']:
                    selected_index = evento.selection['rows'][0]
                    selected_row = df_anual_metricas.iloc[selected_index]
                    
                    col_click_ativo, col_click_inativo = st.columns(2)
                    
                    status_selecionado = None
                    
                    # Opções de filtragem
                    with col_click_ativo:
                        if st.button(f"🔎 Ver {formatar_milhar_br(selected_row['Contagem de Clientes Pontuando (Ativos)'])} ATIVOS em {selected_row['Temporada']}"):
                            status_selecionado = 'ativo'
                    
                    with col_click_inativo:
                        if st.button(f"🔎 Ver {formatar_milhar_br(selected_row['Contagem de Clientes Não Pontuando (Inativos)'])} INATIVOS em {selected_row['Temporada']}"):
                            status_selecionado = 'inativo'

                    if status_selecionado:
                        st.session_state['filtro_status_ano'] = {
                            'ano': selected_row['Temporada'], 
                            'status': status_selecionado, 
                            'termo_pesquisa': status_selecionado.upper()
                        }
                        st.rerun()

                
                
                # 2. Tabela de Detalhe por Cliente (Item 10B) - RESPEITANDO OS FILTROS LATERAIS
                st.markdown("##### 10 B. Detalhe de Clientes Ativos/Inativos no Período e Entidade Selecionados")
                
                # 1. Identificar clientes que pontuaram no período FILTRADO
                clientes_ativos_no_periodo_filtrado = set(df_filtrado['CNPJ_CPF_LIMPO'].unique())
                
                # 2. Clientes Inativos: Estão no histórico da ENTIDADE, mas NÃO pontuaram no PERÍODO FILTRADO
                clientes_inativos_no_periodo = clientes_historicos_na_entidade.difference(clientes_ativos_no_periodo_filtrado)

                # 3. DataFrame de ATIVOS 
                df_ativos = df_filtrado.groupby([COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO']).agg(
                    Qtd_Pedidos_Periodo=(COLUNA_PEDIDO, 'nunique'), 
                    Ultima_Data_Compra=('Data da Venda', 'max') 
                ).reset_index()
                df_ativos['Status'] = 'ATIVO'

                # 4. DataFrame de INATIVOS 
                df_historico_relevante = df_dados_original[
                    (df_dados_original['Loja'].isin(lojas_selecionadas)) &
                    (df_dados_original['Segmento'].isin(segmentos_selecionados))
                ].copy()
                
                df_inativos_base = df_historico_relevante[df_historico_relevante['CNPJ_CPF_LIMPO'].isin(clientes_inativos_no_periodo)].copy()
                
                # Agrupamos o histórico relevante para pegar a última data de compra e nome para os inativos
                df_inativos = df_inativos_base.groupby([COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO']).agg(
                    Ultima_Data_Compra=('Data da Venda', 'max') 
                ).reset_index()
                
                df_inativos['Qtd_Pedidos_Periodo'] = 0
                df_inativos['Status'] = 'INATIVO'

                # Unifica Ativos e Inativos
                df_detalhe = pd.concat([
                    df_ativos.rename(columns={'CNPJ_CPF_LIMPO': 'CPF/CNPJ_LIMPO', COLUNA_ESPECIFICADOR: 'Nome'}),
                    df_inativos.rename(columns={'CNPJ_CPF_LIMPO': 'CPF/CNPJ_LIMPO', COLUNA_ESPECIFICADOR: 'Nome'})
                ], ignore_index=True)

                # Junta o CPF/CNPJ original para exibição
                df_cnpj_original_map = df_dados_original.groupby('CNPJ_CPF_LIMPO').agg({
                    COLUNA_CNPJ_CPF: 'first' 
                }).reset_index().rename(columns={'CNPJ_CPF_LIMPO': 'CPF/CNPJ_LIMPO', COLUNA_CNPJ_CPF: 'CPF/CNPJ Original'})
                
                df_detalhe = pd.merge(df_detalhe, df_cnpj_original_map, on='CPF/CNPJ_LIMPO', how='left')
                
                # Limpa colunas
                df_detalhe.drop(columns=['CPF/CNPJ_LIMPO'], inplace=True)
                df_detalhe.rename(columns={'CPF/CNPJ Original': 'CPF/CNPJ'}, inplace=True)
                
                # Ordena pelo status e depois pela quantidade de pedidos
                df_detalhe.sort_values(by=['Status', 'Qtd_Pedidos_Periodo'], ascending=[False, False], inplace=True)

                # --- CAMPO DE PESQUISA (Nome, CPF/CNPJ ou ATIVO/INATIVO) + INTERATIVIDADE DE CLIQUE ---
                
                # Obtém o termo de pesquisa inicial do estado, se houver
                initial_search_value = st.session_state['filtro_status_ano']['termo_pesquisa']
                
                # Apenas limpa o termo de pesquisa no estado após ser usado no `st.text_input`
                st.session_state['filtro_status_ano']['termo_pesquisa'] = ''
                    
                termo_pesquisa_atv = st.text_input(
                    "Pesquisar Detalhe (Nome, CPF/CNPJ ou Status):",
                    key='search_profissional_atv',
                    value=initial_search_value, # Define o valor inicial com base no clique
                    placeholder="Digite nome, CPF/CNPJ ou ATIVO/INATIVO"
                )
                
                df_tabela_detalhe_exibicao = df_detalhe.copy()

                if termo_pesquisa_atv:
                    termo_pesquisa_atv_lower = termo_pesquisa_atv.lower()
                    
                    # Filtra o DataFrame usando 3 colunas
                    df_tabela_detalhe_exibicao = df_tabela_detalhe_exibicao[
                        df_tabela_detalhe_exibicao['Nome'].astype(str).str.lower().str.contains(termo_pesquisa_atv_lower, na=False) |
                        df_tabela_detalhe_exibicao['CPF/CNPJ'].astype(str).str.lower().str.contains(termo_pesquisa_atv_lower, na=False) |
                        df_tabela_detalhe_exibicao['Status'].astype(str).str.lower().str.contains(termo_pesquisa_atv_lower, na=False)
                    ].copy()
                    
                    if df_tabela_detalhe_exibicao.empty:
                        st.info(f"Nenhum profissional encontrado para o termo: **{termo_pesquisa_atv}**.")
                        
                # Formatação final da tabela de detalhe
                df_tabela_detalhe_exibicao['Qtd de Pedidos no Período'] = df_tabela_detalhe_exibicao['Qtd_Pedidos_Periodo'].apply(formatar_milhar_br)
                
                # Formatação da Data (DD/MM/AAAA)
                df_tabela_detalhe_exibicao['Última Data da Compra'] = df_tabela_detalhe_exibicao['Ultima_Data_Compra'].apply(
                    lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else 'N/A'
                )
                
                df_tabela_detalhe_exibicao.drop(columns=['Qtd_Pedidos_Periodo', 'Ultima_Data_Compra'], inplace=True)
                
                # Renomear colunas para exibição
                df_tabela_detalhe_exibicao.columns = ['Nome do Profissional', 'Status', 'CPF/CNPJ', 'Qtd de Pedidos no Período', 'Última Data da Compra']
                df_tabela_detalhe_exibicao = df_tabela_detalhe_exibicao[['Nome do Profissional', 'CPF/CNPJ', 'Status', 'Qtd de Pedidos no Período', 'Última Data da Compra']] # Reordenar

                # Função de estilização para Status
                def style_status_row(row):
                    if row['Status'] == 'ATIVO':
                        return ['color: #a3ffb1; font-weight: bold; background-color: #00800020'] * len(row) # Verde ajustado
                    elif row['Status'] == 'INATIVO':
                        return ['color: #ff9999; font-weight: bold; background-color: #ff000020'] * len(row)
                    return [''] * len(row)

                st.dataframe(
                    df_tabela_detalhe_exibicao.style
                        .apply(lambda x: style_status_row(x), axis=1) # Aplica a cor em toda a linha com base no Status
                        .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}, 
                                        subset=pd.IndexSlice[:, ['Status', 'Qtd de Pedidos no Período', 'Última Data da Compra']]),
                    use_container_width=True
                )
                
                st.markdown("---")

    # =======================================================================
    # ITEM 11. ANÁLISE DE VARIAÇÃO DE RANKING POR PROFISSIONAL 
    # =======================================================================
    
    # 1. Identificar a Temporada Atual e a Anterior (ignorando os filtros de data do sidebar)
    todas_temporadas_nums = sorted(df_dados_original[COLUNA_NUMERO_TEMPORADA].loc[df_dados_original[COLUNA_NUMERO_TEMPORADA] > 0].unique())
    
    if len(todas_temporadas_nums) < 2:
        st.subheader("11. Análise de Variação de Ranking (T vs T-1)")
        st.info("⚠️ São necessárias pelo menos duas temporadas com dados para calcular a variação de ranking.")
    else:
        # A temporada atual é a mais recente disponível
        t_atual_num = todas_temporadas_nums[-1]
        t_anterior_num = todas_temporadas_nums[-2]
        
        # 2. Calcular o Ranking Ajustado (respeitando os filtros de Segmento/Loja) - USA FUNÇÃO IMPORTADA
        df_ranking_ajustado, t_atual_nome, t_anterior_nome, max_rank_t_atual, max_rank_t_anterior = calcular_ranking_ajustado(
            df_dados_original, 
            lojas_selecionadas, 
            segmentos_selecionados, 
            t_atual_num, 
            t_anterior_num
        )
        
        st.subheader(f"11. Análise de Variação de Ranking por Profissional ({t_atual_nome} vs {t_anterior_nome})")

        if df_ranking_ajustado.empty:
            st.info("Nenhum profissional pontuou nas temporadas selecionadas para o Segmento/Loja filtrado.")
        else:
            
            # 3. Estilização da tabela
            
            # Função para estilizar a Variação Rank
            def style_variacao_rank(val):
                if not isinstance(val, (int, float)): 
                    return ''
                if val < 0:
                    return 'color: #ff9999; font-weight: bold; background-color: #ff000020'
                elif val > 0:
                    return 'color: #a3ffb1; font-weight: bold; background-color: #00800020' # Verde ajustado
                else:
                    return 'color: #b3e6ff; font-weight: bold' 
            
            # Renomear colunas para o Português para exibição (necessário para o st.dataframe)
            col_t_anterior = f'Rank - T{t_anterior_num}'
            col_t_atual = f'Rank - T{t_atual_num}'
            
            df_display = df_ranking_ajustado.copy()
            
            st.dataframe(
                df_display.style
                    .applymap(style_variacao_rank, subset=['Variação Rank'])
                    .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'},
                                    subset=pd.IndexSlice[:, [col_t_anterior, col_t_atual, 'Variação Rank']]),
                use_container_width=True
            )
            
            st.markdown(f"""
            **Lógica da Variação Rank:** `{t_anterior_nome} Rank Ajustado - {t_atual_nome} Rank Ajustado`.
            - **Valor Negativo (Vermelho):** O profissional **Piorou** seu ranking (ex: de 1 para 5).
            - **Valor Positivo (Verde):** O profissional **Melhorou** seu ranking (ex: de 5 para 1).
            - **Valor Estável (Azul):** O profissional **Manteve** seu ranking (ex: de 1 para 1).
            - **Rank Ajustado (Gap Filling):** Posições **{max_rank_t_anterior + 1}** (para {t_anterior_nome}) ou **{max_rank_t_atual + 1}** (para {t_atual_nome}) são atribuídas a profissionais que pontuaram em uma temporada, mas não na outra, dentro dos filtros de Segmento/Loja.
            """)

# Mensagem se o DataFrame estiver vazio após o carregamento (não deve acontecer agora)
elif df_dados_original.empty and Relatorio == 'Relatorio.xlsx':
    st.warning("O DataFrame está vazio. Verifique se a planilha Excel tem dados.")
