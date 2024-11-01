from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import os
from datetime import datetime
from collections import defaultdict

from util import *

app = Flask(__name__)

user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")
port = os.getenv("PORT")
host = os.getenv("HOST")

postgres_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
app.config["SQLALCHEMY_DATABASE_URI"] = postgres_url
db = SQLAlchemy(app)


class Product(db.Model):
    __tablename__ = "products"
    name = db.Column(db.String(80), nullable=False, primary_key=True)
    stock = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)


class OrderMaster(db.Model):
    __tablename__ = "order_masters"
    id = db.Column(db.Integer, primary_key=True)
    time_made = db.Column(
        db.TIMESTAMP(timezone=False), nullable=False, default=datetime.now()
    )
    order_total = db.Column(db.Float, nullable=False)
    rows = relationship("OrderRow", backref="OrderMaster")


class OrderRow(db.Model):
    __tablename__ = "order_rows"
    row_id = db.Column(db.Integer, primary_key=True, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("order_masters.id"))
    product_ordered = db.Column(
        db.String(80), db.ForeignKey("products.name"), nullable=False
    )
    quantity_ordered = db.Column(db.Integer, nullable=False)
    order_subtotal = db.Column(db.Float, nullable=False)


# create tables in db
with app.app_context():
    db.create_all()


@app.route("/products", methods=["GET", "POST"])
def products():
    if request.method == "GET":
        # send list of products
        products = Product.query.all()
        return render_template("products.html", products=products)

    else:
        # insert a new product
        data = request.json
        try:
            name = data["name"]
            stock = data["stock"]
            price = data["price"]

            if Product.query.filter_by(name=name).first():
                app.logger.info(name)
                app.logger.info(Product.query.filter_by(name=name).first())
                return jsonify({"msg": "Product already in DB"})

            new_product = Product(name=name, stock=stock, price=price)
            insert_into_db(db, [new_product])

        except:
            return jsonify({"msg": "Failed inserting product"})

        return jsonify({"msg": f"Product with name {name} inserted into the DB"})


@app.route("/products/<name>", methods=["DELETE"])
def delete_product(name):
    if request.method == "DELETE":
        # check if exists
        product = Product.query.filter_by(name=name).first()
        if product:
            try:
                # since cascade didn't work
                # then should delete the relevant order rows manually
                rows = OrderRow.query.filter_by(product_ordered=product.name).all()
                delete_from_db(db, rows)
                delete_from_db(db, [product])
                return jsonify({"msg": f"Product with name {name} has been deleted"})
            except Exception as e:
                app.logger.info(e)
                return jsonify({"msg": f"Deleting product with name {name} failed"})
        else:
            return jsonify({"msg": f"No product with name {name}"})


@app.route("/orders/<id>", methods=["DELETE"])
def delete_order(id):
    if request.method == "DELETE":
        # check if exists
        order = OrderMaster.query.filter_by(id=id).first()
        if order:
            try:
                # manual cascading delete of sorts
                # delete order rows related to this order master row
                order_rows = OrderRow.query.filter_by(order_id=id).all()
                delete_from_db(db, order_rows)
                delete_from_db(db, [order])
                return jsonify({"msg": f"Order with id {id} has been deleted"})
            except:
                return jsonify({"msg": f"Deleting order with id {id} failed"})
        else:
            return jsonify({"msg": f"No order with id {id}"})


@app.route("/json_products", methods=["GET", "POST"])
def get_json_products():
    if request.method == "GET":
        products = Product.query.all()
    else:
        try:
            data = request.json
            page_num = data["page_num"]
            results_per_page = data["results_per_page"]
            products = Product.query.order_by(Product.name.asc()).paginate(
                page=page_num, per_page=results_per_page, error_out=False
            )
        except:
            products = Product.query.all()

    return jsonify(
        [{"name": i.name, "stock": i.stock, "price": i.price} for i in products]
    )


