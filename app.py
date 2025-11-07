from flask import Flask, request, jsonify
from flask import Flask, jsonify
import requests
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
from datetime import datetime

# ---------------- Load Environment ----------------
load_dotenv()  # Load variables from .env

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from frontend

# ---------------- MongoDB Connection ----------------
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["hemraj_group"]

# Collections
purchase_collection = db["trading_purchase"]
expense_collection = db["trading_expense"]  # Optional, for future

# ---------------- Helper Functions ----------------
def parse_date(date_str):
    """Convert string YYYY-MM-DD to datetime object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return date_str  # fallback if stored as string

def format_entry(entry):
    """Convert ObjectId to string and datetime to string for frontend."""
    entry["_id"] = str(entry["_id"])
    if isinstance(entry.get("date"), datetime):
        entry["date"] = entry["date"].strftime("%Y-%m-%d")
    return entry



# ---------------- Helper Functions ----------------
def format_expense(expense):
    """Convert ObjectId to string for frontend"""
    expense["_id"] = str(expense["_id"])
    if "date" in expense and isinstance(expense["date"], datetime):
        expense["date"] = expense["date"].strftime("%Y-%m-%d")
    return expense


def parse_date(date_str):
    """Convert YYYY-MM-DD string to datetime"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None
    




API_KEY = "d94ada820d17bd408cccc5cbdf64398f"

@app.route("/api/exchange_rate")
def get_exchange_rate():
    try:
        # Request latest rates from exchangeratesapi.io
        url = f"https://api.exchangeratesapi.io/v1/latest?access_key={API_KEY}&symbols=USD,INR"
        r = requests.get(url)
        data = r.json()

        # Check if API returned an error
        if "error" in data:
            return jsonify({"error": str(data["error"])}), 500

        # Calculate USD → INR rate
        if "rates" in data and "USD" in data["rates"] and "INR" in data["rates"]:
            rate_usd_to_inr = data["rates"]["INR"] / data["rates"]["USD"]
            return jsonify({"rate": round(rate_usd_to_inr, 4)})
        else:
            return jsonify({"error": "Rates unavailable"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500












# ---------------- Trading Purchase Routes ----------------

@app.route("/api/purchases", methods=["GET"])
def get_purchases():
    business_no = request.args.get("businessNo")
    date_from = request.args.get("from")
    date_to = request.args.get("to")

    query = {}

    if business_no:
        query["businessNo"] = {"$regex": business_no, "$options": "i"}

    if date_from or date_to:
        query["date"] = {}
        if date_from:
            query["date"]["$gte"] = parse_date(date_from)
        if date_to:
            query["date"]["$lte"] = parse_date(date_to)
        if not query["date"]:
            query.pop("date")

    entries = list(purchase_collection.find(query).sort("date", -1))
    entries = [format_entry(e) for e in entries]
    return jsonify(entries)

@app.route("/api/purchases", methods=["POST"])
def add_purchase():
    data = request.json
    if "date" in data:
        data["date"] = parse_date(data["date"])
    result = purchase_collection.insert_one(data)
    return jsonify({"_id": str(result.inserted_id)}), 201

@app.route("/api/purchases/<id>", methods=["PUT"])
def update_purchase(id):
    data = request.json
    if "date" in data:
        data["date"] = parse_date(data["date"])
    purchase_collection.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"status": "success"})

@app.route("/api/purchases/<id>", methods=["DELETE"])
def delete_purchase(id):
    purchase_collection.delete_one({"_id": ObjectId(id)})
    return jsonify({"status": "success"})

# ---------------- Trading Expense Routes ----------------

@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    """
    Get all expense jobs, optionally filtered by jobNo.
    """
    job_no = request.args.get("jobNo")
    query = {}

    if job_no:
        query["jobNo"] = {"$regex": job_no, "$options": "i"}

    data = list(expense_collection.find(query).sort("_id", -1))
    data = [format_expense(item) for item in data]
    return jsonify(data)


@app.route("/api/expenses", methods=["POST"])
def add_expense():
    """
    Add a new expense job with jobNo, overallQty, avgRate, avgExpense, bcData, expenseData
    """
    data = request.json
    if not data.get("jobNo"):
        return jsonify({"error": "Job No. is required"}), 400

    # Prevent duplicate jobNo
    existing = expense_collection.find_one({"jobNo": data["jobNo"]})
    if existing:
        return jsonify({"error": "Job No. already exists"}), 409

    data["created_at"] = datetime.now()
    result = expense_collection.insert_one(data)
    return jsonify({"_id": str(result.inserted_id)}), 201


@app.route("/api/expenses/<id>", methods=["PUT"])
def update_expense(id):
    """
    Update an existing expense job by ID
    """
    data = request.json
    expense_collection.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"status": "success"})


@app.route("/api/expenses/<id>", methods=["DELETE"])
def delete_expense(id):
    """
    Delete a job entry by ID
    """
    expense_collection.delete_one({"_id": ObjectId(id)})
    return jsonify({"status": "success"})


# ---------------- Extra: Get Summary ----------------
@app.route("/api/expenses/summary", methods=["GET"])
def get_expense_summary():
    """
    Returns summary of all expenses (avg rate, avg expense, total jobs)
    """
    jobs = list(expense_collection.find())
    if not jobs:
        return jsonify({"totalJobs": 0, "avgRate": 0, "avgExpense": 0})

    avg_rate = sum(job.get("avgRate", 0) for job in jobs) / len(jobs)
    avg_exp = sum(job.get("avgExpense", 0) for job in jobs) / len(jobs)

    return jsonify({
        "totalJobs": len(jobs),
        "avgRate": round(avg_rate, 2),
        "avgExpense": round(avg_exp, 2)
    })


# ---------------- Run Server ----------------
if __name__ == "__main__":
    app.run(debug=True,port=5000)







