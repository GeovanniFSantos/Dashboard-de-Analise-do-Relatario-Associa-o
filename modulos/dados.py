# Módulo: dados.py

import pandas as pd
import streamlit as st
import numpy as np

# Importa as constantes globais
from modulos.config import (
    COLUNAS_NUMERICAS, 
    COLUNA_NUMERO_TEMPORADA, 
    COLUNA_PEDIDO, 
    COLUNA_CNPJ_CPF, 
    COLUNA_ESPECIFICADOR, 
    COLUNA_CPF_NOVO_CADASTRO
)

# Função para carregar os dados (usa cache do streamlit para ser mais rápido)
@st.cache_data
def carregar_e_tratar_dados(caminho_arquivo):
    """Lê o arquivo Excel (2 abas), trata colunas e retorna um DataFrame do Pandas."""
    try:
        # LER A ABA PRINCIPAL (Relatório)
        df = pd.read_excel(caminho_arquivo, sheet_name=0)

        # LER A ABA DE NOVOS CADASTRADOS (Assumindo a aba se chame "Novos Cadastrados")
        try:
            # Lê a aba de Novos Cadastrados do MESMO arquivo
            df_novos = pd.read_excel(caminho_arquivo, sheet_name='Novos Cadastrados')
        except ValueError:
            st.error(f"❌ Erro: A aba 'Novos Cadastrados' não foi encontrada no arquivo '{caminho_arquivo}'.")
            df_novos = pd.DataFrame()
        except FileNotFoundError:
            st.error(f"❌ Erro: O arquivo '{caminho_arquivo}' não foi encontrado.")
            df_novos = pd.DataFrame()

        # === ETAPA DE TRATAMENTO DE DADOS (DF PRINCIPAL) ===
        # 1. Tratamento de Colunas Numéricas (removendo R$ e Símbolos)
        for col in COLUNAS_NUMERICAS:
            if col in df.columns:
                # Remove espaços, vírgulas (usadas como separador de milhar) e R$
                # E converte para numérico
                df[col] = df[col].astype(str).str.replace(r'[^0-9,.]', '', regex=True)
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        # 2. Garantir que 'Data da Venda' seja datetime e filtrar dados inválidos
        if 'Data da Venda' in df.columns:
            df['Data da Venda'] = pd.to_datetime(df['Data da Venda'], errors='coerce')
            
            # Remove linhas com 'Data da Venda' nula ou inválida
            df.dropna(subset=['Data da Venda'], inplace=True) 
            
            # 3. CRIAÇÃO DAS COLUNAS DE MÊS E ANO PARA FILTRAGEM
            df['Ano'] = df['Data da Venda'].dt.year.astype(str)
            df['Mês_num'] = df['Data da Venda'].dt.month.astype(str)
            
            # 4. CRIAÇÃO DA COLUNA DE TEMPORADA DE EXIBIÇÃO
            if COLUNA_NUMERO_TEMPORADA in df.columns:
                # Garante que a coluna de temporada é numérica e a converte para 'Temporada X'
                df[COLUNA_NUMERO_TEMPORADA] = pd.to_numeric(df[COLUNA_NUMERO_TEMPORADA], errors='coerce').fillna(0).astype(int)
                df['Temporada_Exibicao'] = 'Temporada ' + df[COLUNA_NUMERO_TEMPORADA].astype(str)
            
            # 5. Mapeamento e Formatação para o Filtro de Mês 
            nomes_meses_map = {
                '1': 'Jan (01)', '2': 'Fev (02)', '3': 'Mar (03)', '4': 'Abr (04)',
                '5': 'Mai (05)', '6': 'Jun (06)', '7': 'Jul (07)', '8': 'Ago (08)',
                '9': 'Set (09)', '10': 'Out (10)', '11': 'Nov (11)', '12': 'Dez (12)'
            }
            # Aqui, mapeamos e garantimos que apenas os meses válidos sejam exibidos.
            df['Mês_Exibicao'] = df['Mês_num'].map(nomes_meses_map)
            
            # === 6. LÓGICA DE NOVO CADASTRADO (CRÍTICO) ===
            if COLUNA_CNPJ_CPF in df.columns and COLUNA_NUMERO_TEMPORADA in df.columns:
                
                # CRÍTICO: Limpar colunas para merge
                df['CNPJ_CPF_LIMPO'] = df[COLUNA_CNPJ_CPF].astype(str).str.replace(r'[^0-9]', '', regex=True)
                
                if COLUNA_CPF_NOVO_CADASTRO in df_novos.columns:
                    df_novos['CPF_LIMPO'] = df_novos[COLUNA_CPF_NOVO_CADASTRO].astype(str).str.replace(r'[^0-9]', '', regex=True)
                
                    # 6.1. Identifica QUEM está na lista de Novos Cadastrados
                    df['Novo_Cadastro_Existe'] = df['CNPJ_CPF_LIMPO'].isin(df_novos['CPF_LIMPO'].unique())
                    
                    # 6.2. Calculamos a data da primeira compra histórica para clientes da aba principal
                    df_primeira_compra = df.groupby('CNPJ_CPF_LIMPO')['Data da Venda'].min().reset_index()
                    df_primeira_compra.columns = ['CNPJ_CPF_LIMPO', 'Data_Primeira_Compra_Historica']
                    df = pd.merge(df, df_primeira_compra, on='CNPJ_CPF_LIMPO', how='left')
                    
                    # 6.3. Marca APENAS a linha que corresponde à primeira compra histórica
                    df['Novo_Cadastrado'] = np.where(
                        (df['Novo_Cadastro_Existe'] == True) & 
                        (df['Data da Venda'] == df['Data_Primeira_Compra_Historica']), # CRÍTICO: Usa a data da venda, não a da temporada.
                        True,
                        False
                    )
                else:
                    df['Novo_Cadastrado'] = False 
            
        return df, df_novos # Retorna os dois DataFrames
    
    except FileNotFoundError:
        st.error(f"❌ Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        return pd.DataFrame(), pd.DataFrame() 
    except Exception as e:
        st.error(f"Ocorreu um erro ao ler ou tratar o arquivo: {e}")
        return pd.DataFrame(), pd.DataFrame()