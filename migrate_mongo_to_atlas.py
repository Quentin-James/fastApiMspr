"""
Migration MongoDB (Docker) → MongoDB Atlas
Lancer depuis la racine du projet : python migrate_mongo_to_atlas.py
Pré-requis : pip install pymongo
"""

from pymongo import MongoClient

MONGO_LOCAL = "mongodb://localhost:27017"
MONGO_ATLAS = "mongodb+srv://jamesquentin46_db_user:it34Zu0TQFOJmIg5@cluster0.0rfiezq.mongodb.net/?appName=Cluster0"
DB_NAME = "mspr_ia"

COLLECTIONS = [
    "recommendations",
    "meal_plans",
    "sport_programs",
    "user_profiles",
]


def migrate():
    print("Connexion à MongoDB local...")
    src_client = MongoClient(MONGO_LOCAL, serverSelectionTimeoutMS=5000)
    src_db = src_client[DB_NAME]

    print("Connexion à MongoDB Atlas...")
    dst_client = MongoClient(MONGO_ATLAS, serverSelectionTimeoutMS=10000)
    dst_db = dst_client[DB_NAME]

    total = 0
    for col_name in COLLECTIONS:
        docs = list(src_db[col_name].find())
        if not docs:
            print(f"  {col_name}: vide, ignoré.")
            continue

        # Évite les doublons sur _id
        for doc in docs:
            dst_db[col_name].replace_one({"_id": doc["_id"]}, doc, upsert=True)

        print(f"  {col_name}: {len(docs)} document(s) transféré(s).")
        total += len(docs)

    src_client.close()
    dst_client.close()
    print(f"\nMigration terminée : {total} document(s) au total vers Atlas.")


if __name__ == "__main__":
    migrate()
