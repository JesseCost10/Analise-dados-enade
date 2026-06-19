import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

try:
    import geopandas as gpd
    import geobr
    HAS_MAP_LIBS = True
except ImportError:
    HAS_MAP_LIBS = False

sns.set_theme(style="whitegrid")

# ==========================================
# 1. CARREGAMENTO GERAL (PÚBLICAS E PRIVADAS)
# ==========================================
def carregar_dados_iniciais():
    print("\n⏳ [1/2] Lendo cursos e categorizando TODAS as instituições (arq1)...")
    colunas_arq1 = ['CO_CURSO', 'CO_GRUPO', 'CO_CATEGAD', 'CO_REGIAO_CURSO']
    df_cursos = pd.read_csv('microdados2021_arq1.txt', sep=';', usecols=colunas_arq1, dtype=str)
    
    for col in colunas_arq1:
        df_cursos[col] = pd.to_numeric(df_cursos[col], errors='coerce')
        
    df_cursos_cc = df_cursos[df_cursos['CO_GRUPO'] == 4004].copy()
    
    mapa_regioes = {1: 'Norte', 2: 'Nordeste', 3: 'Sudeste', 4: 'Sul', 5: 'Centro-Oeste'}
    df_cursos_cc['Nome_Regiao'] = df_cursos_cc['CO_REGIAO_CURSO'].map(mapa_regioes)

    codigos_publicas = [1, 2, 3, 93, 115, 116, 117, 10001, 10002, 10003]
    df_cursos_cc['Tipo_Instituicao'] = df_cursos_cc['CO_CATEGAD'].apply(lambda x: 'Pública' if x in codigos_publicas else 'Privada')

    def mapear_categoria(codigo):
        if codigo == 1: return 'Federal'
        elif codigo == 2: return 'Estadual'
        elif codigo == 3: return 'Municipal'
        elif codigo == 4: return 'Privada (Com fins lucrativos)'
        elif codigo == 5: return 'Privada (Sem fins lucrativos)'
        else: return 'Outras'
    
    df_cursos_cc['Categoria_Admin'] = df_cursos_cc['CO_CATEGAD'].apply(mapear_categoria)

    print("⏳ [2/2] Lendo notas da prova (arq3)...")
    colunas_arq3 = ['CO_CURSO', 'TP_PRES', 'DS_VT_ACE_OCE']
    df_notas = pd.read_csv('microdados2021_arq3.txt', sep=';', usecols=colunas_arq3, dtype=str)
    
    df_notas['CO_CURSO'] = pd.to_numeric(df_notas['CO_CURSO'], errors='coerce')
    df_notas['TP_PRES'] = pd.to_numeric(df_notas['TP_PRES'], errors='coerce')
    
    df_notas_validas = df_notas[df_notas['TP_PRES'] == 555].copy()
    df_final = pd.merge(df_notas_validas, df_cursos_cc, on='CO_CURSO', how='inner')
    
    indices_descartados = [3, 4, 8, 12, 16, 20, 23, 24]
    
    def calcular_nota(respostas):
        if pd.isna(respostas): return np.nan
        acertos = 0
        validas = 0
        for i in range(27):
            if i not in indices_descartados:
                validas += 1
                if respostas[i] == '1': acertos += 1
        return (acertos / validas) * 100 if validas > 0 else 0

    df_final['Nota_Especifica'] = df_final['DS_VT_ACE_OCE'].apply(calcular_nota)
    
    print("✅ Base completa carregada com Sucesso!")
    return df_final, mapa_regioes, indices_descartados

