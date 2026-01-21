"""
Sample PDF Generator for Testing - DIVERSE LAYOUTS

Creates two sample PDFs with DIFFERENT document structures and layouts.
Each template has a completely different visual format to prove the
comparison tool works across varied document structures.

Usage:
    python sample_test.py

Output:
    sample_old.pdf - Baseline document
    sample_new.pdf - Document with some changed numbers
"""

import fitz  # PyMuPDF
import random
from datetime import datetime, timedelta


def generate_random_date():
    """Generate a random date within the past year."""
    days_ago = random.randint(1, 365)
    date = datetime.now() - timedelta(days=days_ago)
    return date.strftime("%B %d, %Y")


# ============================================================================
# TEMPLATE 1: Multi-Column Payroll with Header Box
# ============================================================================
def render_payroll(page, data, is_new=False):
    """Payroll with header box, multi-column layout, and signature area."""
    
    # Header box with company info
    page.draw_rect(fitz.Rect(50, 40, 560, 110), color=(0.2, 0.4, 0.6), fill=(0.9, 0.95, 1.0), width=2)
    page.insert_text((60, 65), "ACME CORPORATION", fontsize=18, fontname="helv", color=(0.1, 0.2, 0.4))
    page.insert_text((60, 85), "Human Resources Department", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
    page.insert_text((60, 100), f"Pay Period: {data['date']}", fontsize=9, fontname="helv")
    
    # Employee info box on right
    page.draw_rect(fitz.Rect(350, 45, 555, 105), fill=(1, 1, 1), color=(0.5, 0.5, 0.5))
    page.insert_text((360, 62), f"Employee: {data['employee_id']}", fontsize=9, fontname="helv")
    page.insert_text((360, 77), f"Department: {data['department']}", fontsize=9, fontname="helv")
    page.insert_text((360, 92), f"Position: {data['position']}", fontsize=9, fontname="helv")
    
    # Two-column layout: Earnings (left) and Deductions (right)
    y = 140
    page.insert_text((50, y), "EARNINGS", fontsize=12, fontname="helv", color=(0, 0.5, 0))
    page.insert_text((320, y), "DEDUCTIONS", fontsize=12, fontname="helv", color=(0.7, 0, 0))
    
    # Earnings table
    y = 160
    page.draw_rect(fitz.Rect(50, y, 280, y + 20), fill=(0.85, 0.95, 0.85))
    page.insert_text((55, y + 14), "Description", fontsize=9, fontname="helv")
    page.insert_text((200, y + 14), "Amount", fontsize=9, fontname="helv")
    
    y += 20
    for item in data["earnings"]:
        page.draw_rect(fitz.Rect(50, y, 280, y + 18), color=(0.8, 0.8, 0.8), width=0.3)
        page.insert_text((55, y + 13), item["desc"], fontsize=8, fontname="helv")
        page.insert_text((200, y + 13), f"${item['amount']:,.2f}", fontsize=8, fontname="helv")
        y += 18
    
    # Deductions table
    y_ded = 160
    page.draw_rect(fitz.Rect(320, y_ded, 560, y_ded + 20), fill=(1.0, 0.9, 0.9))
    page.insert_text((325, y_ded + 14), "Description", fontsize=9, fontname="helv")
    page.insert_text((480, y_ded + 14), "Amount", fontsize=9, fontname="helv")
    
    y_ded += 20
    for item in data["deductions"]:
        page.draw_rect(fitz.Rect(320, y_ded, 560, y_ded + 18), color=(0.8, 0.8, 0.8), width=0.3)
        page.insert_text((325, y_ded + 13), item["desc"], fontsize=8, fontname="helv")
        page.insert_text((480, y_ded + 13), f"-${abs(item['amount']):,.2f}", fontsize=8, fontname="helv", color=(0.7, 0, 0))
        y_ded += 18
    
    # Summary box at bottom
    y_sum = max(y, y_ded) + 30
    page.draw_rect(fitz.Rect(50, y_sum, 560, y_sum + 80), fill=(0.95, 0.95, 0.95), color=(0.3, 0.3, 0.3), width=1)
    
    page.insert_text((60, y_sum + 20), f"Gross Pay:", fontsize=10, fontname="helv")
    page.insert_text((180, y_sum + 20), f"${data['gross']:,.2f}", fontsize=10, fontname="helv")
    
    page.insert_text((300, y_sum + 20), f"Total Deductions:", fontsize=10, fontname="helv")
    page.insert_text((450, y_sum + 20), f"${data['total_deductions']:,.2f}", fontsize=10, fontname="helv", color=(0.7, 0, 0))
    
    page.draw_rect(fitz.Rect(60, y_sum + 35, 540, y_sum + 37), fill=(0.5, 0.5, 0.5))
    
    page.insert_text((60, y_sum + 55), "NET PAY:", fontsize=14, fontname="helv", color=(0, 0.3, 0.6))
    page.insert_text((180, y_sum + 55), f"${data['net_pay']:,.2f}", fontsize=14, fontname="helv", color=(0, 0.3, 0.6))
    
    page.insert_text((300, y_sum + 55), f"YTD Earnings: ${data['ytd']:,.2f}", fontsize=9, fontname="helv")
    
    # Signature area
    y_sig = y_sum + 100
    page.draw_line((50, y_sig + 30), (200, y_sig + 30), color=(0, 0, 0), width=0.5)
    page.insert_text((50, y_sig + 45), "Employee Signature", fontsize=8, fontname="helv")
    page.draw_line((350, y_sig + 30), (500, y_sig + 30), color=(0, 0, 0), width=0.5)
    page.insert_text((350, y_sig + 45), "Authorized Signature", fontsize=8, fontname="helv")


def template_payroll():
    base = random.uniform(4500, 7500)
    overtime = random.randint(8, 20) * random.uniform(40, 55)
    
    old_data = {
        "date": generate_random_date(),
        "employee_id": f"EMP-{random.randint(1000, 9999)}",
        "department": random.choice(["Engineering", "Sales", "Marketing", "Finance"]),
        "position": random.choice(["Senior Analyst", "Manager", "Specialist", "Coordinator"]),
        "earnings": [
            {"desc": "Base Salary", "amount": round(base, 2)},
            {"desc": "Overtime Pay", "amount": round(overtime, 2)},
            {"desc": "Bonus", "amount": round(random.uniform(300, 800), 2)},
            {"desc": "Allowances", "amount": round(random.uniform(100, 300), 2)},
        ],
        "deductions": [
            {"desc": "Federal Tax", "amount": round(base * 0.15, 2)},
            {"desc": "State Tax", "amount": round(base * 0.05, 2)},
            {"desc": "Health Insurance", "amount": 245.00},
            {"desc": "401(k)", "amount": round(base * 0.06, 2)},
        ],
        "gross": 0, "total_deductions": 0, "net_pay": 0,
        "ytd": round(random.uniform(50000, 90000), 2)
    }
    old_data["gross"] = sum(e["amount"] for e in old_data["earnings"])
    old_data["total_deductions"] = sum(d["amount"] for d in old_data["deductions"])
    old_data["net_pay"] = old_data["gross"] - old_data["total_deductions"]
    
    # NEW with differences
    new_data = {**old_data}
    new_data["earnings"] = [
        {"desc": "Base Salary", "amount": round(base, 2)},
        {"desc": "Overtime Pay", "amount": round(overtime * 1.15, 2)},
        {"desc": "Bonus", "amount": round(old_data["earnings"][2]["amount"] + 150, 2)},
        {"desc": "Allowances", "amount": round(old_data["earnings"][3]["amount"] + 25, 2)},
    ]
    new_data["deductions"] = [
        {"desc": "Federal Tax", "amount": round(base * 0.155, 2)},
        {"desc": "State Tax", "amount": round(base * 0.052, 2)},
        {"desc": "Health Insurance", "amount": 258.00},
        {"desc": "401(k)", "amount": round(base * 0.065, 2)},
    ]
    new_data["gross"] = sum(e["amount"] for e in new_data["earnings"])
    new_data["total_deductions"] = sum(d["amount"] for d in new_data["deductions"])
    new_data["net_pay"] = new_data["gross"] - new_data["total_deductions"]
    new_data["ytd"] = round(old_data["ytd"] + new_data["gross"], 2)
    
    return old_data, new_data, render_payroll, "Multi-Column Payroll Statement"


# ============================================================================
# TEMPLATE 2: Insurance Policy with Nested Sections
# ============================================================================
def render_insurance(page, data, is_new=False):
    """Insurance with nested sections, coverage bars, and risk indicators."""
    
    # Decorative header
    page.draw_rect(fitz.Rect(0, 0, 612, 80), fill=(0.1, 0.3, 0.5))
    page.insert_text((50, 35), "GUARDIAN INSURANCE GROUP", fontsize=22, fontname="helv", color=(1, 1, 1))
    page.insert_text((50, 55), "Premium Statement & Coverage Summary", fontsize=11, fontname="helv", color=(0.8, 0.9, 1))
    page.insert_text((450, 55), f"Policy: {data['policy_no']}", fontsize=10, fontname="helv", color=(1, 1, 1))
    
    # Policy holder info
    y = 100
    page.insert_text((50, y), f"Policyholder: {data['holder']}", fontsize=10, fontname="helv")
    page.insert_text((350, y), f"Effective: {data['date']}", fontsize=10, fontname="helv")
    
    # Coverage section with visual bars
    y = 130
    page.insert_text((50, y), "COVERAGE BREAKDOWN", fontsize=12, fontname="helv", color=(0.1, 0.3, 0.5))
    y += 20
    
    max_coverage = max(c["coverage"] for c in data["coverages"])
    for cov in data["coverages"]:
        # Coverage bar
        bar_width = (cov["coverage"] / max_coverage) * 250
        page.draw_rect(fitz.Rect(50, y, 50 + bar_width, y + 15), fill=(0.2, 0.5, 0.8))
        page.draw_rect(fitz.Rect(50, y, 300, y + 15), color=(0.7, 0.7, 0.7), width=0.5)
        
        page.insert_text((55, y + 11), cov["type"], fontsize=8, fontname="helv", color=(1, 1, 1) if bar_width > 100 else (0, 0, 0))
        page.insert_text((310, y + 11), f"${cov['coverage']:,.0f}", fontsize=8, fontname="helv")
        page.insert_text((400, y + 11), f"Premium: ${cov['premium']:,.2f}", fontsize=8, fontname="helv")
        page.insert_text((520, y + 11), f"{cov['rate']:.2f}%", fontsize=8, fontname="helv")
        y += 22
    
    # Premium calculation box
    y += 15
    page.draw_rect(fitz.Rect(300, y, 560, y + 100), fill=(0.98, 0.98, 0.98), color=(0.3, 0.3, 0.3), width=1)
    page.insert_text((310, y + 20), "PREMIUM SUMMARY", fontsize=11, fontname="helv", color=(0.1, 0.3, 0.5))
    page.insert_text((310, y + 40), f"Base Premium:", fontsize=9, fontname="helv")
    page.insert_text((470, y + 40), f"${data['base_premium']:,.2f}", fontsize=9, fontname="helv")
    page.insert_text((310, y + 55), f"Risk Adjustment:", fontsize=9, fontname="helv")
    page.insert_text((470, y + 55), f"${data['risk_adj']:,.2f}", fontsize=9, fontname="helv")
    page.insert_text((310, y + 70), f"Discount Applied:", fontsize=9, fontname="helv")
    page.insert_text((470, y + 70), f"-${data['discount']:,.2f}", fontsize=9, fontname="helv", color=(0, 0.5, 0))
    page.draw_line((310, y + 78), (550, y + 78), color=(0, 0, 0), width=0.5)
    page.insert_text((310, y + 92), f"TOTAL ANNUAL:", fontsize=10, fontname="helv")
    page.insert_text((460, y + 92), f"${data['total_premium']:,.2f}", fontsize=11, fontname="helv", color=(0.1, 0.3, 0.5))
    
    # Risk indicator
    page.draw_rect(fitz.Rect(50, y, 280, y + 60), color=(0.5, 0.5, 0.5))
    page.insert_text((60, y + 20), f"Risk Category: {data['risk_cat']}", fontsize=10, fontname="helv")
    page.insert_text((60, y + 40), f"Coverage Score: {data['score']}/100", fontsize=10, fontname="helv")


def template_insurance():
    base_premium = random.uniform(2000, 5000)
    
    old_data = {
        "policy_no": f"POL-{random.randint(10000000, 99999999)}",
        "holder": random.choice(["John Smith", "Jane Doe", "Robert Johnson", "Emily Davis"]),
        "date": generate_random_date(),
        "coverages": [
            {"type": "Life Insurance", "coverage": 500000, "premium": round(500000 * 0.002, 2), "rate": 0.20},
            {"type": "Health Coverage", "coverage": 250000, "premium": round(250000 * 0.004, 2), "rate": 0.40},
            {"type": "Disability", "coverage": 150000, "premium": round(150000 * 0.003, 2), "rate": 0.30},
            {"type": "Critical Illness", "coverage": 100000, "premium": round(100000 * 0.005, 2), "rate": 0.50},
        ],
        "base_premium": round(base_premium, 2),
        "risk_adj": round(base_premium * 0.12, 2),
        "discount": round(base_premium * 0.08, 2),
        "total_premium": round(base_premium * 1.04, 2),
        "risk_cat": "Standard",
        "score": random.randint(70, 85)
    }
    
    new_data = {**old_data}
    new_data["coverages"] = [
        {"type": "Life Insurance", "coverage": 550000, "premium": round(550000 * 0.0022, 2), "rate": 0.22},
        {"type": "Health Coverage", "coverage": 275000, "premium": round(275000 * 0.0042, 2), "rate": 0.42},
        {"type": "Disability", "coverage": 150000, "premium": round(150000 * 0.0032, 2), "rate": 0.32},
        {"type": "Critical Illness", "coverage": 125000, "premium": round(125000 * 0.0048, 2), "rate": 0.48},
    ]
    new_data["base_premium"] = round(base_premium * 1.08, 2)
    new_data["risk_adj"] = round(base_premium * 1.08 * 0.10, 2)
    new_data["discount"] = round(base_premium * 1.08 * 0.10, 2)
    new_data["total_premium"] = round(base_premium * 1.08, 2)
    new_data["risk_cat"] = "Preferred"
    new_data["score"] = old_data["score"] + 5
    
    return old_data, new_data, render_insurance, "Insurance Policy with Visual Bars"


# ============================================================================
# TEMPLATE 3: Invoice with Grid Layout and Itemized Details
# ============================================================================
def render_invoice(page, data, is_new=False):
    """Commercial invoice with grid layout and multiple sections."""
    
    # Top row: Company + Invoice info
    page.draw_rect(fitz.Rect(50, 40, 300, 120), fill=(0.95, 0.95, 0.95))
    page.insert_text((60, 65), "TECH SOLUTIONS INC.", fontsize=14, fontname="helv", color=(0.2, 0.2, 0.5))
    page.insert_text((60, 82), "123 Business Avenue", fontsize=8, fontname="helv")
    page.insert_text((60, 94), "Silicon Valley, CA 94000", fontsize=8, fontname="helv")
    page.insert_text((60, 106), "Tel: (555) 123-4567", fontsize=8, fontname="helv")
    
    page.draw_rect(fitz.Rect(320, 40, 560, 120), fill=(0.2, 0.3, 0.5))
    page.insert_text((340, 65), "INVOICE", fontsize=20, fontname="helv", color=(1, 1, 1))
    page.insert_text((340, 85), f"No: {data['invoice_no']}", fontsize=10, fontname="helv", color=(1, 1, 1))
    page.insert_text((340, 100), f"Date: {data['date']}", fontsize=10, fontname="helv", color=(0.8, 0.9, 1))
    page.insert_text((340, 115), f"Due: {data['due_date']}", fontsize=10, fontname="helv", color=(0.8, 0.9, 1))
    
    # Bill To section
    y = 140
    page.insert_text((50, y), "BILL TO:", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))
    page.insert_text((50, y + 15), data["client"], fontsize=10, fontname="helv")
    page.insert_text((50, y + 28), data["client_addr"], fontsize=8, fontname="helv")
    
    # Items table with alternating rows
    y = 200
    headers = ["Item", "Description", "Qty", "Unit Price", "Total"]
    col_x = [50, 100, 320, 400, 500]
    
    # Header
    page.draw_rect(fitz.Rect(50, y, 560, y + 22), fill=(0.2, 0.3, 0.5))
    for i, h in enumerate(headers):
        page.insert_text((col_x[i] + 5, y + 15), h, fontsize=9, fontname="helv", color=(1, 1, 1))
    
    y += 22
    for idx, item in enumerate(data["items"]):
        bg = (0.97, 0.97, 0.97) if idx % 2 == 0 else (1, 1, 1)
        page.draw_rect(fitz.Rect(50, y, 560, y + 25), fill=bg, color=(0.85, 0.85, 0.85), width=0.3)
        page.insert_text((col_x[0] + 5, y + 16), f"{idx + 1}", fontsize=8, fontname="helv")
        page.insert_text((col_x[1] + 5, y + 16), item["desc"][:35], fontsize=8, fontname="helv")
        page.insert_text((col_x[2] + 5, y + 16), f"{item['qty']}", fontsize=8, fontname="helv")
        page.insert_text((col_x[3] + 5, y + 16), f"${item['price']:,.2f}", fontsize=8, fontname="helv")
        page.insert_text((col_x[4] + 5, y + 16), f"${item['total']:,.2f}", fontsize=8, fontname="helv")
        y += 25
    
    # Totals section
    y += 15
    page.draw_rect(fitz.Rect(350, y, 560, y + 90), fill=(0.95, 0.95, 0.95), color=(0.7, 0.7, 0.7))
    
    page.insert_text((360, y + 18), "Subtotal:", fontsize=9, fontname="helv")
    page.insert_text((490, y + 18), f"${data['subtotal']:,.2f}", fontsize=9, fontname="helv")
    
    page.insert_text((360, y + 35), f"Tax ({data['tax_rate']}%):", fontsize=9, fontname="helv")
    page.insert_text((490, y + 35), f"${data['tax']:,.2f}", fontsize=9, fontname="helv")
    
    page.insert_text((360, y + 52), "Shipping:", fontsize=9, fontname="helv")
    page.insert_text((490, y + 52), f"${data['shipping']:,.2f}", fontsize=9, fontname="helv")
    
    page.draw_line((360, y + 60), (550, y + 60), color=(0.3, 0.3, 0.3), width=1)
    
    page.insert_text((360, y + 78), "TOTAL DUE:", fontsize=11, fontname="helv", color=(0.2, 0.3, 0.5))
    page.insert_text((475, y + 78), f"${data['total']:,.2f}", fontsize=12, fontname="helv", color=(0.2, 0.3, 0.5))
    
    # Payment terms
    y += 110
    page.insert_text((50, y), "Payment Terms: ", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))
    page.insert_text((140, y), data["terms"], fontsize=9, fontname="helv")


