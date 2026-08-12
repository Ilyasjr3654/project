# Exemples Text-to-SQL

## Exemple 1

Question :
Quel est le chiffre d'affaires total ?

SQL :
SELECT ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires_total
FROM commandes c
JOIN lignes_commandes l ON c.commande_id = l.commande_id
WHERE c.statut = 'validée';

## Exemple 2

Question :
Quel est le chiffre d'affaires par région ?

SQL :
SELECT cl.region, ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
FROM clients cl
JOIN commandes c ON cl.client_id = c.client_id
JOIN lignes_commandes l ON c.commande_id = l.commande_id
WHERE c.statut = 'validée'
GROUP BY cl.region
ORDER BY chiffre_affaires DESC;

## Exemple 3

Question :
Quels sont les produits les plus vendus ?

SQL :
SELECT p.nom_produit, SUM(l.quantite) AS quantite_totale
FROM produits p
JOIN lignes_commandes l ON p.produit_id = l.produit_id
JOIN commandes c ON l.commande_id = c.commande_id
WHERE c.statut = 'validée'
GROUP BY p.nom_produit
ORDER BY quantite_totale DESC
LIMIT 10;

## Exemple 4

Question :
Montre-moi les ventes par mois.

SQL :
SELECT strftime('%Y-%m', c.date_commande) AS mois,
       ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
FROM commandes c
JOIN lignes_commandes l ON c.commande_id = l.commande_id
WHERE c.statut = 'validée'
GROUP BY mois
ORDER BY mois;

## Exemple 5

Question :
Quel est le panier moyen ?

SQL :
SELECT ROUND(SUM(l.quantite * l.prix_unitaire) / COUNT(DISTINCT c.commande_id), 2) AS panier_moyen
FROM commandes c
JOIN lignes_commandes l ON c.commande_id = l.commande_id
WHERE c.statut = 'validée';
