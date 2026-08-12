from langchain_core.prompts import ChatPromptTemplate


RESULT_INTERPRETATION_SYSTEM_PROMPT = """
Tu es un analyste de reporting commercial. Interprète uniquement les résultats SQL
fournis et réponds en français selon le schéma structuré demandé.

Règles :
- n'invente aucun chiffre ni aucune colonne ;
- choisis "kpi" pour une valeur agrégée unique ;
- choisis "line" pour une évolution temporelle ;
- choisis "bar" pour une comparaison catégorielle lisible ;
- choisis "pie" uniquement pour une répartition avec peu de catégories ;
- choisis "table" lorsque les données détaillées ou nombreuses sont plus appropriées ;
- utilise seulement les noms de colonnes fournis pour x_column, y_columns et series_column ;
- les y_columns d'un graphique doivent être numériques ;
- si aucun graphique n'est pertinent, choisis "text" ou "table" ;
- formule answer de façon concise, factuelle et compréhensible par un métier.
""".strip()


RESULT_INTERPRETATION_HUMAN_PROMPT = """
Question originale : {question}
Titre initial : {title}
Interprétation initiale : {initial_interpretation}

Colonnes et types :
{columns_and_types}

Nombre de lignes : {row_count}

Échantillon limité des résultats :
{sample}

Statistiques simples :
{statistics}
""".strip()


RESULT_INTERPRETATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", RESULT_INTERPRETATION_SYSTEM_PROMPT),
        ("human", RESULT_INTERPRETATION_HUMAN_PROMPT),
    ]
)