def template_invoice():
    items = []
    for i in range(random.randint(4, 6)):
        qty = random.randint(1, 50)
        price = round(random.uniform(50, 500), 2)
        items.append({
            "desc": random.choice(["Software License", "Consulting Hours", "Hardware Component", "Support Package", "Training Session", "Custom Development"]),
            "qty": qty,
            "price": price,
            "total": round(qty * price, 2)
        })
    
    subtotal = sum(i["total"] for i in items)
    tax_rate = random.choice([7.5, 8.0, 8.5, 9.0])
    
    old_data = {
        "invoice_no": f"INV-{random.randint(100000, 999999)}",
        "date": generate_random_date(),
        "due_date": generate_random_date(),
        "client": random.choice(["Global Corp Ltd.", "Pinnacle Industries", "Nexus Enterprises", "Summit Holdings"]),
        "client_addr": "456 Client Street, Business City, BC 12345",
        "items": items,
        "subtotal": round(subtotal, 2),
        "tax_rate": tax_rate,
        "tax": round(subtotal * tax_rate / 100, 2),
        "shipping": round(random.uniform(25, 100), 2),
        "total": round(subtotal * (1 + tax_rate / 100) + random.uniform(25, 100), 2),
        "terms": "Net 30 Days"
    }
    old_data["total"] = round(old_data["subtotal"] + old_data["tax"] + old_data["shipping"], 2)
    
    # NEW version
    new_items = []
    for item in items:
        new_qty = item["qty"] + random.randint(-3, 5)
        new_price = round(item["price"] * random.uniform(0.95, 1.1), 2)
        new_items.append({
            "desc": item["desc"],
            "qty": max(1, new_qty),
            "price": new_price,
            "total": round(max(1, new_qty) * new_price, 2)
        })
    
    new_subtotal = sum(i["total"] for i in new_items)
    new_tax_rate = tax_rate + 0.5
    
    new_data = {**old_data}
    new_data["items"] = new_items
    new_data["subtotal"] = round(new_subtotal, 2)
    new_data["tax_rate"] = new_tax_rate
    new_data["tax"] = round(new_subtotal * new_tax_rate / 100, 2)
    new_data["shipping"] = round(old_data["shipping"] + 15, 2)
    new_data["total"] = round(new_data["subtotal"] + new_data["tax"] + new_data["shipping"], 2)
    
    return old_data, new_data, render_invoice, "Grid Layout Commercial Invoice"


