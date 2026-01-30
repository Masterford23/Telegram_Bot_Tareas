import sqlite3

DB_NAME = "tasks.db"


# ============================
# INICIALIZAR BASE DE DATOS
# ============================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task TEXT
    )
    """)

    conn.commit()
    conn.close()


# ============================
# AGREGAR TAREA
# ============================
def add_task(user_id, task):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tasks (user_id, task) VALUES (?, ?)",
        (user_id, task)
    )

    conn.commit()
    conn.close()


# ============================
# OBTENER TAREAS POR USUARIO
# ============================
def get_tasks(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, task FROM tasks WHERE user_id = ?",
        (user_id,)
    )

    tasks = cursor.fetchall()
    conn.close()

    return tasks


# ============================
# ELIMINAR TAREA
# ============================
def delete_task(user_id, task_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )

    conn.commit()
    conn.close()


# ============================
# EDITAR TAREA
# ============================
def update_task(user_id, task_id, new_text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tasks SET task = ? WHERE id = ? AND user_id = ?",
        (new_text, task_id, user_id)
    )

    conn.commit()
    conn.close()
