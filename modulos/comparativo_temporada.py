# Módulo: comparativo_temporada.py
import pandas as pd
import numpy as np

# Importa constantes e funções auxiliares
from modulos.config import COLUNA_PEDIDO, COLUNA_CNPJ_CPF
from modulos.tratamento import formatar_milhar_br # Importar a função de formatação

# Função auxiliar para calcular métricas temporais (adaptada para o novo Item 1)
def calcular_metricas_temporais(df_base, temporadas_selecionadas, coluna_base):
    """
    Calcula as métricas chave (Pedidos, Pontos, Pontuados, Novos Cadastrados)
    por temporada na base filtrada.
    """
    metricas = {
        'Qtd Pedidos': (COLUNA_PEDIDO, 'nunique'),
        'Pontuação': ('Pontos', 'sum'),
        'Qtd Pontuados': ('CNPJ_CPF_LIMPO', 'nunique'), # Total de pessoas únicas na temporada
        'Novos Cadastrados': (lambda x: x[x['Novo_Cadastrado'] == True]['CNPJ_CPF_LIMPO'].nunique(), 'custom')
    }
    
    # DataFrame para guardar os resultados, com as métricas como índice
    df_resultado = pd.DataFrame(index=metricas.keys())
    
    # Filtra apenas as temporadas que o cliente deseja ver na coluna
    # CRÍTICO: ORDENAÇÃO POR NÚMERO DA TEMPORADA (T7, T8, T9, T10)
    temporadas_ordenadas = sorted([t for t in temporadas_selecionadas if t in df_base['Temporada_Exibicao'].unique()],
                                    key=lambda x: int(x.split(' ')[1]))

    for t_nome in temporadas_ordenadas:
        df_temp = df_base[df_base['Temporada_Exibicao'] == t_nome].copy()
        coluna_t = t_nome.replace("Temporada ", "T")
        
        # Cria uma série de resultados para a temporada atual
        resultados_t = {}
        for nome_metrica, (col_ou_func, tipo) in metricas.items():
            if tipo == 'custom':
                # Aplica a função personalizada para Novos Cadastrados
                valor = col_ou_func(df_temp)
            elif col_ou_func in df_temp.columns:
                # Aplica o aggfunc padrão (sum, nunique)
                agg_func = col_ou_func
                if tipo == 'nunique':
                    valor = df_temp[agg_func].nunique()
                elif tipo == 'sum':
                    valor = df_temp[agg_func].sum()
                else:
                    valor = 0
            else:
                valor = 0
                
            resultados_t[nome_metrica] = valor
            
        # Adiciona a coluna de resultados ao DataFrame final
        df_resultado[coluna_t] = pd.Series(resultados_t)

    # Formatação do índice e valores
    df_resultado.index.name = 'Desempenho'
    
    # Aplicamos a formatação em todas as colunas de temporada
    # OBS: Usamos a função formatar_milhar_br importada de tratamento.py
    for col in df_resultado.columns:
        df_resultado[col] = df_resultado[col].apply(formatar_milhar_br)
        
    return df_resultado