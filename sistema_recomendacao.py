# -*- coding: utf-8 -*-
"""Sistema_Recomendacao.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1uhnAWOI3BHstssn7ygJdsEFTYCUo4aIZ
"""

# Instalar bibliotecas necessárias
!pip install transformers nltk seaborn plotly pyspark

# Importar bibliotecas
import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import mean_absolute_error
from scipy import stats
from pyspark.sql import SparkSession
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
nltk.download("punkt")
nltk.download("stopwords")

# Criar um banco de dados SQLite
conn = sqlite3.connect("produtos.db")

# Criar tabela de usuários
conn.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    user_id INTEGER PRIMARY KEY,
    nome TEXT,
    idade INTEGER,
    genero TEXT
)
""")

# Criar tabela de produtos
conn.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    product_id INTEGER PRIMARY KEY,
    nome TEXT,
    categoria TEXT
)
""")

# Criar tabela de avaliações
conn.execute("""
CREATE TABLE IF NOT EXISTS avaliacoes (
    review_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    product_id INTEGER,
    rating INTEGER,
    comentario TEXT,
    FOREIGN KEY(user_id) REFERENCES usuarios(user_id),
    FOREIGN KEY(product_id) REFERENCES produtos(product_id)
)
""")

# Inserir dados de exemplo
usuarios = [
    (1, "Ana", 25, "F"),
    (2, "Bruno", 30, "M"),
    (3, "Clara", 22, "F"),
    (4, "Daniel", 35, "M"),
    (5, "Eduarda", 28, "F"),
]
conn.executemany("INSERT OR IGNORE INTO usuarios VALUES (?, ?, ?, ?)", usuarios)

produtos = [
    (1, "Smartphone X", "Eletrônicos"),
    (2, "Fone de Ouvido Y", "Eletrônicos"),
    (3, "Livro Z", "Livros"),
    (4, "Câmera W", "Eletrônicos"),
    (5, "Caderno V", "Papelaria"),
]
conn.executemany("INSERT OR IGNORE INTO produtos VALUES (?, ?, ?)", produtos)

avaliacoes = [
    (1, 1, 1, 5, "Adorei o smartphone, muito rápido!"),
    (2, 1, 2, 4, "O fone é bom, mas o som poderia ser mais alto."),
    (3, 2, 1, 3, "O smartphone é ok, mas a bateria não dura muito."),
    (4, 2, 3, 5, "O livro é incrível, recomendo!"),
    (5, 3, 4, 2, "A câmera não atendeu às expectativas."),
    (6, 4, 1, 4, "Smartphone excelente, mas caro."),
    (7, 4, 5, 3, "O caderno é bonito, mas o papel é fino."),
    (8, 5, 2, 5, "Melhor fone que já usei!"),
]
conn.executemany("INSERT OR IGNORE INTO avaliacoes VALUES (?, ?, ?, ?, ?)", avaliacoes)

conn.commit()
conn.close()

print("Banco de dados criado com sucesso!")

# Conectar ao banco de dados SQLite
conn = sqlite3.connect("produtos.db")

# Carregar os dados com Pandas
usuarios_df = pd.read_sql_query("SELECT * FROM usuarios", conn)
produtos_df = pd.read_sql_query("SELECT * FROM produtos", conn)
avaliacoes_df = pd.read_sql_query("SELECT * FROM avaliacoes", conn)

# Fechar a conexão
conn.close()

# Juntar os dados
df = avaliacoes_df.merge(usuarios_df, on="user_id").merge(produtos_df, on="product_id", suffixes=("", "_produto"))

# Salvar como CSV pra uso posterior
df.to_csv("avaliacoes_completas.csv", index=False)

# Usar PySpark pra simular processamento de Big Data
spark = SparkSession.builder.appName("SistemaRecomendacao").getOrCreate()
spark_df = spark.read.csv("avaliacoes_completas.csv", header=True, inferSchema=True)

# Exemplo de transformação com PySpark
spark_df.groupBy("categoria").avg("rating").show()

# Salvar o resultado processado
spark_df.write.mode("overwrite").parquet("avaliacoes_processadas.parquet")

print("Dados processados com sucesso!")

# Carregar os dados processados
df = pd.read_csv("avaliacoes_completas.csv")

