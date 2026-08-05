#!/bin/bash

# Nom de la session screen
SESSION_NAME="flask_session"

# Fermer toute session screen existante avec le même nom
screen -X -S $SESSION_NAME quit

# Démarrer une nouvelle session screen détachée
screen -dmS $SESSION_NAME


# Envoyer la commande npm start à la session screen
screen -S $SESSION_NAME -X stuff "./z-run.sh
"

screen -r $SESSION_NAME