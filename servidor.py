import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_NAME = "tasks.db"


def conectar_banco():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tbl_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


def seed_db_if_empty():
    """Insere os dados iniciais se a tabela estiver vazia."""
    initial_tasks = [
        ("Estudar Python", "Ler o capítulo sobre Flask e APIs RESTful", 0),
        ("Comprar comida", "comprar frutas e vegetais para a semana", 0),
        ("Passear com o pet", "Caminhar por 30 minutos no parque", 1),
    ]

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tbl_tasks")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.executemany(
            "INSERT INTO tbl_tasks (title, description, status) VALUES (?, ?, ?)",
            initial_tasks
        )
        conn.commit()

    cursor.close()
    conn.close()


def task_to_dict(row):
    # row = (id, title, description, status_int)
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "status": bool(row[3]),
    }


# GET /tarefa: lista todas as tarefas
@app.route("/tarefa", methods=["GET"])
def listar_tarefas():
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, description, status FROM tbl_tasks")
    tasks = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify([task_to_dict(t) for t in tasks]), 200


# POST /tarefa: cria uma nova tarefa
@app.route("/tarefa", methods=["POST"])
def criar_tarefa():
    dados = request.json or {}

    # validação mínima
    if "title" not in dados or "description" not in dados:
        return jsonify({"erro": "Campos obrigatórios: title, description"}), 400

    status_bool = bool(dados.get("status", False))
    status_int = 1 if status_bool else 0

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tbl_tasks (title, description, status) VALUES (?, ?, ?)",
        (dados["title"], dados["description"], status_int),
    )
    conn.commit()
    new_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return jsonify({"id": new_id}), 201


# GET /tarefa/<id>: retorna uma tarefa específica
@app.route("/tarefa/<int:task_id>", methods=["GET"])
def obter_tarefa(task_id):
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, description, status FROM tbl_tasks WHERE id = ?",
        (task_id,),
    )
    task = cursor.fetchone()

    cursor.close()
    conn.close()

    if not task:
        return jsonify({"erro": "Tarefa não encontrada"}), 404

    return jsonify(task_to_dict(task)), 200


# PUT /tarefa/<id>: atualiza uma tarefa
@app.route("/tarefa/<int:task_id>", methods=["PUT"])
def atualizar_tarefa(task_id):
    dados = request.json or {}

    if "title" not in dados or "description" not in dados or "status" not in dados:
        return jsonify({"erro": "Campos obrigatórios: title, description, status"}), 400

    status_int = 1 if bool(dados["status"]) else 0

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tbl_tasks SET title = ?, description = ?, status = ? WHERE id = ?",
        (dados["title"], dados["description"], status_int, task_id),
    )
    conn.commit()
    linhas = cursor.rowcount

    cursor.close()
    conn.close()

    if linhas == 0:
        return jsonify({"erro": "Tarefa não encontrada"}), 404

    return jsonify({"mensagem": "Tarefa atualizada com sucesso"}), 200


# DELETE /tarefa/<id>: deleta uma tarefa
@app.route("/tarefa/<int:task_id>", methods=["DELETE"])
def deletar_tarefa(task_id):
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tbl_tasks WHERE id = ?", (task_id,))
    conn.commit()
    linhas = cursor.rowcount

    cursor.close()
    conn.close()

    if linhas == 0:
        return jsonify({"erro": "Tarefa não encontrada"}), 404

    return jsonify({"mensagem": "Tarefa excluída com sucesso"}), 200


if __name__ == "__main__":
    init_db()
    seed_db_if_empty()
    app.run(debug=True)
