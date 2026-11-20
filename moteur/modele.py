"""Modèle de données du réseau de stations."""


class ErreurFormat(Exception):
    """Donnée invalide dans un fichier JSON. Le message nomme l'élément fautif."""
