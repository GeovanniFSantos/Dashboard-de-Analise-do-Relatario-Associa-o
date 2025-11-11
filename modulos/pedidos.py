# Módulo: pedidos.py
import pandas as pd
import plotly.express as px

# Importa as constantes e funções auxiliares
from modulos.config import COLUNA_PEDIDO, MES_ORDEM_FISCAL
from modulos.tratamento import formatar_milhar_br

# Função para calcular o Pivô de Pedidos por Mês e Temporada (Item 6B)
def calcular_pivo_pedidos(df_filtrado, temporadas_selecionadas_exib):
    """Calcula o pivô de Pedidos Únicos por Mês e Temporada."""
    
    df_pivot_pedidos = df_filtrado.pivot_table(
        index='Mês_Exibicao',
        columns='Temporada_Exibicao',
        values=COLUNA_PEDIDO,
        aggfunc='nunique', # Contagem de pedidos únicos
        fill_value=0
    ).reset_index()

    # Reordenação dos Meses (Julho a Junho) 
    df_pivot_pedidos['Ordem'] = df_pivot_pedidos['Mês_Exibicao'].map(MES_ORDEM_FISCAL)
    df_pivot_pedidos.sort_values(by='Ordem', inplace=True)
    df_pivot_pedidos.drop('Ordem', axis=1, inplace=True)
    
    # Filtrar as colunas de Temporada apenas para as selecionadas no filtro lateral
    colunas_temporada_pivot = [col for col in df_pivot_pedidos.columns if col.startswith('Temporada')]
    
    # Colunas a exibir: Mês_Exibicao + Temporadas Selecionadas (ordenadas)
    colunas_display_pedidos = ['Mês_Exibicao'] + sorted(
        [col for col in colunas_temporada_pivot if col in temporadas_selecionadas_exib],
        key=lambda x: int(x.split(' ')[1])
    )

    df_pivot_pedidos_display = df_pivot_pedidos[colunas_display_pedidos].copy()
    
    # Renomear colunas Temporada X para Tx (para ficar mais conciso)
    colunas_renomeadas = {col: col.replace('Temporada ', 'T') for col in colunas_display_pedidos if col.startswith('Temporada')}
    df_pivot_pedidos_display.rename(columns=colunas_renomeadas, inplace=True)
    
    colunas_temporada_tx = [col.replace('Temporada ', 'T') for col in colunas_display_pedidos if col.startswith('Temporada')]
    
    # 2. Adicionar linha de TOTAL
    df_pivot_pedidos_display.set_index('Mês_Exibicao', inplace=True)
    total_row_pedidos = pd.Series(df_pivot_pedidos_display[colunas_temporada_tx].sum(), name='Total')
    df_pivot_pedidos_display = pd.concat([df_pivot_pedidos_display, pd.DataFrame(total_row_pedidos).T])
    df_pivot_pedidos_display.index.name = 'Mês'

    return df_pivot_pedidos_display, colunas_temporada_tx
    
