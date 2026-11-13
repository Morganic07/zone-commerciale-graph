"""Lance l'application : `python -m serveur`, puis ouvrir http://localhost:8000."""

import os

import uvicorn

from serveur.app import app

if __name__ == "__main__":
    port = int(os.environ.get("ZC_PORT") or 8000)
    print(f"Zone commerciale : http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)
