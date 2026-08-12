ALLOWED_SCHEMA: dict[str, dict[str, str]] = {
    "clients": {
        "client_id": "INTEGER",
        "nom_client": "TEXT",
        "ville": "TEXT",
        "region": "TEXT",
    },
    "produits": {
        "produit_id": "INTEGER",
        "nom_produit": "TEXT",
        "categorie": "TEXT",
        "prix": "REAL",
    },
    "commandes": {
        "commande_id": "INTEGER",
        "client_id": "INTEGER",
        "date_commande": "DATE",
        "statut": "TEXT",
    },
    "lignes_commandes": {
        "ligne_id": "INTEGER",
        "commande_id": "INTEGER",
        "produit_id": "INTEGER",
        "quantite": "INTEGER",
        "prix_unitaire": "REAL",
    },
}

ALLOWED_TABLES = frozenset(ALLOWED_SCHEMA)
SYSTEM_SCHEMAS = frozenset(
    {
        "information_schema",
        "pg_catalog",
        "sqlite_master",
        "sqlite_schema",
        "sqlite_temp_master",
    }
)


def schema_as_text() -> str:
    sections: list[str] = []
    for table, columns in ALLOWED_SCHEMA.items():
        sections.append(f"Table {table}:")
        sections.extend(f"- {name} {data_type}" for name, data_type in columns.items())
        sections.append("")
    return "\n".join(sections).strip()
