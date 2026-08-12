from pathlib import Path
import sqlite3
import random
from datetime import date, timedelta

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "reporting_demo.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

random.seed(42)

clients = [
    (1, "Atlas Distribution", "Casablanca", "Casablanca-Settat"),
    (2, "Rabat Services", "Rabat", "Rabat-Salé-Kénitra"),
    (3, "Tanger Market", "Tanger", "Tanger-Tétouan-Al Hoceima"),
    (4, "Marrakech Pro", "Marrakech", "Marrakech-Safi"),
    (5, "Fès Business", "Fès", "Fès-Meknès"),
    (6, "Agadir Trading", "Agadir", "Souss-Massa"),
    (7, "Casa Retail", "Casablanca", "Casablanca-Settat"),
    (8, "Rabat Digital", "Rabat", "Rabat-Salé-Kénitra"),
    (9, "Oriental Shop", "Oujda", "Oriental"),
    (10, "Laayoune Store", "Laayoune", "Laâyoune-Sakia El Hamra")
]

produits = [
    (1, "Ordinateur portable", "Informatique", 7500.00),
    (2, "Smartphone", "Téléphonie", 4200.00),
    (3, "Écran 27 pouces", "Informatique", 2300.00),
    (4, "Imprimante laser", "Bureautique", 1800.00),
    (5, "Clavier mécanique", "Accessoires", 650.00),
    (6, "Souris sans fil", "Accessoires", 250.00),
    (7, "Routeur Wi-Fi", "Réseau", 900.00),
    (8, "Disque SSD 1To", "Stockage", 1100.00),
    (9, "Casque audio", "Accessoires", 480.00),
    (10, "Serveur NAS", "Stockage", 6200.00)
]

statuts = ["validée", "validée", "validée", "validée", "annulée", "en attente"]

def random_date(start_year=2024, end_year=2026):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        cur.executescript(f.read())
    cur.executemany(
        "INSERT INTO clients (client_id, nom_client, ville, region) VALUES (?, ?, ?, ?)", clients
    )
    cur.executemany(
        "INSERT INTO produits (produit_id, nom_produit, categorie, prix) VALUES (?, ?, ?, ?)", produits
    )
    commande_id = 1
    ligne_id = 1
    for _ in range(180):
        client_id = random.choice(clients)[0]
        date_commande = random_date().isoformat()
        statut = random.choice(statuts)
        cur.execute(
            "INSERT INTO commandes (commande_id, client_id, date_commande, statut) VALUES (?, ?, ?, ?)",
            (commande_id, client_id, date_commande, statut)
        )
        number_of_lines = random.randint(1, 4)
        selected_products = random.sample(produits, number_of_lines)
        for produit in selected_products:
            produit_id = produit[0]
            prix_standard = produit[3]
            quantite = random.randint(1, 8)
            prix_unitaire = round(prix_standard * random.uniform(0.90, 1.05), 2)
            cur.execute(
                """
                INSERT INTO lignes_commandes
                (ligne_id, commande_id, produit_id, quantite, prix_unitaire)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ligne_id, commande_id, produit_id, quantite, prix_unitaire)
            )
            ligne_id += 1
        commande_id += 1
    conn.commit()
    conn.close()
    print(f"Base de données créée avec succès : {DB_PATH}")

if __name__ == "__main__":
    main()
