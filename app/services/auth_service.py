from app.db.connection import get_db_connection

def register_user(req):
    conn = get_db_connection()
    cur = conn.cursor()

    # 이메일 중복 체크
    cur.execute("SELECT * FROM users WHERE email = %s", (req.email,))
    if cur.fetchone():
        conn.close()

        print(f"[REGISTER] FAIL - email already exists: {req.email}")

        return None, "이미 존재하는 사용자입니다"

    # 유저 생성
    cur.execute(
        """
        INSERT INTO users (user_name, email, password)
        VALUES (%s, %s, %s)
        RETURNING user_id
        """,
        (req.user_name, req.email, req.password)
    )

    user_id = cur.fetchone()[0]

    # 강아지 생성
    cur.execute(
        """
        INSERT INTO dogs (user_id, dog_name, size, is_neutered, vaccination_count)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, req.dog_name, req.size, req.is_neutered, req.vaccination_count)
    )

    conn.commit()
    conn.close()

    print(f"[REGISTER] SUCCESS - user_id={user_id}, email={req.email}")

    return user_id, "회원가입 성공"

def login_user(req):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id, user_name FROM users WHERE user_name=%s AND password=%s",
        (req.user_name, req.password)
    )

    user = cur.fetchone()
    conn.close()

    if user:
        print(f"[LOGIN] SUCCESS - user_id={user[0]}, user_name={user[1]}")
        return user
    else:
        print(f"[LOGIN] FAIL - user_name={req.user_name}")
        return None
