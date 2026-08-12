# Dictionnaire de données - Chatbot de reporting

## Objectif

Ce dictionnaire de données décrit la base commerciale de démonstration utilisée pour le projet de chatbot de reporting Text-to-SQL.

Il sert à fournir au module RAG et au LLM le contexte nécessaire pour comprendre les tables, les colonnes, les relations et les règles métier.

## Tables

### Table `clients`

| Colonne | Type | Description |
|---|---|---|
| client_id | INTEGER | Identifiant unique du client |
| nom_client | TEXT | Nom du client |
| ville | TEXT | Ville du client |
| region | TEXT | Région commerciale du client |

Rôle : stocker les informations des clients.

### Table `produits`

| Colonne | Type | Description |
|---|---|---|
| produit_id | INTEGER | Identifiant unique du produit |
| nom_produit | TEXT | Nom du produit |
| categorie | TEXT | Catégorie du produit |
| prix | REAL | Prix standard du produit |

Rôle : stocker les produits vendus par l'entreprise.

### Table `commandes`

| Colonne | Type | Description |
|---|---|---|
| commande_id | INTEGER | Identifiant unique de la commande |
| client_id | INTEGER | Référence vers le client |
| date_commande | DATE | Date de la commande |
| statut | TEXT | Statut de la commande : validée, annulée, en attente |

Rôle : stocker les commandes passées par les clients.

### Table `lignes_commandes`

| Colonne | Type | Description |
|---|---|---|
| ligne_id | INTEGER | Identifiant unique de la ligne de commande |
| commande_id | INTEGER | Référence vers la commande |
| produit_id | INTEGER | Référence vers le produit |
| quantite | INTEGER | Quantité commandée |
| prix_unitaire | REAL | Prix appliqué au produit dans cette commande |

Rôle : stocker le détail des produits dans chaque commande.

## Relations

- `clients.client_id = commandes.client_id`
- `commandes.commande_id = lignes_commandes.commande_id`
- `produits.produit_id = lignes_commandes.produit_id`

## Règles métier

- Le chiffre d'affaires est calculé avec : `SUM(lignes_commandes.quantite * lignes_commandes.prix_unitaire)`.
- Seules les commandes avec le statut `validée` sont prises en compte dans le chiffre d'affaires.
- Les commandes avec le statut `annulée` ne doivent pas être incluses dans les ventes.
- Les commandes avec le statut `en attente` ne doivent pas être incluses dans le chiffre d'affaires validé.
- Le panier moyen est calculé par : chiffre d'affaires total / nombre de commandes validées.
- Les ventes par région nécessitent les tables `clients`, `commandes` et `lignes_commandes`.
- Les ventes par produit nécessitent les tables `produits`, `lignes_commandes` et `commandes`.
- Les ventes par mois sont calculées à partir de `commandes.date_commande`.

## Synonymes métier

| Terme utilisateur | Signification |
|---|---|
| CA | Chiffre d'affaires |
| chiffre d'affaires | `SUM(quantite * prix_unitaire)` |
| ventes | Commandes validées |
| meilleur client | Client avec le plus grand chiffre d'affaires |
| top produits | Produits les plus vendus |
| évolution mensuelle | Agrégation par mois |
| commande annulée | `statut = 'annulée'` |
| commande validée | `statut = 'validée'` |
| région | `clients.region` |
| ville | `clients.ville` |
