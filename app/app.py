import os

import psycopg
from psycopg.rows import dict_row
from flask import Flask, jsonify, request

app = Flask(__name__)


def get_connection():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=5,
        row_factory=dict_row
    )


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                item TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0)
            )
        """)


@app.get("/")
def home():
    return jsonify(
        service="orders-service",
        message="Ordering application is running"
    )


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


@app.get("/ready")
def ready():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return jsonify(status="ready"), 200
    except psycopg.Error:
        app.logger.exception("Database readiness check failed")
        return jsonify(status="not ready"), 503


@app.post("/orders")
def create_order():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Send a JSON object"), 400

    item = data.get("item")
    quantity = data.get("quantity")

    if not isinstance(item, str) or not item.strip():
        return jsonify(error="Item must be a non-empty string"), 400

    if type(quantity) is not int or quantity < 1:
        return jsonify(error="Quantity must be a positive integer"), 400

    with get_connection() as conn:
        order = conn.execute(
            """
            INSERT INTO orders (item, quantity)
            VALUES (%s, %s)
            RETURNING id, item, quantity
            """,
            (item.strip(), quantity)
        ).fetchone()

    return jsonify(order), 201


@app.get("/orders")
def list_orders():
    with get_connection() as conn:
        orders = conn.execute(
            "SELECT id, item, quantity FROM orders ORDER BY id"
        ).fetchall()

    return jsonify(orders), 200


@app.get("/orders/<int:order_id>")
def get_order(order_id):
    with get_connection() as conn:
        order = conn.execute(
            """
            SELECT id, item, quantity
            FROM orders
            WHERE id = %s
            """,
            (order_id,)
        ).fetchone()

    if order is None:
        return jsonify(error="Order not found"), 404

    return jsonify(order), 200


@app.errorhandler(psycopg.Error)
def database_error(error):
    app.logger.exception("Database operation failed")
    return jsonify(error="Database unavailable"), 503