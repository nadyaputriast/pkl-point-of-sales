"""
Struktur data transaksi dan feedback untuk MongoDB.
Tidak perlu class model, cukup dict/JSON.

Contoh dokumen transaksi:
{
    "buyer_name": "Budi",
    "buyer_phone": "08123456789",
    "items": [
        {"website": "A", "price": 10000},
        {"website": "B", "price": 20000}
    ],
    "admin": "Admin1",
    "total": 30000,
    "payment_type": "Transfer",
    "invoice_path": "/invoices/invoice_123.pdf",
    "feedback": {
        "rating": 5,
        "comment": "Bagus!"
    },
    "created_at": "2025-07-22T10:00:00"
}
"""
# Tidak perlu class model, data langsung disimpan sebagai dict/JSON ke MongoDB