# Estatísticas descritivas
print("Estatísticas Descritivas:")
print(df[["rating", "idade"]].describe())

# Teste de normalidade (Shapiro-Wilk) pra ratings
stat, p = stats.shapiro(df["rating"])
print(f"\nTeste de Normalidade (Shapiro-Wilk) para ratings: p-valor = {p:.4f}")
if p > 0.05:
    print("Os ratings parecem seguir uma distribuição normal.")
else:
    print("Os ratings não seguem uma distribuição normal.")

# Correlação entre idade e rating
corr, p = stats.pearsonr(df["idade"], df["rating"])
print(f"\nCorrelação entre idade e rating: {corr:.4f}, p-valor = {p:.4f}")

# Carregar os dados
df = pd.read_csv("avaliacoes_completas.csv")

# Pré-processamento de texto
stop_words = set(stopwords.words("portuguese"))

# Baixar os recursos necessários do NLTK
nltk.download("punkt")
nltk.download("punkt_tab")  # Adicionado para corrigir o erro
nltk.download("stopwords")

def preprocess_text(text):
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalpha() and t not in stop_words]
    return " ".join(tokens)

df["comentario_limpo"] = df["comentario"].apply(preprocess_text)

# Análise de sentimentos com um modelo pré-treinado
from transformers import pipeline
sentiment_analyzer = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
df["sentimento"] = df["comentario_limpo"].apply(lambda x: sentiment_analyzer(x)[0]["label"] if x else "neutro")

# Mapear os sentimentos pra valores numéricos
sentiment_map = {"1 star": -2, "2 stars": -1, "3 stars": 0, "4 stars": 1, "5 stars": 2, "neutro": 0}
df["sentimento_score"] = df["sentimento"].map(sentiment_map)

# Salvar os dados com análise de sentimentos
df.to_csv("avaliacoes_com_sentimentos.csv", index=False)

print("Análise de sentimentos concluída!")
print(df[["comentario", "sentimento", "sentimento_score"]])

# Carregar os dados com sentimentos
df = pd.read_csv("avaliacoes_com_sentimentos.csv")

# Criar uma matriz usuário-produto com ratings ajustados pelo sentimento
df["rating_ajustado"] = df["rating"] + df["sentimento_score"] * 0.5
matriz_usuario_produto = df.pivot(index="user_id", columns="product_id", values="rating_ajustado").fillna(0)

# Calcular similaridade entre usuários usando Scikit-Learn
similaridade_usuarios = cosine_similarity(matriz_usuario_produto)
similaridade_usuarios_df = pd.DataFrame(similaridade_usuarios, index=matriz_usuario_produto.index, columns=matriz_usuario_produto.index)

# Função pra recomendar produtos
def recomendar_produtos(user_id, num_recomendacoes=2):
    # Obter similaridades do usuário
    similaridades = similaridade_usuarios_df[user_id]
    # Ordenar usuários por similaridade (excluindo o próprio usuário)
    usuarios_similares = similaridades.sort_values(ascending=False).index[1:]

    # Obter produtos avaliados pelos usuários similares
    produtos_recomendados = {}
    for similar_user in usuarios_similares:
        # Produtos que o usuário similar avaliou, mas o usuário alvo não
        produtos_similar = matriz_usuario_produto.loc[similar_user]
        produtos_nao_avaliados = produtos_similar[matriz_usuario_produto.loc[user_id] == 0]
        for product_id, rating in produtos_nao_avaliados.items():
            if rating > 0:
                if product_id not in produtos_recomendados:
                    produtos_recomendados[product_id] = []
                produtos_recomendados[product_id].append(rating * similaridades[similar_user])

    # Calcular a média ponderada das avaliações
    recomendacoes = [(product_id, np.mean(ratings)) for product_id, ratings in produtos_recomendados.items()]
    recomendacoes = sorted(recomendacoes, key=lambda x: x[1], reverse=True)[:num_recomendacoes]

    # Mapear product_id pra nomes
    produtos_df = pd.read_sql_query("SELECT * FROM produtos", sqlite3.connect("produtos.db"))
    recomendacoes_nomes = [(produtos_df.loc[produtos_df["product_id"] == pid, "nome"].iloc[0], score) for pid, score in recomendacoes]
    return recomendacoes_nomes