# Função para calcular o Pivô de Novos Clientes (Item 9A)
def calcular_pivo_novos_clientes(df_dados_original, df_novos_filtrados, meses_selecionados_exib, temporadas_selecionadas_exib):
    """Calcula o pivô de Novos Profissionais Pontuados por Mês e Temporada."""
    
    # 1. Agrupamento e Soma (Pivô da base completa para obter todas as colunas)
    df_pivot_base_novos_full = df_dados_original[df_dados_original['Novo_Cadastrado'] == True].pivot_table(
        index='Mês_Exibicao', 
        columns='Temporada_Exibicao', 
        values='Novo_Cadastrado', 
        aggfunc='sum',
        fill_value=0 
    ).reset_index()

    # 2. Filtra os Meses
    df_pivot_novos_filtrado = df_pivot_base_novos_full[df_pivot_base_novos_full['Mês_Exibicao'].isin(meses_selecionados_exib)].copy()
    
    # 3. Tratamento de Colunas e Ordenação 
    colunas_temporada_full_novos = [col for col in df_pivot_base_novos_full.columns if col.startswith('Temporada')]
    
    colunas_temporada_sorted_num_novos = sorted([
        col for col in colunas_temporada_full_novos if col != 'Temporada 0' and len(col.split(' ')) > 1
    ], key=lambda x: int(x.split(' ')[1]))
    
    # 4. Cálculo dos VALORES FILTRADOS (com base no df_novos_filtrados)
    df_valores_filtrados_novos = df_novos_filtrados.pivot_table(
        index='Mês_Exibicao',
        columns='Temporada_Exibicao',
        values='Novo_Cadastrado',
        aggfunc='sum',
        fill_value=0
    )
    
    # Inicializa o DF de novos clientes final
    df_pivot_novos = df_pivot_novos_filtrado[['Mês_Exibicao']].copy()
    
    for col in colunas_temporada_sorted_num_novos:
        df_pivot_novos[col] = 0
        
        if col in temporadas_selecionadas_exib:
            if col in df_valores_filtrados_novos.columns:
                 df_pivot_novos[col] = df_pivot_novos['Mês_Exibicao'].map(df_valores_filtrados_novos[col].to_dict()).fillna(0)

    
    # Reordenação dos Meses (Julho a Junho)
    df_pivot_novos['Ordem'] = df_pivot_novos['Mês_Exibicao'].map(MES_ORDEM_FISCAL)
    df_pivot_novos.sort_values(by='Ordem', inplace=True)
    df_pivot_novos.drop('Ordem', axis=1, inplace=True)
    
    # Renomear colunas de temporada para 'Clientes T9', 'Clientes T10', etc.
    colunas_clientes = [col for col in df_pivot_novos.columns if col.startswith('Temporada')]
    df_pivot_novos.columns = [
        'Mês_Exibicao' if col == 'Mês_Exibicao' else col.replace('Temporada ', 'Clientes T')
        for col in df_pivot_novos.columns
    ]
    
    # Ordenação das colunas de T7 -> T10
    colunas_clientes_renomeadas = [col for col in df_pivot_novos.columns if col.startswith('Clientes T')]
    colunas_clientes_sorted = sorted(colunas_clientes_renomeadas, key=lambda x: int(x.split('T')[1]))
    
    # 5. Cálculo da Evolução Qualitativa (Se houver 2 temporadas)
    nome_coluna_evolucao_cli = 'Evolução Clientes indisponível' 
    
    if len(temporadas_selecionadas_exib) >= 2 and not df_pivot_novos.empty:
        
        t_atual_col_cli_raw = sorted(temporadas_selecionadas_exib, key=lambda x: int(x.split(' ')[1]))[-1].replace('Temporada ', 'Clientes T')
        t_anterior_col_cli_raw = sorted(temporadas_selecionadas_exib, key=lambda x: int(x.split(' ')[1]))[-2].replace('Temporada ', 'Clientes T')
        
        def calcular_evolucao_contagem(row):
            valor_atual = row[t_atual_col_cli_raw]
            valor_anterior = row[t_anterior_col_cli_raw]
            
            if valor_atual > valor_anterior:
                return "Evolução Positiva", 1
            elif valor_atual < valor_anterior:
                return "Evolução Negativa", -1
            else:
                return "Evolução Estável", 0 
                
        
        df_pivot_novos['Evolução Qualitativa Texto'], df_pivot_novos['Evolução Qualitativa Valor'] = zip(*df_pivot_novos.apply(calcular_evolucao_contagem, axis=1))

        nome_coluna_evolucao_cli = f"Evolução Clientes ({t_atual_col_cli_raw.replace('Clientes T', 'T')} vs {t_anterior_col_cli_raw.replace('Clientes T', 'T')})"
        df_pivot_novos.rename(columns={'Evolução Qualitativa Texto': nome_coluna_evolucao_cli}, inplace=True)
        colunas_display_final_cli = colunas_clientes_sorted + [nome_coluna_evolucao_cli] 
    else:
        colunas_display_final_cli = colunas_clientes_sorted
        
    # Adicionar linha de TOTAL
    total_row = pd.Series(df_pivot_novos[colunas_clientes_renomeadas].sum(), name='Total')
    total_row['Mês_Exibicao'] = 'Total'
    df_pivot_novos.set_index('Mês_Exibicao', inplace=True)
    
    if not df_pivot_novos.empty or any(col in df_pivot_novos.columns for col in colunas_clientes_renomeadas):
        df_pivot_novos = pd.concat([df_pivot_novos, pd.DataFrame(total_row).T.set_index('Mês_Exibicao')])
        df_pivot_novos.index.name = 'Mês' 
    
    # CÁLCULO DA EVOLUÇÃO TOTAL QUALITATIVA (Se a coluna existir)
    if 'Evolução Qualitativa Valor' in df_pivot_novos.columns and 'Total' in df_pivot_novos.index:
        total_atual_cli = df_pivot_novos.loc[df_pivot_novos.index != 'Total', t_atual_col_cli_raw].sum() 
        total_anterior_cli = df_pivot_novos.loc[df_pivot_novos.index != 'Total', t_anterior_col_cli_raw].sum() 

        if total_atual_cli > total_anterior_cli:
            evolucao_texto_total_cli = "Evolução Positiva"
        elif total_atual_cli < total_anterior_cli:
            evolucao_texto_total_cli = "Evolução Negativa"
        else:
            evolucao_texto_total_cli = "Evolução Estável"

        df_pivot_novos.loc['Total', nome_coluna_evolucao_cli] = evolucao_texto_total_cli
        df_pivot_novos.loc['Total', 'Evolução Qualitativa Valor'] = 0 # Valor fictício para o estilo

    return df_pivot_novos, colunas_display_final_cli, nome_coluna_evolucao_cli