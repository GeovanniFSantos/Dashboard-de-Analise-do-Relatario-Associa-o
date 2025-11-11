# Módulo: tratamento.py
import pandas as pd # Necessário para o style_total_pontuacao (row.iloc[0])
import numpy as np  # Necessário para calcular_evolucao_pct

# ==============================================================================
# FUNÇÃO AUXILIAR PARA FORMATAÇÃO (MOVIDA DO ESCOPO GLOBAL)
# ==============================================================================
def formatar_milhar_br(valor):
    """Formata um número para o padrão brasileiro (separador de milhar ponto, sem casas decimais)."""
    if isinstance(valor, (int, float)):
        # Formatação para o Brasil (separador de milhar ponto, decimal vírgula)
        # Usa replace temporário para trocar vírgula por ponto no separador de milhar
        return f"{valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(valor)

# ==============================================================================
# FUNÇÕES DE ESTILIZAÇÃO GENÉRICA (CORRIGIDAS PARA USAR index.name)
# ==============================================================================
def style_total_pontuacao(row):
    """Estilo para aplicar cor de fundo escuro e texto branco na linha 'Total'."""
    # Estilo da linha Total, verificando o nome do índice (ou o valor da primeira coluna se não for indexado)
    if row.name == 'Total' or (isinstance(row.iloc[0], str) and row.iloc[0] == 'Total'):
        return ['font-weight: bold; background-color: #333333; color: white'] * len(row)
    return [''] * len(row)

# Função para calcular a evolução em % (usada em vários itens)
def calcular_evolucao_pct(atual, anterior):
    if anterior > 0:
        return (atual / anterior) - 1
    elif atual > 0:
        return 1.0 # Crescimento de zero para um valor positivo (+100%)
    return 0.0 # Zero ou zero para zero

# Funções de estilização para o Item 2 (Categorias)
def style_nome_categoria(val):
    cores = {
        'Diamante': 'color: #b3e6ff; font-weight: bold',  
        'Esmeralda': 'color: #a3ffb1; font-weight: bold', # Verde ajustado
        'Ruby': 'color: #ff9999; font-weight: bold', 
        'Topázio': 'color: #ffe08a; font-weight: bold', 
        'Pro': 'color: #d1d1d1; font-weight: bold', 
        'Total': 'color: #ffffff; font-weight: bold; background-color: #333333', 
    }
    return cores.get(val, '')