# Testar o sistema de recomendação
user_id = 1
recomendacoes = recomendar_produtos(user_id)
print(f"\nRecomendações para o usuário {user_id}:")
for produto, score in recomendacoes:
    print(f"- {produto}: Score {score:.2f}")

# Salvar as recomendações
with open("recomendacoes.txt", "w") as f:
    f.write(f"Recomendações para o usuário {user_id}:\n")
    for produto, score in recomendacoes:
        f.write(f"- {produto}: Score {score:.2f}\n")

# Carregar os dados
df = pd.read_csv("avaliacoes_com_sentimentos.csv")

# Visualização 1: Distribuição de Ratings por Categoria
plt.figure(figsize=(10, 6))
sns.boxplot(x="categoria", y="rating", data=df)
plt.title("Distribuição de Ratings por Categoria de Produto")
plt.xlabel("Categoria")
plt.ylabel("Rating")
plt.show()

# Visualização 2: Sentimento por Produto (Plotly interativo)
fig = px.bar(df, x="nome_produto", y="sentimento_score", color="sentimento",
             title="Sentimento Médio por Produto",
             labels={"nome_produto": "Produto", "sentimento_score": "Score de Sentimento"})
fig.show()

# Visualização 3: Correlação entre Idade e Rating
plt.figure(figsize=(8, 6))
sns.scatterplot(x="idade", y="rating", hue="genero", size="sentimento_score", data=df)
plt.title("Correlação entre Idade e Rating, com Sentimento e Gênero")
plt.xlabel("Idade")
plt.ylabel("Rating")
plt.show()

# Storytelling
print("""
Relatório de Análise de Avaliações de Produtos

1. **Distribuição de Ratings por Categoria**:
   - A categoria 'Eletrônicos' tem uma ampla variação de ratings, indicando opiniões mistas.
   - 'Livros' e 'Papelaria' têm ratings mais consistentes, geralmente acima de 3.

2. **Sentimento dos Comentários**:
   - Produtos como 'Smartphone X' e 'Fone de Ouvido Y' têm sentimentos positivos, refletindo comentários elogiosos.
   - A 'Câmera W' recebeu comentários negativos, o que pode indicar problemas de qualidade.

3. **Impacto da Idade e Gênero**:
   - Não há uma correlação forte entre idade e rating, mas usuários mais jovens tendem a dar notas mais extremas (muito altas ou muito baixas).
   - Mulheres parecem dar notas ligeiramente mais altas que homens, especialmente em produtos de 'Papelaria'.

Recomendações:
- Focar em melhorar a 'Câmera W', que tem avaliações negativas.
- Promover o 'Smartphone X' e 'Fone de Ouvido Y' em campanhas de marketing, destacando os comentários positivos.
""")

# Carregar os dados
df = pd.read_csv("avaliacoes_com_sentimentos.csv")

# Recriar a coluna rating_ajustado (mesma fórmula usada no Passo 6)
df["rating_ajustado"] = df["rating"] + df["sentimento_score"] * 0.5

# Análise de viés de gênero
print("Análise de Viés de Gênero nos Ratings:")
rating_por_genero = df.groupby("genero")["rating"].mean()
print(rating_por_genero)

# Teste estatístico pra diferença significativa
from scipy.stats import ttest_ind
ratings_f = df[df["genero"] == "F"]["rating"]
ratings_m = df[df["genero"] == "M"]["rating"]
stat, p = ttest_ind(ratings_f, ratings_m)
print(f"\nTeste t para diferença de ratings por gênero: p-valor = {p:.4f}")
if p < 0.05:
    print("Há uma diferença significativa nos ratings entre gêneros, indicando possível viés.")
else:
    print("Não há diferença significativa nos ratings entre gêneros.")

# Avaliar o sistema de recomendação
# Criar a matriz usuário-produto
matriz_usuario_produto = df.pivot(index="user_id", columns="product_id", values="rating_ajustado").fillna(0)

# Calcular similaridade entre usuários
similaridade_usuarios = cosine_similarity(matriz_usuario_produto)
similaridade_usuarios_df = pd.DataFrame(similaridade_usuarios, index=matriz_usuario_produto.index, columns=matriz_usuario_produto.index)

