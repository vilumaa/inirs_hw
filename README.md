# inirs_hw

How to host the server and DB:
run `docker-compose up`

## DB Objects:

### Product:

    name: String, primary_key
    stock: Integer
    price: Float

### OrderMaster:

    id: Integer, primary_key
    time_made = TIMESTAMP
    order_total: Float

### OrderRow:

    row_id: Integer, primary_key
    order_id: Integer, ForeignKey("order_masters.id")
    product_ordered: String, ForeignKey("products.name")
    quantity_ordered: Integer
    order_subtotal: Float

## Endpoints:

### GET:

/products - returns html table showing all products
/orders - returns html table showing all master orders
/order_rows - returns html table showing all order rows
/json_products - returns all products as JSON
/json_orders - returns all orders as JSON

### POST:

/products - insert new product

```
{
    "name": str,
    "stock": int,
    "price": float
}
```

/orders - insert new order master and individual order rows

```
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
```

/json_products - returns some paginated products as JSON

```
{
    page_num: int,
    results_per_page:int
}
```

/json_orders - returns some orders as JSON

```
{
    page_num: int,
    results_per_page:int
}
```

/related_products - returns popularity-sorted list of products that are bought together with a specific product

```
{
    "product": str
}
```

### DELETE:

/products/<name> - deletes product `name`
`name: str`

/orders/<id> - deletes master order `id` and individual order rows
`name: str`

## Tests:

1. Install required modules (pytest, hypothesis)
   For example using poetry:
   `poetry install`
2. Run tests using `poetry run pytest`
3. TODO: some teardown/reset method is needed for the tests to work well. Ow failing tests populate the DB with old data, breaking future tests
