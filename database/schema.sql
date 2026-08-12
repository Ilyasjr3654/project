DROP TABLE IF EXISTS lignes_commandes;
DROP TABLE IF EXISTS commandes;
DROP TABLE IF EXISTS produits;
DROP TABLE IF EXISTS clients;

CREATE TABLE clients (
    client_id INTEGER PRIMARY KEY,
    nom_client TEXT NOT NULL,
    ville TEXT NOT NULL,
    region TEXT NOT NULL
);

CREATE TABLE produits (
    produit_id INTEGER PRIMARY KEY,
    nom_produit TEXT NOT NULL,
    categorie TEXT NOT NULL,
    prix REAL NOT NULL
);

CREATE TABLE commandes (
    commande_id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,
    date_commande DATE NOT NULL,
    statut TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE lignes_commandes (
    ligne_id INTEGER PRIMARY KEY,
    commande_id INTEGER NOT NULL,
    produit_id INTEGER NOT NULL,
    quantite INTEGER NOT NULL,
    prix_unitaire REAL NOT NULL,
    FOREIGN KEY (commande_id) REFERENCES commandes(commande_id),
    FOREIGN KEY (produit_id) REFERENCES produits(produit_id)
);