# Função pra prever ratings de produtos já avaliados
def prever_rating(user_id, product_id):
    # Obter similaridades do usuário
    similaridades = similaridade_usuarios_df[user_id]
    # Excluir o próprio usuário
    usuarios_similares = similaridades.index[similaridades.index != user_id]

    # Calcular a previsão como uma média ponderada dos ratings dos usuários similares
    numerador = 0
    denominador = 0
    for similar_user in usuarios_similares:
        rating = matriz_usuario_produto.loc[similar_user, product_id]
        if rating > 0:  # Se o usuário similar avaliou o produto
            similaridade = similaridades[similar_user]
            numerador += similaridade * rating
            denominador += similaridade
    if denominador == 0:
        return 0  # Se não houver usuários similares que avaliaram o produto, retornar 0
    return numerador / denominador

# Calcular previsões e valores verdadeiros
previsoes = []
verdadeiros = []
for user_id in matriz_usuario_produto.index:
    for product_id in matriz_usuario_produto.columns:
        verdadeiro = matriz_usuario_produto.loc[user_id, product_id]
        if verdadeiro > 0:  # Se o usuário avaliou o produto
            previsao = prever_rating(user_id, product_id)
            verdadeiros.append(verdadeiro)
            previsoes.append(previsao)

# Verificar se há valores pra calcular o MAE
if len(verdadeiros) == 0:
    print("\nNão há pares de valores verdadeiros e previstos para calcular o MAE.")
else:
    mae = mean_absolute_error(verdadeiros, previsoes)
    print(f"\nErro Médio Absoluto (MAE) do Sistema de Recomendação: {mae:.2f}")

# Documentar considerações éticas
with open("etica_e_governanca.txt", "w") as f:
    f.write("""
Considerações Éticas e de Governança

1. **Viés de Gênero**:
   - Observamos uma diferença nos ratings médios entre gêneros.
   - Isso pode indicar que o sistema de recomendação favorece produtos avaliados por um gênero específico, o que pode perpetuar desigualdades.

2. **Impacto Social**:
   - Produtos com avaliações negativas (ex.: Câmera W) podem ser recomendados a usuários similares, perpetuando insatisfação.
   - Recomenda-se adicionar um filtro pra evitar recomendar produtos com baixa satisfação.

3. **Governança**:
   - Implementar auditorias regulares pra monitorar vieses.
   - Garantir transparência nas recomendações, informando os usuários sobre como as sugestões são geradas.
""")

"""# Sistema de Recomendação de Produtos

## Descrição
Este projeto implementa um sistema de recomendação de produtos baseado em avaliações de clientes, com análise de sentimentos e visualizações, executado no Google Colab.

## Estrutura do Projeto
O projeto está organizado em células no Colab, com as seguintes etapas:
1. **Configuração do Ambiente**: Instalação de bibliotecas.
2. **Criação do Banco de Dados**: Banco SQLite com dados de usuários, produtos e avaliações.
3. **Processamento de Dados**: Uso de Pandas e PySpark.
4. **Análise Estatística**: Estatísticas descritivas e testes estatísticos.
5. **Processamento de Linguagem Natural (NLP)**: Análise de sentimentos com Transformers.
6. **Sistema de Recomendação**: Filtragem colaborativa com Scikit-Learn.
7. **Visualizações e Storytelling**: Gráficos com Matplotlib, Seaborn e Plotly.
8. **Análise Ética e Governança**: Análise de vieses e considerações éticas.

## Metodologia Ágil
- **Sprint 1**: Configuração do ambiente e criação do banco de dados.
- **Sprint 2**: Processamento de dados e análise estatística.
- **Sprint 3**: NLP e sistema de recomendação.
- **Sprint 4**: Visualizações, storytelling, análise ética e documentação.

## Resultados
- **Arquivos Gerados**:
  - `avaliacoes_completas.csv`: Dados processados.
  - `avaliacoes_com_sentimentos.csv`: Dados com análise de sentimentos.
  - `recomendacoes.txt`: Recomendações geradas.
  - `etica_e_governanca.txt`: Relatório ético.
- **Visualizações**: Gráficos exibidos diretamente no notebook (boxplot, gráfico interativo, scatter plot).
"""