@app.route("/orders", methods=["GET", "POST"])
def orders():
    if request.method == "GET":
        # send list of orders
        orders = OrderMaster.query.all()
        return render_template("orders.html", orders=orders)

    else:
        # insert a new order
        # expected format
        # TODO: use pydantic to create such dtypes
        """
        {
            "id": int,
            "order_total": float,
            "rows": [
            {
                "product_ordered" : products.name,
                "quantity_ordered" : int,
                "order_subtotal" : float,
            }
            ]
        }
        """
        try:
            data = request.json
            id = data["id"]
            time_made = datetime.now()
            order_total = data["order_total"]
            app.logger.info(data)
            {
                "id": 1000000,
                "order_total": 2.0,
                "rows": [
                    {
                        "order_id": 1000000,
                        "row_id": 1000000,
                        "product_ordered": "product0",
                        "quantity_ordered": 2,
                        "subtotal": 2.0,
                    }
                ],
            }

            if OrderMaster.query.filter_by(id=id).first():
                app.logger.info(id)
                app.logger.info(OrderMaster.query.filter_by(id=id).first())
                return jsonify({"msg": "Order already in DB"})

            new_order = OrderMaster(
                id=id,
                time_made=time_made,
                order_total=order_total,
            )
            insert_into_db(db, [new_order])

            rows = data["rows"]

            new_order_rows = []
            for row in rows:
                row_id = row["row_id"]
                product_ordered = row["product_ordered"]
                quantity_ordered = row["quantity_ordered"]
                order_subtotal = row["order_subtotal"]

                new_order_rows.append(
                    OrderRow(
                        order_id=id,
                        row_id=row_id,
                        product_ordered=product_ordered,
                        quantity_ordered=quantity_ordered,
                        order_subtotal=order_subtotal,
                    )
                )
            insert_into_db(db, new_order_rows)

            return jsonify({"msg": f"New order inserted into the DB"})
        except Exception as e:
            app.logger.info(e)
            return jsonify({"msg": f"Inserting new order failed"})


@app.route("/json_orders", methods=["GET", "POST"])
def get_json_orders():
    if request.method == "GET":
        rows = (
            db.session.query(OrderMaster, OrderRow)
            .join(OrderRow)
            .order_by(OrderMaster.time_made.asc())
            .all()
        )

    else:
        try:
            data = request.json
            page_num = data["page_num"]
            results_per_page = data["results_per_page"]
            rows = (
                db.session.query(OrderMaster, OrderRow)
                .outerjoin(OrderRow)
                .order_by(OrderMaster.time_made.asc())
                .paginate(page=page_num, per_page=results_per_page, error_out=False)
            )
        except:
            rows = (
                db.session.query(OrderMaster, OrderRow)
                .join(OrderRow)
                .order_by(OrderMaster.time_made.asc())
                .all()
            )

    results = []

    for order_master, order_row in rows:
        if order_row == None:
            continue
        results.append(
            {
                "id": order_master.id,
                "order_id": order_row.order_id,
                "time_made": order_master.time_made.isoformat(),
                "order_total": order_master.order_total,
                "row_id": order_row.row_id,
                "product_ordered": order_row.product_ordered,
                "quantity_ordered": order_row.quantity_ordered,
                "order_subtotal": order_row.order_subtotal,
            }
        )
    return jsonify(results)


@app.route("/related_products", methods=["POST"])
def get_related_products():
    """Return products that have been bought together with product p"""

    data = request.json
    try:
        product = data["product"]

    except:
        return {"msg": "No product given"}

    # get order IDs with the product in question
    filtered_order_rows = OrderRow.query.filter_by(product_ordered=product).all()
    app.logger.info
    app.logger.info(product)
    app.logger.info(filtered_order_rows)
    if not filtered_order_rows:
        return jsonify([])

    # TODO: dunno how to aggregate in flask_sqlalchemy
    # shouldve just used the full library
    product_count = OrderRow.query.filter(
        OrderRow.order_id.in_({row.order_id for row in filtered_order_rows})
    ).all()

    # TODO: group by iteration for now, although it's slow and stupid
    counts = defaultdict(int)
    for item in product_count:
        counts[item.product_ordered] += 1

    # remove product p itself
    if product in counts:
        del counts[product]

    return jsonify(
        [x for x, _ in sorted(counts.items(), key=lambda x: x[1], reverse=True)]
    )


@app.route("/order_rows", methods=["GET", "POST"])
def order_rows():
    if request.method == "GET":
        # send list of orders
        orders = OrderRow.query.all()
        return render_template("order_rows.html", orders=orders)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
