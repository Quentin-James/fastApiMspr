"""
Migration MySQL (Docker) → Supabase PostgreSQL
Lancer depuis la racine du projet : python migrate_mysql_to_supabase.py
Pré-requis : pip install pymysql psycopg2-binary sqlalchemy
"""

from sqlalchemy import create_engine, text, URL

MYSQL_URL = "mysql+pymysql://mspr:mspr@localhost:3306/mspr_users"

SUPABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres.qmzirfizvanbzpauzsnh",
    password="Ght1cd12-!d",
    host="aws-1-eu-north-1.pooler.supabase.com",
    port=6543,
    database="postgres",
)


def migrate():
    dst = create_engine(SUPABASE_URL, pool_pre_ping=True)

    # Crée la table sur Supabase
    print("Création du schéma sur Supabase...")
    with dst.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_accounts (
                id            SERIAL PRIMARY KEY,
                email         VARCHAR(255) NOT NULL UNIQUE,
                full_name     VARCHAR(255) NOT NULL,
                password_salt VARCHAR(64)  NOT NULL,
                password_hash VARCHAR(128) NOT NULL,
                role          VARCHAR(32)  NOT NULL DEFAULT 'user',
                is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
                created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
                updated_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
                last_login_at TIMESTAMP
            )
        """))
    print("Schéma OK.")

    # Lecture depuis MySQL (optionnel — si le container Docker tourne)
    rows = []
    try:
        src = create_engine(
            MYSQL_URL,
            connect_args={"auth_plugin": "mysql_native_password"},
            pool_pre_ping=True,
        )
        with src.connect() as conn:
            rows = conn.execute(text("SELECT * FROM user_accounts")).fetchall()
        print(f"MySQL: {len(rows)} utilisateur(s) trouvé(s).")
    except Exception as e:
        print(f"MySQL inaccessible ({e.__class__.__name__}: {e})")
        print("→ Aucune donnée à migrer, le schéma Supabase est prêt.")
        return

    if not rows:
        print("Rien à migrer.")
        return

    # Insertion dans Supabase
    with dst.begin() as conn:
        for row in rows:
            conn.execute(text("""
                INSERT INTO user_accounts
                    (id, email, full_name, password_salt, password_hash,
                     role, is_active, created_at, updated_at, last_login_at)
                VALUES
                    (:id, :email, :full_name, :password_salt, :password_hash,
                     :role, :is_active, :created_at, :updated_at, :last_login_at)
                ON CONFLICT (email) DO NOTHING
            """), row._mapping)

        conn.execute(text(
            "SELECT setval('user_accounts_id_seq', (SELECT MAX(id) FROM user_accounts))"
        ))

    print(f"Migration terminée : {len(rows)} ligne(s) transférée(s).")


if __name__ == "__main__":
    migrate()
