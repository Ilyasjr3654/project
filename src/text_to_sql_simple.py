import re
import unicodedata


def normalize_question(question: str) -> str:
    text = unicodedata.normalize("NFKD", question.lower().strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9 ]", " ", text)


def question_to_sql_simple(question: str) -> tuple[str | None, str]:
    q = normalize_question(question)

    if (
        "mois" in q
        and "region" in q
        and ("chiffre d affaires" in q or "vente" in q or "ca" in q)
    ):
        return """
        SELECT strftime('%Y-%m', c.date_commande) AS mois,
               cl.region,
               ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
        FROM clients cl
        JOIN commandes c ON cl.client_id = c.client_id
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée'
        GROUP BY mois, cl.region
        ORDER BY mois, chiffre_affaires DESC;
        """, "Analyse mensuelle du chiffre d'affaires par région."

    if (
        "mois" in q
        and ("plus grand" in q or "meilleur" in q or "plus eleve" in q)
        and ("chiffre d affaires" in q or "vente" in q or "ca" in q)
    ):
        return """
        SELECT strftime('%Y-%m', c.date_commande) AS mois,
               ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
        FROM commandes c
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée'
        GROUP BY mois
        ORDER BY chiffre_affaires DESC
        LIMIT 1;
        """, "Identification du mois avec le chiffre d'affaires le plus élevé."

    if (
        "quantite totale" in q
        and ("vendue" in q or "vendu" in q or "vente" in q)
    ):
        return """
        SELECT SUM(l.quantite) AS quantite_totale_vendue
        FROM commandes c
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée';
        """, "Calcul de la quantité totale vendue sur les commandes validées."

    if "chiffre d affaires total" in q or "ca total" in q:
        return """
        SELECT ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires_total
        FROM commandes c
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée';
        """, "Calcul du chiffre d'affaires total des commandes validées."

    if "chiffre d affaires par region" in q or "ca par region" in q or "ventes par region" in q:
        return """
        SELECT cl.region, ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
        FROM clients cl
        JOIN commandes c ON cl.client_id = c.client_id
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée'
        GROUP BY cl.region
        ORDER BY chiffre_affaires DESC;
        """, "Analyse du chiffre d'affaires par région."

    if "chiffre d affaires de casablanca" in q or "ca de casablanca" in q or "ventes de casablanca" in q:
        return """
        SELECT cl.ville, ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
        FROM clients cl
        JOIN commandes c ON cl.client_id = c.client_id
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée'
          AND cl.ville = 'Casablanca'
        GROUP BY cl.ville;
        """, "Calcul du chiffre d'affaires des clients de Casablanca."

    if "ville" in q and ("vente" in q or "chiffre d affaires" in q or "ca" in q):
        limit_clause = "LIMIT 1" if "plus" in q or "meilleur" in q or "fort" in q else ""
        return f"""
        SELECT cl.ville, ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
        FROM clients cl
        JOIN commandes c ON cl.client_id = c.client_id
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée'
        GROUP BY cl.ville
        ORDER BY chiffre_affaires DESC
        {limit_clause};
        """, "Analyse du chiffre d'affaires par ville."

    if "meilleurs clients" in q or "top clients" in q or "5 clients" in q:
        return """
        SELECT cl.nom_client, cl.ville, cl.region,
               ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
        FROM clients cl
        JOIN commandes c ON cl.client_id = c.client_id
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée'
        GROUP BY cl.client_id, cl.nom_client, cl.ville, cl.region
        ORDER BY chiffre_affaires DESC
        LIMIT 5;
        """, "Classement des 5 meilleurs clients par chiffre d'affaires."

    if "produits les plus vendus" in q or "top produits" in q:
        return """
        SELECT p.nom_produit, p.categorie, SUM(l.quantite) AS quantite_totale
        FROM produits p
        JOIN lignes_commandes l ON p.produit_id = l.produit_id
        JOIN commandes c ON l.commande_id = c.commande_id
        WHERE c.statut = 'validée'
        GROUP BY p.produit_id, p.nom_produit, p.categorie
        ORDER BY quantite_totale DESC
        LIMIT 10;
        """, "Classement des produits les plus vendus."

    if (
        "produits par categorie" in q
        or ("categorie" in q and "plus de produits" in q)
        or ("categorie" in q and "contient" in q and "produit" in q)
    ):
        limit_clause = "LIMIT 1" if "plus" in q or "contient" in q else ""
        return f"""
        SELECT p.categorie, COUNT(*) AS nombre_produits
        FROM produits p
        GROUP BY p.categorie
        ORDER BY nombre_produits DESC
        {limit_clause};
        """, "Comptage des produits par catégorie."

    if "categorie" in q:
        return """
        SELECT p.categorie, ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
        FROM produits p
        JOIN lignes_commandes l ON p.produit_id = l.produit_id
        JOIN commandes c ON l.commande_id = c.commande_id
        WHERE c.statut = 'validée'
        GROUP BY p.categorie
        ORDER BY chiffre_affaires DESC;
        """, "Analyse du chiffre d'affaires par catégorie."

    if "ventes par mois" in q or "evolution" in q:
        return """
        SELECT strftime('%Y-%m', c.date_commande) AS mois,
               ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
        FROM commandes c
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée'
        GROUP BY mois
        ORDER BY mois;
        """, "Évolution mensuelle du chiffre d'affaires."

    if "commandes annulees" in q or "annulee" in q:
        return """
        SELECT COUNT(*) AS nombre_commandes_annulees
        FROM commandes
        WHERE statut = 'annulée';
        """, "Nombre de commandes annulées."

    if (
        "commandes recentes" in q
        or "dernieres commandes" in q
        or ("commandes" in q and "recentes" in q)
    ):
        return """
        SELECT commande_id, client_id, date_commande, statut
        FROM commandes
        ORDER BY date_commande DESC
        LIMIT 10;
        """, "Liste des commandes les plus récentes."

    if "panier moyen" in q:
        return """
        SELECT ROUND(SUM(l.quantite * l.prix_unitaire) / COUNT(DISTINCT c.commande_id), 2) AS panier_moyen
        FROM commandes c
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée';
        """, "Calcul du panier moyen des commandes validées."

    if "compare" in q and "2024" in q and "2025" in q:
        return """
        SELECT strftime('%Y', c.date_commande) AS annee,
               ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS chiffre_affaires
        FROM commandes c
        JOIN lignes_commandes l ON c.commande_id = l.commande_id
        WHERE c.statut = 'validée'
          AND strftime('%Y', c.date_commande) IN ('2024', '2025')
        GROUP BY annee
        ORDER BY annee;
        """, "Comparaison du chiffre d'affaires entre 2024 et 2025."

    return None, "Question non reconnue dans le mode simple. Essaie le mode LangChain + RAG + LLM."
