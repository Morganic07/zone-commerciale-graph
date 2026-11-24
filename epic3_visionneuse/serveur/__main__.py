"""Lance le serveur : `python -m epic3_visionneuse.serveur`, puis ouvrir http://localhost:8000."""

import uvicorn

from epic3_visionneuse.serveur.application import RESEAU_PAR_DEFAUT, creer_application

application = creer_application(RESEAU_PAR_DEFAUT)
uvicorn.run(application, host="127.0.0.1", port=8000)