# ============================================================================
# TEMPLATE 4: Financial Report with Charts-like Elements
# ============================================================================
def render_financial(page, data, is_new=False):
    """Financial statement with chart-like visual elements."""
    
    # Clean header
    page.draw_line((50, 60), (560, 60), color=(0.2, 0.4, 0.6), width=2)
    page.insert_text((50, 50), f"QUARTERLY FINANCIAL REPORT - {data['quarter']}", fontsize=16, fontname="helv", color=(0.1, 0.3, 0.5))
    page.insert_text((50, 75), f"Company: {data['company']} | Report Date: {data['date']}", fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
    
    # Key metrics in boxes
    y = 100
    metrics = [
        ("Revenue", data["revenue"], (0.2, 0.6, 0.3)),
        ("Expenses", data["expenses"], (0.7, 0.3, 0.2)),
        ("Net Income", data["net_income"], (0.2, 0.4, 0.7)),
        ("EBITDA", data["ebitda"], (0.5, 0.3, 0.6)),
    ]
    
    box_width = 120
    for i, (label, value, color) in enumerate(metrics):
        x = 50 + i * 130
        page.draw_rect(fitz.Rect(x, y, x + box_width, y + 55), fill=color)
        page.insert_text((x + 10, y + 20), label, fontsize=9, fontname="helv", color=(1, 1, 1))
        page.insert_text((x + 10, y + 42), f"${value:,.0f}", fontsize=12, fontname="helv", color=(1, 1, 1))
    
    # Bar chart simulation for expenses breakdown
    y = 180
    page.insert_text((50, y), "EXPENSE BREAKDOWN", fontsize=11, fontname="helv", color=(0.2, 0.2, 0.2))
    y += 15
    
    max_exp = max(e["amount"] for e in data["expense_breakdown"])
    for exp in data["expense_breakdown"]:
        bar_width = (exp["amount"] / max_exp) * 300
        page.draw_rect(fitz.Rect(150, y, 150 + bar_width, y + 16), fill=(0.3, 0.5, 0.7))
        page.insert_text((55, y + 12), exp["category"], fontsize=8, fontname="helv")
        page.insert_text((460, y + 12), f"${exp['amount']:,.0f}", fontsize=8, fontname="helv")
        y += 22
    
    # Assets vs Liabilities comparison
    y += 20
    page.insert_text((50, y), "BALANCE SHEET SUMMARY", fontsize=11, fontname="helv", color=(0.2, 0.2, 0.2))
    y += 15
    
    # Assets column
    page.draw_rect(fitz.Rect(50, y, 290, y + 120), color=(0.7, 0.7, 0.7))
    page.draw_rect(fitz.Rect(50, y, 290, y + 25), fill=(0.2, 0.5, 0.3))
    page.insert_text((60, y + 17), "ASSETS", fontsize=10, fontname="helv", color=(1, 1, 1))
    
    ay = y + 30
    for asset in data["assets"]:
        page.insert_text((60, ay + 12), asset["name"], fontsize=8, fontname="helv")
        page.insert_text((200, ay + 12), f"${asset['value']:,.0f}", fontsize=8, fontname="helv")
        ay += 18
    
    page.insert_text((60, y + 105), f"Total: ${data['total_assets']:,.0f}", fontsize=9, fontname="helv", color=(0.2, 0.5, 0.3))
    
    # Liabilities column
    page.draw_rect(fitz.Rect(310, y, 560, y + 120), color=(0.7, 0.7, 0.7))
    page.draw_rect(fitz.Rect(310, y, 560, y + 25), fill=(0.6, 0.2, 0.2))
    page.insert_text((320, y + 17), "LIABILITIES", fontsize=10, fontname="helv", color=(1, 1, 1))
    
    ly = y + 30
    for liab in data["liabilities"]:
        page.insert_text((320, ly + 12), liab["name"], fontsize=8, fontname="helv")
        page.insert_text((470, ly + 12), f"${liab['value']:,.0f}", fontsize=8, fontname="helv")
        ly += 18
    
    page.insert_text((320, y + 105), f"Total: ${data['total_liabilities']:,.0f}", fontsize=9, fontname="helv", color=(0.6, 0.2, 0.2))


def template_financial():
    revenue = random.uniform(1000000, 5000000)
    expenses = revenue * random.uniform(0.6, 0.85)
    
    old_data = {
        "quarter": f"Q{random.randint(1, 4)} {random.randint(2024, 2026)}",
        "company": random.choice(["Apex Technologies", "Horizon Industries", "Vertex Corp", "Meridian Inc"]),
        "date": generate_random_date(),
        "revenue": round(revenue, 0),
        "expenses": round(expenses, 0),
        "net_income": round(revenue - expenses, 0),
        "ebitda": round((revenue - expenses) * 1.3, 0),
        "expense_breakdown": [
            {"category": "Salaries & Wages", "amount": round(expenses * 0.45, 0)},
            {"category": "Operations", "amount": round(expenses * 0.25, 0)},
            {"category": "Marketing", "amount": round(expenses * 0.15, 0)},
            {"category": "R&D", "amount": round(expenses * 0.10, 0)},
            {"category": "Admin & Other", "amount": round(expenses * 0.05, 0)},
        ],
        "assets": [
            {"name": "Cash & Securities", "value": round(revenue * 0.3, 0)},
            {"name": "Accounts Receivable", "value": round(revenue * 0.2, 0)},
            {"name": "Property & Equipment", "value": round(revenue * 0.4, 0)},
        ],
        "liabilities": [
            {"name": "Accounts Payable", "value": round(revenue * 0.15, 0)},
            {"name": "Long-term Debt", "value": round(revenue * 0.25, 0)},
            {"name": "Other Liabilities", "value": round(revenue * 0.05, 0)},
        ],
        "total_assets": round(revenue * 0.9, 0),
        "total_liabilities": round(revenue * 0.45, 0),
    }
    
    # NEW version with changes
    new_revenue = revenue * random.uniform(1.02, 1.08)
    new_expenses = new_revenue * random.uniform(0.58, 0.82)
    
    new_data = {**old_data}
    new_data["revenue"] = round(new_revenue, 0)
    new_data["expenses"] = round(new_expenses, 0)
    new_data["net_income"] = round(new_revenue - new_expenses, 0)
    new_data["ebitda"] = round((new_revenue - new_expenses) * 1.35, 0)
    new_data["expense_breakdown"] = [
        {"category": "Salaries & Wages", "amount": round(new_expenses * 0.43, 0)},
        {"category": "Operations", "amount": round(new_expenses * 0.26, 0)},
        {"category": "Marketing", "amount": round(new_expenses * 0.16, 0)},
        {"category": "R&D", "amount": round(new_expenses * 0.11, 0)},
        {"category": "Admin & Other", "amount": round(new_expenses * 0.04, 0)},
    ]
    new_data["assets"] = [
        {"name": "Cash & Securities", "value": round(new_revenue * 0.32, 0)},
        {"name": "Accounts Receivable", "value": round(new_revenue * 0.18, 0)},
        {"name": "Property & Equipment", "value": round(new_revenue * 0.42, 0)},
    ]
    new_data["total_assets"] = round(new_revenue * 0.92, 0)
    new_data["total_liabilities"] = round(new_revenue * 0.42, 0)
    
    return old_data, new_data, render_financial, "Financial Report with Visual Charts"


# ============================================================================
# TEMPLATE 5: Tax Form with Form Fields Layout
# ============================================================================
def render_tax(page, data, is_new=False):
    """Tax form with official form field layout."""
    
    # Official form header
    page.draw_rect(fitz.Rect(50, 40, 560, 100), color=(0, 0, 0), width=1.5)
    page.insert_text((60, 60), "FORM 1040-EZ", fontsize=14, fontname="helv")
    page.insert_text((200, 60), "U.S. Individual Income Tax Return", fontsize=12, fontname="helv")
    page.insert_text((60, 80), f"Tax Year: {data['tax_year']}", fontsize=10, fontname="helv")
    page.insert_text((350, 80), f"SSN: XXX-XX-{data['ssn_last4']}", fontsize=10, fontname="helv")
    
    # Form fields with boxes
    y = 120
    
    # Section A: Income
    page.draw_rect(fitz.Rect(50, y, 560, y + 20), fill=(0.9, 0.9, 0.9))
    page.insert_text((55, y + 14), "SECTION A: INCOME", fontsize=10, fontname="helv")
    y += 25
    
    fields_income = [
        ("1", "Wages, salaries, tips (W-2)", data["wages"]),
        ("2", "Taxable interest", data["interest"]),
        ("3", "Unemployment compensation", data["unemployment"]),
        ("4", "Adjusted Gross Income (add lines 1-3)", data["agi"]),
    ]
    
    for line, desc, value in fields_income:
        page.draw_rect(fitz.Rect(50, y, 80, y + 20), color=(0, 0, 0), width=0.5)
        page.insert_text((60, y + 14), line, fontsize=9, fontname="helv")
        page.insert_text((90, y + 14), desc, fontsize=9, fontname="helv")
        page.draw_rect(fitz.Rect(450, y, 560, y + 20), color=(0, 0, 0), width=0.5)
        page.insert_text((460, y + 14), f"${value:,.2f}", fontsize=9, fontname="helv")
        y += 24
    
    # Section B: Deductions
    y += 10
    page.draw_rect(fitz.Rect(50, y, 560, y + 20), fill=(0.9, 0.9, 0.9))
    page.insert_text((55, y + 14), "SECTION B: DEDUCTIONS & EXEMPTIONS", fontsize=10, fontname="helv")
    y += 25
    
    fields_ded = [
        ("5", "Standard deduction", data["std_deduction"]),
        ("6", "Personal exemption", data["exemption"]),
        ("7", "Taxable income (line 4 minus lines 5-6)", data["taxable_income"]),
    ]
    
    for line, desc, value in fields_ded:
        page.draw_rect(fitz.Rect(50, y, 80, y + 20), color=(0, 0, 0), width=0.5)
        page.insert_text((60, y + 14), line, fontsize=9, fontname="helv")
        page.insert_text((90, y + 14), desc, fontsize=9, fontname="helv")
        page.draw_rect(fitz.Rect(450, y, 560, y + 20), color=(0, 0, 0), width=0.5)
        page.insert_text((460, y + 14), f"${value:,.2f}", fontsize=9, fontname="helv")
        y += 24
    
    # Section C: Tax Computation
    y += 10
    page.draw_rect(fitz.Rect(50, y, 560, y + 20), fill=(0.9, 0.9, 0.9))
    page.insert_text((55, y + 14), "SECTION C: TAX COMPUTATION", fontsize=10, fontname="helv")
    y += 25
    
    fields_tax = [
        ("8", f"Tax from table (rate: {data['tax_rate']}%)", data["tax_from_table"]),
        ("9", "Federal income tax withheld", data["withheld"]),
        ("10", "Earned income credit", data["eic"]),
    ]
    
    for line, desc, value in fields_tax:
        page.draw_rect(fitz.Rect(50, y, 80, y + 20), color=(0, 0, 0), width=0.5)
        page.insert_text((60, y + 14), line, fontsize=9, fontname="helv")
        page.insert_text((90, y + 14), desc, fontsize=9, fontname="helv")
        page.draw_rect(fitz.Rect(450, y, 560, y + 20), color=(0, 0, 0), width=0.5)
        page.insert_text((460, y + 14), f"${value:,.2f}", fontsize=9, fontname="helv")
        y += 24
    
    # Final result box
    y += 15
    if data["refund"] > 0:
        page.draw_rect(fitz.Rect(300, y, 560, y + 40), fill=(0.85, 0.95, 0.85), color=(0, 0.5, 0), width=2)
        page.insert_text((320, y + 25), f"REFUND DUE: ${data['refund']:,.2f}", fontsize=12, fontname="helv", color=(0, 0.4, 0))
    else:
        page.draw_rect(fitz.Rect(300, y, 560, y + 40), fill=(1, 0.9, 0.9), color=(0.7, 0, 0), width=2)
        page.insert_text((320, y + 25), f"AMOUNT OWED: ${abs(data['refund']):,.2f}", fontsize=12, fontname="helv", color=(0.6, 0, 0))
    
    # Signature line
    y += 60
    page.draw_line((50, y), (250, y), color=(0, 0, 0), width=0.5)
    page.insert_text((50, y + 12), "Taxpayer Signature", fontsize=8, fontname="helv")
    page.draw_line((350, y), (500, y), color=(0, 0, 0), width=0.5)
    page.insert_text((350, y + 12), "Date", fontsize=8, fontname="helv")


def template_tax():
    wages = random.uniform(45000, 120000)
    
    old_data = {
        "tax_year": str(random.randint(2024, 2026)),
        "ssn_last4": f"{random.randint(1000, 9999)}",
        "wages": round(wages, 2),
        "interest": round(random.uniform(100, 2000), 2),
        "unemployment": 0.00,
        "agi": round(wages + random.uniform(100, 2000), 2),
        "std_deduction": 13850.00,
        "exemption": 4050.00,
        "taxable_income": round(wages - 17900, 2),
        "tax_rate": 22,
        "tax_from_table": round((wages - 17900) * 0.22, 2),
        "withheld": round(wages * 0.18, 2),
        "eic": 0.00,
        "refund": round(wages * 0.18 - (wages - 17900) * 0.22, 2),
    }
    
    new_wages = wages * random.uniform(1.02, 1.06)
    new_data = {**old_data}
    new_data["wages"] = round(new_wages, 2)
    new_data["interest"] = round(old_data["interest"] + random.uniform(50, 300), 2)
    new_data["agi"] = round(new_data["wages"] + new_data["interest"], 2)
    new_data["std_deduction"] = 14200.00
    new_data["taxable_income"] = round(new_data["agi"] - 14200 - 4050, 2)
    new_data["tax_rate"] = 24
    new_data["tax_from_table"] = round(new_data["taxable_income"] * 0.24, 2)
    new_data["withheld"] = round(new_wages * 0.19, 2)
    new_data["refund"] = round(new_data["withheld"] - new_data["tax_from_table"], 2)
    
    return old_data, new_data, render_tax, "Official Tax Form Layout"


# ============================================================================
# MAIN
# ============================================================================
def main():
    """Generate random old/new PDF pair from 5 diverse templates."""
    
    templates = [
        template_payroll,
        template_insurance,
        template_invoice,
        template_financial,
        template_tax,
    ]
    
    # Randomly select template
    template_func = random.choice(templates)
    old_data, new_data, render_func, template_name = template_func()
    
    print(f"\n{'='*60}")
    print(f"SELECTED TEMPLATE: {template_name}")
    print(f"{'='*60}\n")
    
    # Create OLD PDF
    doc_old = fitz.open()
    page_old = doc_old.new_page(width=612, height=792)
    render_func(page_old, old_data)
    doc_old.save("sample_old.pdf")
    doc_old.close()
    print("Created: sample_old.pdf")
    
    # Create NEW PDF
    doc_new = fitz.open()
    page_new = doc_new.new_page(width=612, height=792)
    render_func(page_new, new_data, is_new=True)
    doc_new.save("sample_new.pdf")
    doc_new.close()
    print("Created: sample_new.pdf")
    
    print(f"\n{'='*60}")
    print(f"Template: {template_name}")
    print(f"The NEW version contains intentional numerical differences.")
    print(f"{'='*60}")
    print("\nTo test, run:")
    print("  python run_pipeline.py sample_old.pdf sample_new.pdf")


if __name__ == "__main__":
    main()
