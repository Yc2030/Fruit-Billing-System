from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# PRICE LIST
# -----------------------------
PRICES = {
    "apple": 10,
    "banana": 5,
    "orange": 8
}

# -----------------------------
# STORAGE
# -----------------------------
fruit_count = {
    "apple": 0,
    "banana": 0,
    "orange": 0
}

bill_no = 1000

# -----------------------------
# HOME
# -----------------------------
@app.get("/")
def home():
    return {
        "message": "Fruit Billing API Running"
    }

# -----------------------------
# GET LIVE STATUS
# -----------------------------
@app.get("/status")
def status():

    total = 0

    for fruit, count in fruit_count.items():
        total += count * PRICES[fruit]

    return {
        "cart": fruit_count,
        "total_amount": total
    }

# -----------------------------
# ADD ITEM
# -----------------------------
@app.post("/add_item")
def add_item(data: dict):

    fruit = data.get("fruit")

    if not fruit:
        return {
            "error": "Fruit name missing"
        }

    fruit = fruit.lower()

    if fruit in fruit_count:

        fruit_count[fruit] += 1

        return {
            "message": f"{fruit} added",
            "count": fruit_count[fruit]
        }

    return {
        "error": "Unknown fruit"
    }

# -----------------------------
# CREATE BILL
# -----------------------------
@app.post("/create_bill")
def create_bill():

    global bill_no

    total = 0
    items = {}

    for fruit, count in fruit_count.items():

        if count > 0:

            item_total = count * PRICES[fruit]

            items[fruit] = {
                "quantity": count,
                "unit_price": PRICES[fruit],
                "total_price": item_total
            }

            total += item_total

    bill_no += 1

    final_bill = {
        "bill_no": bill_no,
        "items": items,
        "grand_total": total
    }

    # RESET CART
    for fruit in fruit_count:
        fruit_count[fruit] = 0

    return final_bill
