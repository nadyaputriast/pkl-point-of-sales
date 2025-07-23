import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson import ObjectId
from PIL import Image, ImageDraw, ImageFont
import io
from whatsapp import send_whatsapp
from datetime import datetime

# --- Load environment and initialize app ---

load_dotenv()
import certifi
app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config["MONGO_CONNECT"] = False
mongo = PyMongo(app, tlsCAFile=certifi.where())
CORS(app)


# --- ROUTES ---
@app.route("/")
def index():
    return "Flask MongoDB Connected!"

## --- CRUD Clients ---
@app.route("/clients", methods=["POST"])
def create_client():
    data = request.json
    data["createdAt"] = data.get("createdAt") or str(request.date)
    result = mongo.db.clients.insert_one(data)
    return jsonify({"_id": str(result.inserted_id), "message": "Client created"}), 201

@app.route("/clients", methods=["GET"])
def get_clients():
    clients = list(mongo.db.clients.find())
    for c in clients:
        c["_id"] = str(c["_id"])
    return jsonify(clients)

@app.route("/clients/<client_id>", methods=["GET"])
def get_client(client_id):
    client = mongo.db.clients.find_one({"_id": ObjectId(client_id)})
    if not client:
        return jsonify({"error": "Client not found"}), 404
    client["_id"] = str(client["_id"])
    return jsonify(client)

@app.route("/clients/<client_id>", methods=["PUT", "PATCH"])
def update_client(client_id):
    data = request.json
    result = mongo.db.clients.update_one({"_id": ObjectId(client_id)}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"error": "Client not found"}), 404
    return jsonify({"message": "Client updated"})