# ==========================================
# FUNÇÃO AUXILIAR: CALCULAR DADOS TEMÁTICOS
# ==========================================
def preparar_dados_tematicos(df_filtrado, mapa_regioes, indices_descartados):
    eixos_tematicos = {
        0: 'Sistemas Operacionais', 1: 'Algoritmos e Est. Dados', 2: 'Inteligência Artificial', 
        5: 'Organização e Arq. de Comp.', 6: 'Engenharia de Software', 7: 'Organização e Arq. de Comp.', 
        9: 'Inteligência Artificial', 10: 'Eng. Software / IHC', 11: 'Algoritmos e Est. Dados', 
        13: 'Bancos de Dados', 14: 'Algoritmos e Est. Dados', 15: 'Eng. Software / Redes', 
        17: 'IHC', 18: 'Probabilidade e Estatística', 19: 'Organização e Arq. de Comp.', 
        21: 'Arq. Comp. / Algoritmos', 22: 'Teoria da Computação', 25: 'Teoria dos Grafos', 26: 'Sistemas Distribuídos'
    }

    resultados = []
    for regiao in mapa_regioes.values():
        df_regiao = df_filtrado[df_filtrado['Nome_Regiao'] == regiao]
        respostas = df_regiao['DS_VT_ACE_OCE'].dropna()
        if len(respostas) == 0: continue
            
        for i in range(27):
            if i in indices_descartados: continue
            taxa_acerto = (respostas.str[i] == '1').mean() * 100
            resultados.append({'Região': regiao, 'Tema': eixos_tematicos[i], 'Taxa de Acerto (%)': taxa_acerto})

    df_consolidado = pd.DataFrame(resultados).groupby(['Tema', 'Região'])['Taxa de Acerto (%)'].mean().reset_index()
    df_pivot = df_consolidado.pivot(index='Tema', columns='Região', values='Taxa de Acerto (%)')
    df_pivot['Média Nacional'] = df_pivot.mean(axis=1)
    df_pivot = df_pivot.sort_values(by='Média Nacional', ascending=False).drop(columns=['Média Nacional'])
    
    return df_pivot

# ==========================================
# MÓDULO 1: OPÇÕES PÚBLICAS
# ==========================================
def opcao_1_tematico_publicas(df_final, mapa_regioes, indices_descartados):
    print("\n⏳ Gerando Mapa de Calor e Planilha (Públicas)...")
    df_publicas = df_final[df_final['Tipo_Instituicao'] == 'Pública']
    df_pivot = preparar_dados_tematicos(df_publicas, mapa_regioes, indices_descartados)
    
    df_pivot.to_excel('planilha_tematica_publicas.xlsx')
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(df_pivot, annot=True, fmt=".1f", cmap="YlGnBu", linewidths=.5, cbar_kws={'label': 'Taxa de Acerto (%)'})
    plt.title('Ranking Temático: Desempenho no ENADE 2021 por Região\n(Universidades Públicas)', fontsize=14, fontweight='bold', pad=20)
    plt.ylabel('')
    plt.xlabel('')
    plt.tight_layout()
    plt.savefig('mapa_de_calor_publicas.png', dpi=300)
    print("✅ SUCESSO! Arquivos 'mapa_de_calor_publicas.png' e 'planilha_tematica_publicas.xlsx' gerados.")

