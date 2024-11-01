import pytest
from hypothesis import given, settings, example
from hypothesis import strategies as st
import requests


@st.composite
def generate_random_data(draw):

    # generate some products
    number_of_products = draw(st.integers(min_value=1, max_value=30))
    product_indices = range(number_of_products)

    # names must be unique, since they're primary key
    unique_names = draw(
        st.lists(
            st.from_regex("product[0-9]+", fullmatch=True),
            min_size=number_of_products,
            max_size=number_of_products,
            unique=True,
        )
    )
    names = {idx: unique_names[idx] for idx in product_indices}
    name_list = list(names.values())
    stock_levels = draw(
        st.fixed_dictionaries({idx: st.integers(3, 30) for idx in product_indices})
    )
    prices = draw(
        st.fixed_dictionaries({idx: st.floats(1, 10) for idx in product_indices})
    )

    products = [
        {
            "name": names[item],
            "stock": stock_levels[item],
            "price": prices[item],
        }
        for item in product_indices
    ]
    prices_by_name = {product["name"]: product["price"] for product in products}

    # generate some orders with some products ordered
    number_of_orders = draw(st.integers(min_value=1, max_value=50))
    order_indices = range(number_of_orders)

    # row_ids and order_ids must be unique, since they're primary key
    unique_order_ids = draw(
        st.lists(
            st.integers(min_value=1_000_000, max_value=9_999_999),
            min_size=number_of_orders,
            max_size=number_of_orders,
            unique=True,
        )
    )
    order_ids = draw(
        st.just(
            {idx: unique_order_ids[idx] for idx in order_indices},
        )
    )

    products_in_order = draw(
        st.fixed_dictionaries(
            {
                idx: st.sets(
                    elements=st.sampled_from(name_list),
                    min_size=1,
                    max_size=5,
                )
                for idx in order_indices
            }
        )
    )

    unique_row_ids = draw(
        st.lists(
            st.integers(min_value=1_000_000, max_value=9_999_999),
            min_size=len(order_indices) * 5,
            max_size=len(order_indices) * 5,
            unique=True,
        )
    )

    row_ids = {
        idx: {product: unique_row_ids.pop(0) for product in products_in_order[idx]}
        for idx in order_indices
    }
    quantities_ordered = draw(
        st.fixed_dictionaries(
            {
                idx: st.fixed_dictionaries(
                    {
                        product: st.integers(min_value=2, max_value=2000)
                        for product in products_in_order[idx]
                    }
                )
                for idx in order_indices
            }
        )
    )
    subtotals = {
        (idx, product): prices_by_name[product] * quantities_ordered[idx][product]
        for idx, set_of_products in products_in_order.items()
        for product in set_of_products
    }
    totals = {
        idx: sum(value for (idx2, p), value in subtotals.items() if idx == idx2)
        for idx in order_indices
    }

    orders = [
        {"id": order_ids[idx], "order_total": totals[idx], "rows": []}
        for idx in order_indices
    ]
    orders_by_id = {order["id"]: order for order in orders}
    order_rows = [
        {
            "order_id": order_ids[idx],
            "row_id": row_ids[idx][product],
            "product_ordered": product,
            "quantity_ordered": quantities_ordered[idx][product],
            "order_subtotal": subtotals[idx, product],
        }
        for idx in order_indices
        for product in products_in_order[idx]
    ]
    for order_row in order_rows:
        orders_by_id[order_row["order_id"]]["rows"].append(order_row)

    return dict(products=products, orders=orders)


