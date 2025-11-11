# Módulo: analise_lojas.py
import pandas as pd
import numpy as np

# Importa as constantes e funções auxiliares
from modulos.tratamento import calcular_evolucao_pct

# ==============================================================================
# NOVA FUNÇÃO AUXILIAR PARA O ITEM 7: ANÁLISE DE EVOLUÇÃO DE LOJAS
# ==============================================================================
def calcular_analise_lojas(df_base, t_atual_nome, t_anterior_nome, lojas_base_analise):
    """
    Realiza a análise de evolução de lojas (Pontos, Evolução %, Terços e Pirâmide).
    
    Args:
        df_base (pd.DataFrame): DataFrame já filtrado por Segmento/Loja/Mês.
        t_atual_nome (str): Nome da temporada atual (ex: 'Temporada 10').
        t_anterior_nome (str): Nome da temporada anterior (ex: 'Temporada 09').
        lojas_base_analise (list): Lista de lojas que devem compor a base (seleção manual do usuário).

    Returns:
        tuple: (df_evolucao, df_rank_quantitativo, df_rank_pontuacao, df_piramide_status)
    """
    
    # CRÍTICO: Filtrar a base de dados *antes* do agrupamento para incluir APENAS
    # as lojas selecionadas pelo usuário, garantindo que o cálculo de pontos
    # para T_Atual e T_Anterior seja feito apenas para elas.
    df_base_filtrada_lojas = df_base[df_base['Loja'].isin(lojas_base_analise)].copy()
    
    # 1. Filtra as duas temporadas de interesse
    df_t_vs_t = df_base_filtrada_lojas[
        df_base_filtrada_lojas['Temporada_Exibicao'].isin([t_atual_nome, t_anterior_nome])
    ].copy()
    
    # 2. Agrupa por Loja e Temporada, somando os Pontos
    # Aqui, garantimos que todas as lojas selecionadas (mesmo com 0 pontos) sejam incluídas.
    # Primeiro, pegamos a lista completa de lojas do filtro manual:
    lojas_para_analisar = pd.DataFrame({'Loja': lojas_base_analise})
    
    df_pontos_loja = df_t_vs_t.groupby(['Loja', 'Temporada_Exibicao'])['Pontos'].sum().reset_index()
    
    # 3. Pivotar para ter Pontos T_Atual e T_Anterior
    df_evolucao = df_pontos_loja.pivot_table(
        index='Loja',
        columns='Temporada_Exibicao',
        values='Pontos',
        fill_value=0 # Preenche com 0 lojas que não pontuaram na temporada, mas que existem no df_t_vs_t
    ).reset_index()
    
    # CRÍTICO: Mesclar com a lista completa de lojas do multiselect para incluir lojas com 0 pontos em ambas as Ts
    # que estão na seleção do usuário.
    df_evolucao_final = pd.merge(
        lojas_para_analisar,
        df_evolucao,
        on='Loja',
        how='left'
    ).fillna(0) # Zera os pontos para as lojas que não apareceram no df_evolucao (pontuaram 0 em ambas as T's)
    
    
    col_atual = t_atual_nome
    col_anterior = t_anterior_nome

    # --- PARTE 1: Evolução % e Classificação ---
    
    # Calcula a Evolução % (usando a função importada)
    df_evolucao_final['Evolução %'] = df_evolucao_final.apply(
        lambda row: calcular_evolucao_pct(row[col_atual], row[col_anterior]), axis=1
    )
    
    # Classifica a loja por status (Pirâmide de Evolução - Parte 3)
    def classificar_status(row):
        pontos_atual = row[col_atual]
        pontos_anterior = row[col_anterior]
        
        if pontos_anterior == 0 and pontos_atual == 0:
            return 'Zero em T-1 e T-Atual' 
        if pontos_anterior == 0 and pontos_atual > 0:
            return 'Cresceram (Zeraram na T-1)' 
        if pontos_anterior > 0 and pontos_atual == 0:
            return 'Zeraram na T-Atual' 
        if pontos_anterior > 0 and pontos_atual > 0:
            if pontos_atual > pontos_anterior:
                return 'Cresceram' 
            elif pontos_atual < pontos_anterior:
                return 'Decresceram' 
            else:
                return 'Estáveis'
        
        return 'Outros'

    df_evolucao_final['Status_Evolução'] = df_evolucao_final.apply(classificar_status, axis=1)
    
    # Ponto 1: Ordenação decrescente de pontos (AGORA USANDO T_ANTERIOR COMO PRINCIPAL)
    # Importante: A loja "Dunelli" (e outras) que tem zero pontos ficará no final.
    df_evolucao_final.sort_values(
        by=[col_anterior, col_atual], 
        ascending=[False, False], 
        inplace=True
    ) 
    
    # --- PARTE 2: Separação por Terços (Quantitativo de Lojas Iguais) ---
    
    # Número total de lojas ativas na base de análise (lojas_base_analise)
    total_lojas_base = len(df_evolucao_final['Loja'].unique())
    
    # Define os cortes dos terços de forma quantitativa e igualitária
    terco_size = total_lojas_base // 3
    restante = total_lojas_base % 3

    # Define os limites de corte de índice
    corte_1 = terco_size + (1 if restante > 0 else 0)
    corte_2 = corte_1 + terco_size + (1 if restante > 1 else 0)
    
    # Garantimos um índice limpo para os cortes
    df_tercos = df_evolucao_final.copy().reset_index(drop=True)
    
    # Atribuição de terço por índice (corte de quantidade)
    df_tercos['Terço'] = '3° Terço'
    df_tercos.loc[:corte_1 - 1, 'Terço'] = '1° Terço'
    df_tercos.loc[corte_1:corte_2 - 1, 'Terço'] = '2° Terço'
    
    # 2.3 Montar o DataFrame de Ranking Quantitativo (Lojas por Terço)
    df_rank_quantitativo_base = df_tercos.groupby('Terço').agg(
        **{
            col_anterior: (col_anterior, lambda x: (x > 0).sum()), # Conta lojas que pontuaram na T-1
            col_atual: (col_atual, lambda x: (x > 0).sum()), # Conta lojas que pontuaram na T-Atual
            'Lojas_Total': ('Loja', 'nunique') # Contagem total de lojas no terço (deve ser igual em todas as temporadas)
        }
    ).reset_index()
    
    # Ponto 2: Garante que a contagem de lojas totais seja sempre a mesma para T_Anterior e T_Atual
    # Substituímos a contagem de 'Pontuadas' pela contagem de 'Lojas_Total' na coluna de cada temporada
    df_rank_quantitativo = pd.DataFrame({
        'Terço': df_rank_quantitativo_base['Terço'],
        col_anterior: df_rank_quantitativo_base['Lojas_Total'], # Contagem de lojas por terço (igual T_Atual e T_Anterior)
        col_atual: df_rank_quantitativo_base['Lojas_Total'] # Contagem de lojas por terço (igual T_Atual e T_Anterior)
    }).sort_values(by='Terço', ascending=True)

    # --- CORREÇÃO: ADICIONA A COLUNA DE TOTAL DE LOJAS PARA EXIBIÇÃO NO APP.PY ---
    df_rank_quantitativo['Total de Lojas'] = df_rank_quantitativo['Terço'].apply(
        lambda x: df_rank_quantitativo_base.loc[df_rank_quantitativo_base['Terço'] == x, 'Lojas_Total'].iloc[0]
    )
    # --- FIM CORREÇÃO ---

    
    # 2.4 Montar o DataFrame de Ranking da Pontuação (Pontuação Total dentro daquele corte de lojas)
    df_rank_pontuacao_base = df_tercos.groupby('Terço').agg(
        **{
            col_anterior: (col_anterior, 'sum'), 
            col_atual: (col_atual, 'sum')
        }
    ).reset_index()
    
    pontuacao_terco = []
    for _, row in df_rank_pontuacao_base.iterrows():
        pontos_ant = row[col_anterior]
        pontos_atual = row[col_atual]
        
        evol = calcular_evolucao_pct(pontos_atual, pontos_ant)
        
        pontuacao_terco.append({
            'Terço': row['Terço'],
            col_anterior: pontos_ant,
            col_atual: pontos_atual,
            'Evolução %': evol
        })

    df_rank_pontuacao = pd.DataFrame(pontuacao_terco)
    df_rank_pontuacao.sort_values(by='Terço', ascending=True, inplace=True)
    
    # --- PARTE 3: Pirâmide de Status (Contagem) ---
    
    df_piramide_sumario = pd.DataFrame({
        'Status': [
            f'Cresceram (Evolução Positiva)', 
            f'Decresceram (Evolução Negativa)', 
            f'Zeraram na {t_anterior_nome.replace("Temporada ", "T")} e Pontuaram na {t_atual_nome.replace("Temporada ", "T")}',
            f'Zeraram na {t_atual_nome.replace("Temporada ", "T")}'
        ],
        'Contagem': [
            df_evolucao_final[df_evolucao_final['Evolução %'] > 0.0001].shape[0],
            df_evolucao_final[df_evolucao_final['Evolução %'] < -0.0001].shape[0],
            df_evolucao_final[(df_evolucao_final[col_anterior] == 0) & (df_evolucao_final[col_atual] > 0)].shape[0],
            df_evolucao_final[(df_evolucao_final[col_anterior] > 0) & (df_evolucao_final[col_atual] == 0)].shape[0],
        ]
    })
    
    df_piramide_sumario = df_piramide_sumario[df_piramide_sumario['Contagem'] > 0]


    return df_evolucao_final, df_rank_quantitativo, df_rank_pontuacao, df_piramide_sumario