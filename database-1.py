import aiosqlite
import os

DB_PATH = os.environ.get("DB_PATH", "quiz_bot.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                language TEXT DEFAULT 'uz',
                joined_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                is_active INTEGER DEFAULT 0,
                added_by INTEGER DEFAULT 0,
                added_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                role TEXT DEFAULT 'admin',
                added_by INTEGER DEFAULT 0,
                added_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                questions TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                quiz_id INTEGER,
                score INTEGER,
                total INTEGER,
                mode TEXT,
                finished_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("INSERT OR IGNORE INTO settings VALUES ('bot_active', '1')")
        await db.commit()


# ── Users ──

async def add_user(user_id, username, first_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?,?,?)",
            (user_id, username or '', first_name or '')
        )
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY rowid DESC") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_user_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            return row[0]


async def set_language(user_id, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        await db.commit()


# ── Subscriptions ──

async def add_subscription(user_id, added_by):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO subscriptions (user_id, is_active, added_by) VALUES (?,1,?)",
            (user_id, added_by)
        )
        await db.commit()


async def remove_subscription(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET is_active=0 WHERE user_id=?", (user_id,)
        )
        await db.commit()


async def is_subscribed(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_active FROM subscriptions WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row and row[0] == 1


async def get_all_subscriptions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u.user_id, u.username, u.first_name, s.is_active, s.added_at
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.is_active = 1
            ORDER BY s.added_at DESC
        """) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_subscription_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active=1") as cur:
            row = await cur.fetchone()
            return row[0]


async def add_all_subscriptions(added_by):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            users = await cur.fetchall()
        for (uid,) in users:
            await db.execute(
                "INSERT OR REPLACE INTO subscriptions (user_id, is_active, added_by) VALUES (?,1,?)",
                (uid, added_by)
            )
        await db.commit()
        return len(users)


async def remove_all_subscriptions():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE subscriptions SET is_active=0")
        await db.commit()


# ── Admins ──

async def add_admin(user_id, added_by, role='admin'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO admins (user_id, role, added_by) VALUES (?,?,?)",
            (user_id, role, added_by)
        )
        await db.commit()


async def remove_admin(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()


async def is_admin(user_id, super_admin_id):
    if user_id == super_admin_id:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None


async def get_all_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins ORDER BY added_at DESC") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ── Quizzes ──

async def save_quiz(user_id, title, questions_json):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO quizzes (user_id, title, questions) VALUES (?,?,?)",
            (user_id, title, questions_json)
        )
        await db.commit()
        return cur.lastrowid


async def get_quiz(quiz_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_quizzes(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM quizzes WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ── Results ──

async def save_result(user_id, quiz_id, score, total, mode):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO results (user_id, quiz_id, score, total, mode) VALUES (?,?,?,?,?)",
            (user_id, quiz_id, score, total, mode)
        )
        await db.commit()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active=1") as cur:
            active_subs = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM quizzes") as cur:
            total_quizzes = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM results") as cur:
            total_results = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now', '-1 day')"
        ) as cur:
            today_users = (await cur.fetchone())[0]
        return {
            "total_users": total_users,
            "active_subs": active_subs,
            "total_quizzes": total_quizzes,
            "total_results": total_results,
            "today_users": today_users,
        }


# ── Settings ──

async def is_bot_active():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key='bot_active'") as cur:
            row = await cur.fetchone()
            return row[0] == '1' if row else True


async def toggle_bot():
    current = await is_bot_active()
    new_val = '0' if current else '1'
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE settings SET value=? WHERE key='bot_active'", (new_val,))
        await db.commit()
    return not current
