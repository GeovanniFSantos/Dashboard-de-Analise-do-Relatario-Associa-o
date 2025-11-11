# Módulo: categoria.py
import pandas as pd
import numpy as np

# Importa as constantes
from modulos.config import COLUNA_NUMERO_TEMPORADA, COLUNA_ESPECIFICADOR, CATEGORIAS_NOMES

# ==============================================================================
# FUNÇÕES DE CÁLCULO DE CATEGORIAS E EVOLUÇÃO
# ==============================================================================

# A função calcular_categorias recebe df_base e df_agrupado. O df_base não é usado
# internamente para a lógica de categorias, mas é mantido por compatibilidade.
def calcular_categorias(df_base, df_agrupado):
    """
    Classifica profissionais em categorias com base na Pontuacao_Total.
    """
    
    if df_agrupado.empty:
        # Define as colunas esperadas
        return pd.DataFrame(columns=['Categoria', COLUNA_ESPECIFICADOR, 'Pontuacao_Total'])
        
    # Recria as condições com base nas pontuações do DF de agrupamento
    condicoes_agrupadas = [
        (df_agrupado['Pontuacao_Total'] >= 5000000), # Diamante
        (df_agrupado['Pontuacao_Total'] >= 2000000), # Esmeralda
        (df_agrupado['Pontuacao_Total'] >= 500000), # Ruby
        (df_agrupado['Pontuacao_Total'] >= 150000), # Topázio
        (df_agrupado['Pontuacao_Total'] >= 1) # Pro
    ]
        
    categorias_np_select = ['Diamante', 'Esmeralda', 'Ruby', 'Topázio', 'Pro']

    df_agrupado['Categoria'] = np.select(condicoes_agrupadas, categorias_np_select, default='Sem Categoria')
    return df_agrupado

# Função para obter a pontuação da temporada anterior (corrigida)
def get_pontuacao_temporada_anterior(df_original_completo, temporada_atual_num, lojas_selecionadas, segmentos_selecionados, categoria=None):
    """Obtém a pontuação total ou por categoria da temporada anterior com base nos filtros atuais."""
    temporada_anterior_num = int(temporada_atual_num) - 1
    temporada_anterior_nome = f"Temporada {temporada_anterior_num}"
    
    if temporada_anterior_num <= 0:
        return 0
        
    # 1. Filtra o DF original apenas para a temporada anterior
    df_anterior_base = df_original_completo[df_original_completo['Temporada_Exibicao'] == temporada_anterior_nome].copy()
    
    if df_anterior_base.empty:
        return 0
        
    # 2. APLICA O FILTRO DE LOJA/SEGMENTO DA TEMPORADA ATUAL
    df_anterior_filtrado = df_anterior_base[
        (df_anterior_base['Loja'].isin(lojas_selecionadas)) &
        (df_anterior_base['Segmento'].isin(segmentos_selecionados))
    ].copy()
    
    if df_anterior_filtrado.empty:
        return 0

    # 3. Calcula as categorias no DF anterior (para agrupar por categoria)
    df_anterior_agrupado = df_anterior_filtrado.groupby(COLUNA_ESPECIFICADOR)['Pontos'].sum().reset_index()
    df_anterior_agrupado.columns = [COLUNA_ESPECIFICADOR, 'Pontuacao_Total']
    
    # Chama a função local calcular_categorias
    df_desempenho_anterior = calcular_categorias(df_anterior_filtrado, df_anterior_agrupado)
    
    if categoria is None:
            # Retorna a pontuação total da temporada anterior (sem filtro de categoria)
            return df_desempenho_anterior['Pontuacao_Total'].sum()

    # Retorna a pontuação total da categoria específica na temporada anterior
    pontuacao = df_desempenho_anterior.loc[df_desempenho_anterior['Categoria'] == categoria, 'Pontuacao_Total'].sum()
    return pontuacao

# Função para obter a contagem de profissionais por categoria
def get_contagem_categoria(df_desempenho, categorias_base=CATEGORIAS_NOMES):
    """
    Calcula a contagem de profissionais por categoria.
    """
    # Inclui 'Sem Categoria' na lista para garantir que todas sejam consideradas na contagem
    todas_categorias = categorias_base + ['Sem Categoria']
    if df_desempenho.empty:
        return {cat: 0 for cat in todas_categorias}
    
    contagem = df_desempenho.groupby('Categoria')[COLUNA_ESPECIFICADOR].nunique().to_dict()
    # Preenche com 0s categorias ausentes
    for cat in todas_categorias:
        if cat not in contagem:
            contagem[cat] = 0
    return contagem