@settings(
    max_examples=100,
    deadline=None,
)
@example(
    {
        "products": [{"name": "product0", "stock": 3, "price": 1.0}],
        "orders": [
            {
                "id": 1000000,
                "order_total": 2.0,
                "rows": [
                    {
                        "order_id": 1000000,
                        "row_id": 1000000,
                        "product_ordered": "product0",
                        "quantity_ordered": 2,
                        "order_subtotal": 2.0,
                    }
                ],
            }
        ],
    }
)
@given(generate_random_data())
def test_random_candidate_full_run(data):
    """Add all items, get items from db, make sure they're in there, then delete again"""

    # clean DB from potential existing rows
    product_deletion_url = "http://localhost:5000/products/"
    for product in data["products"]:
        response = requests.delete(product_deletion_url + product["name"])

    # delete orders
    order_deletion_url = "http://localhost:5000/orders/"
    for order in data["orders"]:
        response = requests.delete(order_deletion_url + str(order["id"]))

    # add products
    product_insertion_url = "http://localhost:5000/products"
    for product in data["products"]:
        response = requests.post(product_insertion_url, json=product)
        assert (
            "inserted into the DB" in response.json()["msg"]
            or "already in DB" in response.json()["msg"]
        ), response.json()["msg"]

    # add orders
    order_insertion_url = "http://localhost:5000/orders"
    for order in data["orders"]:
        response = requests.post(order_insertion_url, json=order)

    # get json_products
    # use GT to get all products
    json_products_url = "http://localhost:5000/json_products"
    response_all = requests.get(json_products_url)
    product_names_in_db = [product["name"] for product in response_all.json()]
    # check all products are in the response (i.e. they're in the DB)
    for product in data["products"]:
        assert product["name"] in product_names_in_db

    # get 1 page worth of products
    response_1_page = requests.post(
        json_products_url, json={"page_num": 2, "results_per_page": 5}
    )
    # ensure 1 page is <= than all products
    assert len(response_all.json()) >= len(response_1_page.json())

    # get json_orders
    json_orders_url = "http://localhost:5000/json_orders"
    response_all = requests.get(json_orders_url)
    order_ids_in_db = [order["id"] for order in response_all.json()]
    # check all orders are in the response (i.e. they're in the DB)
    for order in data["orders"]:
        assert order["id"] in order_ids_in_db

    # get 1 page worth of orders
    response_1_page = requests.post(
        json_orders_url, json={"page_num": 2, "results_per_page": 5}
    )
    # ensure 1 page is <= than all orders
    assert len(response_all.json()) >= len(response_1_page.json())

    # get_related_products
    related_products_url = "http://localhost:5000/related_products"
    a_product = data["products"][0]
    response = requests.post(related_products_url, json={"product": a_product["name"]})
    # expecting a list of products (potentially empty)
    assert isinstance(response.json(), list)

    # delete products
    # clean DB from potential existing rows
    product_deletion_url = "http://localhost:5000/products/"
    for product in data["products"]:
        response = requests.delete(product_deletion_url + product["name"])
        product_name = product["name"]
        assert (
            response.json()["msg"]
            == f"Product with name {product_name} has been deleted"
        )

    # delete orders
    order_deletion_url = "http://localhost:5000/orders/"
    for order in data["orders"]:
        response = requests.delete(order_deletion_url + str(order["id"]))
        order_id = order["id"]
        assert response.json()["msg"] == f"Order with id {order_id} has been deleted"


def test_relevant_products():
    """Add some items, make sure they come up in related products, then delete"""

    data = {
        "products": [
            {"name": "myprod1", "stock": 3, "price": 1.0},
            {"name": "myprod2", "stock": 3, "price": 1.0},
        ],
        "orders": [
            {
                "id": 100000000,
                "order_total": 4.0,
                "rows": [
                    {
                        "order_id": 100000000,
                        "row_id": 100000000,
                        "product_ordered": "myprod1",
                        "quantity_ordered": 2,
                        "order_subtotal": 2.0,
                    },
                    {
                        "order_id": 100000000,
                        "row_id": 100000000,
                        "product_ordered": "myprod2",
                        "quantity_ordered": 2,
                        "order_subtotal": 2.0,
                    },
                ],
            }
        ],
    }

    # add products
    product_insertion_url = "http://localhost:5000/products"
    for product in data["products"]:
        response = requests.post(product_insertion_url, json=product)
        print(response.json())

    # add orders
    order_insertion_url = "http://localhost:5000/orders"
    for order in data["orders"]:
        response = requests.post(order_insertion_url, json=order)
        print(response.json())

    # get_related_products
    related_products_url = "http://localhost:5000/related_products"
    a_product = data["products"][0]
    response = requests.post(related_products_url, json={"product": a_product["name"]})
    # expecting a list of products (potentially empty)
    assert data["products"][1] in response.json()

    # delete products
    # clean DB from potential existing rows
    product_deletion_url = "http://localhost:5000/products/"
    for product in data["products"]:
        response = requests.delete(product_deletion_url + product["name"])

    """
    # delete orders
    order_deletion_url = "http://localhost:5000/orders/"
    for order in data["orders"]:
        response = requests.delete(order_deletion_url + str(order["id"]))
    """
