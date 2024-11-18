# delete_migrations.py
import os

# Exclure le dossier 'myenv' du traitement
excluded_folder = 'myenv'

for folderName, subfolders, filenames in os.walk('.'):
    # Vérifier si le dossier en cours d'itération fait partie des dossiers exclus
    if excluded_folder in folderName:
        continue

    for filename in filenames:
        # Supprimer les fichiers de migration Python (hors __init__.py)
        if folderName.endswith('migrations') and filename.endswith('.py'):
            if not filename.startswith('__init__'):
                print('FILE INSIDE ' + folderName + ': ' + folderName + '/' + filename)
                os.unlink(os.path.join(folderName, filename))
        
        # Supprimer les fichiers de cache Python dans les migrations
        if folderName.endswith('migrations/__pycache__') and filename.endswith('.pyc'):
            print('FILE INSIDE ' + folderName + ': ' + folderName + '/' + filename)
            os.unlink(os.path.join(folderName, filename))
