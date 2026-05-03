import psycopg


def get_db_connection():
    return psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="pet_travel_db",
        user="pet_travel_user",
        password="pet_travel_pass"
    )


# 테스트용 (선택)
if __name__ == "__main__":
    try:
        conn = get_db_connection()
        print("DB 연결 성공")

        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public';
            """)
            tables = cur.fetchall()

            print("현재 테이블 목록:")
            for table in tables:
                print("-", table[0])

        conn.close()

    except Exception as e:
        print("DB 연결 실패:", e)