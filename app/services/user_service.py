from app.db.connection import get_db_connection


def create_user(user_name: str, password: str):
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_name, password)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (user_name, password)
            )
            user_id = cur.fetchone()[0]

        conn.commit()
        return user_id

    finally:
        conn.close()