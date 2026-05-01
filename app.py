import os
import base64
import streamlit as st
import re
import uuid
import pandas as pd
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SESSION_TIMEOUT_MINUTES = 30

def get_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# -----------------------------
# AUTH
# -----------------------------
def check_timeout():
    if "last_activity" in st.session_state:
        elapsed = datetime.now() - st.session_state.last_activity
        if elapsed > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            st.session_state.logged_in = False
            st.session_state.last_activity = None

def reset_timer():
    st.session_state.last_activity = datetime.now()

def show_login():
    _, col, _ = st.columns([1, 1, 1])
    with col:
        logo_b64 = get_image_base64(os.path.join(BASE_DIR, "logo", "Raza Herbal Dawakhana 3.png"))
        st.markdown(
            f"<div style='text-align:center'><img src='data:image/png;base64,{logo_b64}' width='130'/><h2>Raza Herbal Dawakhana</h2></div>",
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("🔐 Login"):
            valid_user = st.secrets["auth"]["username"]
            valid_pass = st.secrets["auth"]["password"]
            if username == valid_user and password == valid_pass:
                st.session_state.logged_in = True
                st.session_state.last_activity = datetime.now()
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

check_timeout()

if not st.session_state.logged_in:
    st.set_page_config(page_title="Raza Herbal Dawakhana", layout="centered")
    show_login()
    st.stop()
else:
    st.set_page_config(page_title="Raza Herbal Dawakhana", layout="wide")

reset_timer()

logo_b64 = get_image_base64(os.path.join(BASE_DIR, "logo", "Raza Herbal Dawakhana 3.png"))
st.markdown(
    f"""
    <div style='text-align:center'>
        <img src='data:image/png;base64,{logo_b64}' width='160'/>
        <h2 style='margin-top:8px'>Raza Herbal Dawakhana</h2>
    </div>
    """,
    unsafe_allow_html=True
)

st.subheader("🧾 Customer Order Entry")

# FILE PATHS & SCHEMA
orders_file      = os.path.join(BASE_DIR, "data", "orders.csv")
order_items_file = os.path.join(BASE_DIR, "data", "order_items.csv")

ORDERS_SCHEMA     = ["order_id", "timestamp", "customer_name", "age", "phone", "order_source", "payment_method"]
ORDER_ITEMS_SCHEMA = ["item_id", "order_id", "product_name", "quantity", "price", "discount_amount"]

# SESSION STATE
if "products" not in st.session_state:
    st.session_state.products = []

if "form_key" not in st.session_state:
    st.session_state.form_key = 0

if "show_success" not in st.session_state:
    st.session_state.show_success = False

# CLEANING FUNCTIONS
def clean_name(name):
    return re.sub(r"[^A-Za-z ]", "", name)

def clean_phone(phone):
    return re.sub(r"\D", "", phone)[:10]

# CUSTOMER INFO
if st.session_state.show_success:
    st.success("✅ Order saved! Enter next order.")
    st.session_state.show_success = False


col1, col2, col3 = st.columns(3)

with col1:
    raw_name = st.text_input("Customer Name", key=f"cust_name_{st.session_state.form_key}")
    customer_name = clean_name(raw_name).lower()
    if raw_name.lower() != customer_name:
        st.warning("Only alphabets allowed")

with col2:
    age = st.number_input("Age", min_value=1, step=1, key=f"age_{st.session_state.form_key}")

with col3:
    raw_phone = st.text_input("Phone Number", key=f"phone_{st.session_state.form_key}")
    phone = clean_phone(raw_phone)
    if raw_phone != phone:
        st.warning("Only digits allowed (10 max)")

# ORDER INFO
st.header("🛒 Order Info")

col4, col5 = st.columns(2)

with col4:
    order_source = st.selectbox(
        "Order Source",
        ["Select", "Walk-in", "Online", "WhatsApp", "Call"],
        key=f"order_source_{st.session_state.form_key}"
    )

with col5:
    payment_method = st.selectbox(
        "Payment Method",
        ["Select", "Cash", "UPI", "Card"],
        key=f"payment_method_{st.session_state.form_key}"
    )

 
# PRODUCTS

st.header("📦 Products")

if st.button("➕ Add Product"):
    st.session_state.products.append(str(uuid.uuid4()))
    st.rerun()

to_remove = None

for pid in st.session_state.products:
    idx = st.session_state.products.index(pid)
    st.subheader(f"Product {idx + 1}")

    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])

    with col1:
        raw_pname = st.text_input(f"Product Name", key=f"name_{pid}")
        pname = re.sub(r"[^A-Za-z0-9 ]", "", raw_pname)
        if raw_pname != pname:
            st.warning("Special characters removed")

    with col2:
        st.number_input("Quantity", min_value=1, step=1, key=f"qty_{pid}")

    with col3:
        st.number_input("Selling Price", min_value=0.01, key=f"price_{pid}")

    with col4:
        st.number_input("Discount Amount (₹)", min_value=0.0, key=f"disc_{pid}")

    with col5:
        st.write("")
        st.write("")
        if st.button("❌ Remove", key=f"remove_{pid}"):
            to_remove = pid

