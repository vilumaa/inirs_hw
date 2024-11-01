import random
import requests
import string
from datetime import datetime


def generate_products(num_products):
    """Generates products by inserting them into the DB 1-by-1"""
    post_url = "http://localhost:5000/products"

    for _ in range(num_products):

        name = "".join(
            random.choice(string.ascii_letters + string.digits) for _ in range(10)
        )
        # probably no conflicts, but api will reject insertion if does conflict
        stock = random.randint(1, 20)
        price = random.random() * 10
        new_product = {"name": name, "stock": stock, "price": price}
        response = requests.post(post_url, json=new_product)
        print(response.text)


def get_products():
    return requests.get("http://localhost:5000/json_products").json()


def generate_orders(num_orders):
    """Generated orders with varying amounts of rows"""

    post_url = "http://localhost:5000/orders"

    products = get_products()
    if not products:
        return

    for _ in range(num_orders):

        id = random.randint(1_000_000, 9_999_999)
        rows = []
        num_rows = random.randint(1, min(5, len(products)))
        bought_products_for_this_order = random.choices(products, k=num_rows)
        for _ in range(num_rows):
            current_product = bought_products_for_this_order.pop(0)
            quantity_ordered = random.randint(1, 10)
            rows.append(
                {
                    "row_id": random.randint(1_000_000, 9_999_999),
                    "order_id": id,
                    "product_ordered": current_product["name"],
                    "quantity_ordered": quantity_ordered,
                    "order_subtotal": current_product["price"] * quantity_ordered,
                }
            )
        order_total = sum(row["order_subtotal"] for row in rows)
        new_order = {
            "id": id,
            "order_total": order_total,
            "rows": rows,
        }

        response = requests.post(post_url, json=new_order)
        print(response.text)


if __name__ == "__main__":
    generate_products(30)
    generate_orders(50)