@app.route("/clients/<client_id>", methods=["DELETE"])
def delete_client(client_id):
    result = mongo.db.clients.delete_one({"_id": ObjectId(client_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Client not found"}), 404
    return jsonify({"message": "Client deleted"})

## --- CRUD Invoices ---
@app.route("/invoices", methods=["POST"])
def create_invoice():
    data = request.json
    # Hitung subtotal
    items = data.get("items", [])
    subtotal = sum(float(it.get("price", 0)) for it in items)
    ppn = data.get("ppn", False)
    pph = data.get("pph", False)
    tax = 0
    if ppn:
        tax += subtotal * 0.11
    if pph:
        tax += subtotal * 0.025
    data["tax"] = tax
    data["total"] = subtotal + tax
    # Jika status lunas, set dibayar = total
    if data.get("status") == "lunas":
        data["dibayar"] = data["total"]
    result = mongo.db.invoices.insert_one(data)
    return jsonify({"_id": str(result.inserted_id), "message": "Invoice created"}), 201

@app.route("/invoices", methods=["GET"])
def get_invoices():
    invoices = list(mongo.db.invoices.find())
    for inv in invoices:
        inv["_id"] = str(inv["_id"])
        inv["clientId"] = str(inv["clientId"]) if "clientId" in inv else None
    return jsonify(invoices)

@app.route("/invoices/<invoice_id>", methods=["GET"])
def get_invoice(invoice_id):
    invoice = mongo.db.invoices.find_one({"_id": ObjectId(invoice_id)})
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    invoice["_id"] = str(invoice["_id"])
    invoice["clientId"] = str(invoice["clientId"]) if "clientId" in invoice else None
    return jsonify(invoice)

@app.route("/invoices/<invoice_id>", methods=["PUT", "PATCH"])
def update_invoice(invoice_id):
    data = request.json
    # Hitung subtotal
    items = data.get("items", [])
    subtotal = sum(float(it.get("price", 0)) for it in items)
    ppn = data.get("ppn", False)
    pph = data.get("pph", False)
    tax = 0
    if ppn:
        tax += subtotal * 0.11
    if pph:
        tax += subtotal * 0.025
    data["tax"] = tax
    data["total"] = subtotal + tax
    # Jika status lunas, set dibayar = total
    if data.get("status") == "lunas":
        data["dibayar"] = data["total"]
    result = mongo.db.invoices.update_one({"_id": ObjectId(invoice_id)}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify({"message": "Invoice updated"})

@app.route("/invoices/<invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):
    result = mongo.db.invoices.delete_one({"_id": ObjectId(invoice_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify({"message": "Invoice deleted"})

@app.route("/invoices/<invoice_id>/generate", methods=["GET"])
def generate_invoice_png(invoice_id):
    invoice = mongo.db.invoices.find_one({"_id": ObjectId(invoice_id)})
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    client = mongo.db.clients.find_one({"_id": ObjectId(invoice["clientId"])}) if "clientId" in invoice else None

    # Data untuk invoice
    items = invoice.get("items", [])
    total = invoice.get("total", 0)
    invoice_number = invoice.get("invoiceNumber", "-")
    client_name = client["name"] if client else "-"
    issued_at = invoice.get("issuedAt", "-")
    due_date = invoice.get("dueDate", "-")

    # Buat gambar PNG
    width, height = 600, 400 + 30 * len(items)
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    y = 20
    draw.text((20, y), f"INVOICE: {invoice_number}", font=font, fill=(0,0,0))
    y += 30
    draw.text((20, y), f"Client: {client_name}", font=font, fill=(0,0,0))
    y += 30
    draw.text((20, y), f"Issued: {issued_at}", font=font, fill=(0,0,0))
    y += 30
    draw.text((20, y), f"Due: {due_date}", font=font, fill=(0,0,0))
    y += 40
    draw.text((20, y), "Items:", font=font, fill=(0,0,0))
    y += 30
    for item in items:
        desc = item.get("description", "-")
        price = item.get("price", 0)
        draw.text((40, y), f"- {desc}: Rp{price:,}", font=font, fill=(0,0,0))
        y += 30
    y += 10
    draw.text((20, y), f"TOTAL: Rp{total:,}", font=font, fill=(0,0,0))

    # Simpan ke buffer
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=True, download_name=f"invoice_{invoice_number}.png")

## --- CREATE Project (as Invoice) ---
@app.route("/projects", methods=["POST"])
def create_project():
    data = request.json
    client_id = data.get("clientId")
    project_id = data.get("projectId")  # invoice id
    notes = data.get("notes", "")
    status_project = data.get("statusProject", "belum dikerjakan")
    deadline = data.get("deadline")

    # If projectId (invoice) is given, fetch invoice for details
    invoice = None
    if project_id:
        invoice = mongo.db.invoices.find_one({"_id": ObjectId(project_id)})
    if invoice:
        project_name = invoice["items"][0]["description"] if invoice.get("items") else ""
        auto_deadline = invoice.get("dueDate")
        is_cicil = invoice.get("status") == "cicil"
        deadline_to_use = auto_deadline if is_cicil else (deadline or auto_deadline)
        doc = {
            "clientId": ObjectId(client_id) if client_id and len(client_id) == 24 else client_id,
            "projectId": project_id,
            "projectName": project_name,
            "deadline": deadline_to_use,
            "notes": notes,
            "statusProject": status_project,
            "total": invoice.get("total"),
            "dibayar": invoice.get("dibayar"),
        }
    else:
        # Manual entry (no invoice)
        doc = {
            "clientId": ObjectId(client_id) if client_id and len(client_id) == 24 else client_id,
            "projectName": data.get("projectName", ""),
            "deadline": deadline,
            "notes": notes,
            "statusProject": status_project,
        }
    result = mongo.db.projects.insert_one(doc)
    return jsonify({"_id": str(result.inserted_id), "message": "Project created"}), 201

@app.route("/projects", methods=["GET"])
def get_projects():
    from bson import ObjectId
    # Query params
    search = request.args.get("search", "").lower()
    sort = request.args.get("sort", "deadline-desc")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))

    # Convert clientId to ObjectId if needed (for $lookup to work)
    def ensure_objectid(val):
        try:
            return ObjectId(val) if isinstance(val, str) and len(val) == 24 else val
        except Exception:
            return val

    # Preprocess invoices to ensure clientId is ObjectId
    invoices = list(mongo.db.invoices.find())
    for inv in invoices:
        if "clientId" in inv and isinstance(inv["clientId"], str) and len(inv["clientId"]) == 24:
            inv["clientId"] = ObjectId(inv["clientId"])

    # Use aggregation pipeline
    pipeline = [
        {"$addFields": {"clientId": {"$cond": [
            {"$and": [
                {"$isArray": ["$clientId"]},
                {"$eq": [{"$type": {"$arrayElemAt": ["$clientId", 0]}}, "string"]}
            ]},
            {"$map": {"input": "$clientId", "as": "id", "in": {"$toObjectId": "$$id"}}},
            "$clientId"
        ]}}},
        {"$lookup": {
            "from": "clients",
            "localField": "clientId",
            "foreignField": "_id",
            "as": "client"
        }},
        {"$unwind": {"path": "$client", "preserveNullAndEmptyArrays": True}},
    ]

    # Filtering (search by client name or project name/description)
    if search:
        pipeline.append({
            "$match": {
                "$or": [
                    {"client.name": {"$regex": search, "$options": "i"}},
                    {"items.description": {"$regex": search, "$options": "i"}},
                ]
            }
        })

    # Sorting
    sort_field = "dueDate" if "deadline" in sort else "client.name"
    sort_dir = -1 if sort.endswith("desc") else 1
    pipeline.append({"$sort": {sort_field: sort_dir}})

    # Pagination
    pipeline.append({"$skip": (page - 1) * page_size})
    pipeline.append({"$limit": page_size})

    # Project fields for frontend
    pipeline.append({
        "$project": {
            "_id": 1,
            "clientId": 1,
            "clientName": "$client.name",
            "projectName": {"$arrayElemAt": ["$items.description", 0]},
            "deadline": "$dueDate",
            "status": 1,
            "notes": "$notes",
            "dibayar": 1,
            "total": 1,
        }
    })

    projects = list(mongo.db.invoices.aggregate(pipeline))
    # Calculate outstanding for cicil
    for p in projects:
        p["_id"] = str(p["_id"])
        if p.get("status") == "cicil":
            p["outstanding"] = max((p.get("total") or 0) - (p.get("dibayar") or 0), 0)
        else:
            p["outstanding"] = 0
    return jsonify(projects)

## --- CRUD Payments ---
@app.route("/payments", methods=["POST"])
def create_payment():
    data = request.json
    result = mongo.db.payments.insert_one(data)
    return jsonify({"_id": str(result.inserted_id), "message": "Payment created"}), 201

@app.route("/payments", methods=["GET"])
def get_payments():
    payments = list(mongo.db.payments.find())
    for pay in payments:
        pay["_id"] = str(pay["_id"])
        pay["invoiceId"] = str(pay["invoiceId"]) if "invoiceId" in pay else None
    return jsonify(payments)

@app.route("/payments/<payment_id>", methods=["GET"])
def get_payment(payment_id):
    payment = mongo.db.payments.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        return jsonify({"error": "Payment not found"}), 404
    payment["_id"] = str(payment["_id"])
    payment["invoiceId"] = str(payment["invoiceId"]) if "invoiceId" in payment else None
    return jsonify(payment)

@app.route("/payments/<payment_id>", methods=["PUT", "PATCH"])
def update_payment(payment_id):
    data = request.json
    result = mongo.db.payments.update_one({"_id": ObjectId(payment_id)}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"error": "Payment not found"}), 404
    return jsonify({"message": "Payment updated"})

@app.route("/payments/<payment_id>", methods=["DELETE"])
def delete_payment(payment_id):
    result = mongo.db.payments.delete_one({"_id": ObjectId(payment_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Payment not found"}), 404
    return jsonify({"message": "Payment deleted"})

## --- CRUD Feedbacks ---
@app.route("/feedbacks", methods=["POST"])
def create_feedback():
    data = request.json
    result = mongo.db.feedbacks.insert_one(data)
    return jsonify({"_id": str(result.inserted_id), "message": "Feedback created"}), 201

@app.route("/feedbacks", methods=["GET"])
def get_feedbacks():
    feedbacks = list(mongo.db.feedbacks.find())
    for fb in feedbacks:
        fb["_id"] = str(fb["_id"])
        fb["clientId"] = str(fb["clientId"]) if "clientId" in fb else None
        fb["invoiceId"] = str(fb["invoiceId"]) if "invoiceId" in fb else None
    return jsonify(feedbacks)

@app.route("/feedbacks/<feedback_id>", methods=["GET"])
def get_feedback(feedback_id):
    feedback = mongo.db.feedbacks.find_one({"_id": ObjectId(feedback_id)})
    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404
    feedback["_id"] = str(feedback["_id"])
    feedback["clientId"] = str(feedback["clientId"]) if "clientId" in feedback else None
    feedback["invoiceId"] = str(feedback["invoiceId"]) if "invoiceId" in feedback else None
    return jsonify(feedback)

@app.route("/feedbacks/<feedback_id>", methods=["PUT", "PATCH"])
def update_feedback(feedback_id):
    data = request.json
    result = mongo.db.feedbacks.update_one({"_id": ObjectId(feedback_id)}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"error": "Feedback not found"}), 404
    return jsonify({"message": "Feedback updated"})

@app.route("/feedbacks/<feedback_id>", methods=["DELETE"])
def delete_feedback(feedback_id):
    result = mongo.db.feedbacks.delete_one({"_id": ObjectId(feedback_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Feedback not found"}), 404
    return jsonify({"message": "Feedback deleted"})

@app.route("/send-whatsapp", methods=["POST"])
def send_whatsapp_endpoint():
    data = request.json
    phone = data.get("phone")
    message = data.get("message")
    if not phone or not message:
        return jsonify({"error": "phone and message required"}), 400
    result = send_whatsapp(phone, message)
    return jsonify(result)

## --- Dashboard Summary ---
@app.route("/dashboard/summary", methods=["GET"])
def dashboard_summary():
    total_clients = mongo.db.clients.count_documents({})
    total_invoices = mongo.db.invoices.count_documents({})
    total_payments = mongo.db.payments.count_documents({})
    total_feedbacks = mongo.db.feedbacks.count_documents({})
    total_sales = sum([inv.get("total", 0) for inv in mongo.db.invoices.find()])
    avg_rating = None
    feedbacks = list(mongo.db.feedbacks.find())
    if feedbacks:
        avg_rating = sum([fb.get("rating", 0) for fb in feedbacks]) / len(feedbacks)
    return jsonify({
        "total_clients": total_clients,
        "total_invoices": total_invoices,
        "total_payments": total_payments,
        "total_feedbacks": total_feedbacks,
        "total_sales": total_sales,
        "avg_rating": avg_rating
    })

## --- Relasi: Invoice per Klien ---
@app.route("/clients/<client_id>/invoices", methods=["GET"])
def get_invoices_by_client(client_id):
    invoices = list(mongo.db.invoices.find({"clientId": ObjectId(client_id)}))
    for inv in invoices:
        inv["_id"] = str(inv["_id"])
        inv["clientId"] = str(inv["clientId"]) if "clientId" in inv else None
    return jsonify(invoices)

## --- Generator Nomor Invoice Otomatis ---
def generate_invoice_number():
    today = datetime.now().strftime("%Y%m%d")
    count_today = mongo.db.invoices.count_documents({"issuedAt": today}) + 1
    return f"INV-{today}-{count_today:04d}"

@app.route("/invoices/generate-number", methods=["GET"])
def get_invoice_number():
    invoice_number = generate_invoice_number()
    return jsonify({"invoice_number": invoice_number})


if __name__ == "__main__":
    print("[INFO] Starting Flask app on http://localhost:5000 ...")
    app.run(debug=True, host="0.0.0.0", port=5000)