def opcao_2_mapa_publicas(df_final):
    print("\n⏳ Calculando Desempenho Geral (Públicas)...")
    df_publicas = df_final[df_final['Tipo_Instituicao'] == 'Pública']
    medias_regionais = df_publicas.groupby('Nome_Regiao')['Nota_Especifica'].mean().reset_index()
    print("\n📊 Desempenho Médio Geral por Região:")
    print(medias_regionais.to_string(index=False))
    
    if HAS_MAP_LIBS:
        print("⏳ Baixando mapa geográfico...")
        br_regioes = geobr.read_region(year=2020)
        mapa_traducao = {'Norte': 'Norte', 'Nordeste': 'Nordeste', 'Sudeste': 'Sudeste', 'Sul': 'Sul', 'Centro Oeste': 'Centro-Oeste'}
        br_regioes['Nome_Regiao'] = br_regioes['name_region'].map(mapa_traducao)
        
        br_mapa_notas = br_regioes.merge(medias_regionais, on='Nome_Regiao', how='left')
        fig, ax = plt.subplots(figsize=(10, 10))
        br_mapa_notas.plot(column='Nota_Especifica', cmap='Blues', linewidth=0.8, ax=ax, edgecolor='0.2', legend=True)
        
        for idx, row in br_mapa_notas.iterrows():
            plt.annotate(text=f"{row['Nome_Regiao']}\n{row['Nota_Especifica']:.1f}%", 
                         xy=(row['geometry'].centroid.x, row['geometry'].centroid.y),
                         horizontalalignment='center', fontsize=10, fontweight='bold')
            
        plt.title("Desempenho Geral em Ciência da Computação Bacharelado (Públicas)\nENADE 2021", fontsize=14, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig('mapa_brasil_publicas.png', dpi=300)
        print("✅ Mapa visual salvo como 'mapa_brasil_publicas.png'.")

def opcao_3_categorias_publicas(df_final):
    print("\n⏳ Calculando desempenho Federal, Estadual, Municipal...")
    df_publicas = df_final[df_final['Tipo_Instituicao'] == 'Pública']
    resumo_cat = df_publicas.groupby(['Nome_Regiao', 'Categoria_Admin'])['Nota_Especifica'].mean().reset_index()
    resumo_cat.rename(columns={'Nota_Especifica': 'Nota Média (%)'}, inplace=True)
    
    plt.figure(figsize=(14, 7))
    bar_plot = sns.barplot(x='Nome_Regiao', y='Nota Média (%)', hue='Categoria_Admin', data=resumo_cat, palette='Set2')
    plt.title('Desempenho por Categoria Pública (Federal, Estadual, Municipal)\nCiência da Computação Bacharelado - ENADE 2021', fontsize=14, fontweight='bold')
    plt.xlabel('Região')
    plt.ylabel('Nota Média (%)')
    plt.legend(title='Rede Pública', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    for container in bar_plot.containers:
        bar_plot.bar_label(container, fmt='%.1f%%', padding=3, fontsize=10)
        
    plt.tight_layout()
    plt.savefig('comparativo_categorias_publicas.png', dpi=300)
    print("✅ Gráfico salvo como 'comparativo_categorias_publicas.png'.")

def opcao_4_renda_publicas(df_final):
    print("\n⏳ Calculando Relação Institucional entre Renda e Desempenho...")
    if not os.path.exists('microdados2021_arq14.txt'):
        print("🚨 ERRO: O arquivo 'microdados2021_arq14.txt' não está na pasta!")
        return

    df_renda = pd.read_csv('microdados2021_arq14.txt', sep=';', usecols=['CO_CURSO', 'QE_I08'], dtype=str)
    df_renda['CO_CURSO'] = pd.to_numeric(df_renda['CO_CURSO'], errors='coerce')
    
    dicionario_renda = {
        'A': '1. Até 1,5 Salário', 'B': '2. De 1,5 a 3 Salários', 'C': '3. De 3 a 4,5 Salários',
        'D': '4. De 4,5 a 6 Salários', 'E': '5. De 6 a 10 Salários', 'F': '6. De 10 a 30 Salários', 'G': '7. Acima de 30 Salários'
    }
    
    # === AQUI ESTAVA O SEU ERRO! A SOLUÇÃO "À PROVA DE BALAS" ===
    # Remove aspas, espaços em branco e converte para maiúsculo para forçar o reconhecimento do dicionário
    df_renda['QE_I08'] = df_renda['QE_I08'].astype(str).str.replace('"', '').str.strip().str.upper()
    df_renda['Faixa de Renda'] = df_renda['QE_I08'].map(dicionario_renda)
    
    # Remove as rendas inválidas ANTES de agrupar, protegendo a função 'mode()'
    df_renda = df_renda.dropna(subset=['Faixa de Renda'])
    # ==========================================================

    renda_curso = df_renda.groupby('CO_CURSO')['Faixa de Renda'].agg(lambda x: x.mode()[0] if not x.mode().empty else np.nan).reset_index()
    renda_curso.rename(columns={'Faixa de Renda': 'Renda Predominante do Curso'}, inplace=True)
    
    df_publicas = df_final[df_final['Tipo_Instituicao'] == 'Pública']
    nota_curso = df_publicas.groupby('CO_CURSO')['Nota_Especifica'].mean().reset_index()
    
    df_cruzado = pd.merge(nota_curso, renda_curso, on='CO_CURSO', how='inner').dropna()
    
    if df_cruzado.empty:
        print("🚨 ERRO: Nenhum dado foi encontrado após cruzar as notas com as rendas! Verifique se o arquivo arq14 pertence ao ENADE 2021.")
        return
        
    resumo = df_cruzado.groupby('Renda Predominante do Curso')['Nota_Especifica'].mean().reset_index()
    resumo.rename(columns={'Nota_Especifica': 'Nota Média da Universidade (%)'}, inplace=True)
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x='Nota Média da Universidade (%)', y='Renda Predominante do Curso', data=resumo, palette='viridis', order=sorted(resumo['Renda Predominante do Curso'].unique()))
    plt.title('Impacto da Renda Predominante no Desempenho (Públicas)\nCiência da Computação Bacharelado - ENADE 2021', fontsize=14, fontweight='bold')
    plt.xlabel('Nota Média na Componente Específica (%)')
    plt.ylabel('Renda Predominante dos Alunos')
    plt.tight_layout()
    plt.savefig('renda_vs_desempenho_publicas.png', dpi=300)
    print("✅ Gráfico salvo como 'renda_vs_desempenho_publicas.png'.")

# ==========================================
# MÓDULO 2: OPÇÕES PRIVADAS (PARTICULARES)
# ==========================================
def opcao_5_tematico_privadas(df_final, mapa_regioes, indices_descartados):
    print("\n⏳ Gerando Mapa de Calor e Planilha (Apenas Particulares)...")
    df_privadas = df_final[df_final['Tipo_Instituicao'] == 'Privada'].copy()
    
    if df_privadas.empty:
        print("🚨 Nenhuma universidade privada foi encontrada na base!")
        return

    df_pivot = preparar_dados_tematicos(df_privadas, mapa_regioes, indices_descartados)
    
    df_pivot.to_excel('planilha_tematica_privadas.xlsx')
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(df_pivot, annot=True, fmt=".1f", cmap="Reds", linewidths=.5, cbar_kws={'label': 'Taxa de Acerto (%)'})
    plt.title('Ranking Temático: Desempenho no ENADE 2021 por Região\n(Universidades Particulares)', fontsize=14, fontweight='bold', pad=20)
    plt.ylabel('')
    plt.xlabel('')
    plt.tight_layout()
    plt.savefig('mapa_de_calor_privadas.png', dpi=300)
    print("✅ SUCESSO! Arquivos 'mapa_de_calor_privadas.png' e 'planilha_tematica_privadas.xlsx' gerados.")

def opcao_6_categorias_privadas(df_final):
    print("\n⏳ Calculando desempenho Particulares (Com Fins e Sem Fins Lucrativos)...")
    df_privadas = df_final[df_final['Tipo_Instituicao'] == 'Privada'].copy()
    df_privadas = df_privadas[df_privadas['Categoria_Admin'].isin(['Privada (Com fins lucrativos)', 'Privada (Sem fins lucrativos)'])]

    resumo_privadas = df_privadas.groupby(['Nome_Regiao', 'Categoria_Admin'])['Nota_Especifica'].mean().reset_index()
    resumo_privadas.rename(columns={'Nota_Especifica': 'Nota Média (%)'}, inplace=True)
    
    plt.figure(figsize=(14, 7))
    bar_plot = sns.barplot(x='Nome_Regiao', y='Nota Média (%)', hue='Categoria_Admin', data=resumo_privadas, palette='magma')
    plt.title('Desempenho por Categoria Privada\nCiência da Computação Bacharelado - ENADE 2021', fontsize=14, fontweight='bold')
    plt.xlabel('Região')
    plt.ylabel('Nota Média (%)')
    plt.legend(title='Rede Privada', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    for container in bar_plot.containers:
        bar_plot.bar_label(container, fmt='%.1f%%', padding=3, fontsize=10)
        
    plt.tight_layout()
    plt.savefig('comparativo_categorias_privadas.png', dpi=300)
    print("✅ Gráfico salvo como 'comparativo_categorias_privadas.png'.")

# ==========================================
# MENU PRINCIPAL
# ==========================================
def menu_interativo():
    print("="*50)
    print("SISTEMA DE ANÁLISE - ENADE 2021")
    print("="*50)
    
    df_final, mapa_regioes, indices_descartados = carregar_dados_iniciais()
    
    while True:
        print("\n" + "-"*50)
        print("UNIVERSIDADES PÚBLICAS")
        print("1 - Mapa de Calor Temático e Planilha")
        print("2 - Desempenho Médio Regional (Mapa do Brasil)")
        print("3 - Comparativo Institucional (Federal, Estadual, Municipal)")
        print("4 - Relação Institucional entre Renda e Desempenho")
        
        print("\nUNIVERSIDADES PARTICULARES")
        print("5 - Mapa de Calor Temático e Planilha")
        print("6 - Comparativo Institucional (Com Fins e Sem Fins Lucrativos)")
        
        print("\n0 - Sair do Sistema")
        
        escolha = input("Digite o número da opção desejada: ")
        
        if escolha == '1': opcao_1_tematico_publicas(df_final, mapa_regioes, indices_descartados)
        elif escolha == '2': opcao_2_mapa_publicas(df_final)
        elif escolha == '3': opcao_3_categorias_publicas(df_final)
        elif escolha == '4': opcao_4_renda_publicas(df_final)
        elif escolha == '5': opcao_5_tematico_privadas(df_final, mapa_regioes, indices_descartados)
        elif escolha == '6': opcao_6_categorias_privadas(df_final)
        elif escolha == '0':
            print("Saindo...")
            break
        else:
            print("🚨 Opção inválida. Tente novamente.")

if __name__ == "__main__":
    menu_interativo()