if to_remove:
    st.session_state.products.remove(to_remove)
    st.rerun()

# SUBMIT
if st.button("✅ Submit Order"):

    errors = []

    if not customer_name.strip():
        errors.append("Customer name required")

    if age <= 0:
        errors.append("Valid age required")

    if len(phone) != 10:
        errors.append("Phone must be 10 digits")

    if order_source == "Select":
        errors.append("Select order source")

    if payment_method == "Select":
        errors.append("Select payment method")

    if len(st.session_state.products) == 0:
        errors.append("Add at least one product")

    order_items_data = []

    for pid in st.session_state.products:
        idx   = st.session_state.products.index(pid)
        pname = re.sub(r"[^A-Za-z0-9 ]", "", st.session_state.get(f"name_{pid}", "")).lower()
        qty   = st.session_state.get(f"qty_{pid}")
        price = st.session_state.get(f"price_{pid}")
        disc  = st.session_state.get(f"disc_{pid}")

        row_errors = []

        if not pname.strip():
            row_errors.append(f"Product {idx + 1}: Name required")
        if not qty or qty < 1:
            row_errors.append(f"Product {idx + 1}: Quantity must be at least 1")
        if not price or price <= 0:
            row_errors.append(f"Product {idx + 1}: Price must be greater than 0")
        if disc is None or disc < 0:
            row_errors.append(f"Product {idx + 1}: Invalid discount amount")
        if disc is not None and price and disc >= price:
            row_errors.append(f"Product {idx + 1}: Discount cannot be >= price")

        errors.extend(row_errors)

        if not row_errors:
            order_items_data.append({
                "product_name": pname,
                "quantity": qty,
                "price": price,
                "discount_amount": disc
            })

    if errors:
        st.error("🚨 Fix errors:")
        for e in errors:
            st.write(f"- {e}")
    else:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        short_uuid = str(uuid.uuid4())[:6]
        order_id = f"ORD_{timestamp}_{short_uuid}"

        orders_data = {
            "order_id": order_id,
            "timestamp": timestamp,
            "customer_name": customer_name,
            "age": age,
            "phone": phone,
            "order_source": order_source,
            "payment_method": payment_method
        }

        for item in order_items_data:
            item["item_id"] = f"ITEM_{str(uuid.uuid4())[:6]}"
            item["order_id"] = order_id

        # SAVE TO CSV
        os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

        orders_df      = pd.DataFrame([orders_data])[ORDERS_SCHEMA]
        order_items_df = pd.DataFrame(order_items_data)[ORDER_ITEMS_SCHEMA]

        orders_df.to_csv(
            orders_file,
            mode='a',
            header=not os.path.exists(orders_file),
            index=False
        )
        order_items_df.to_csv(
            order_items_file,
            mode='a',
            header=not os.path.exists(order_items_file),
            index=False
        )

        st.success("✅ Order Submitted & Data Saved!")
        st.info("📁 Data saved to data/orders.csv and data/order_items.csv")

        st.write("### Order Data")
        st.json(orders_data)

        st.write("### Order Items Data")
        st.json(order_items_data)

        # RESET FORM
        st.session_state.products = []
        st.session_state.form_key += 1
        st.session_state.show_success = True
        st.rerun()
