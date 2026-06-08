import os
import base64
import streamlit as st
import re
import uuid
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials

IST = ZoneInfo("Asia/Kolkata")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_TOKEN = "rhd-login-2024"
LOGIN_ENABLED = False  # True karo jab login chahiye

SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_sheets():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["gsheets"]["sheet_id"])
    return spreadsheet.worksheet("orders"), spreadsheet.worksheet("order_items")


def get_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# -----------------------------
# AUTH
# -----------------------------
def show_login():
    _, col, _ = st.columns([1, 1, 1])
    with col:
        logo_b64 = get_image_base64(os.path.join(BASE_DIR, "logo", "Raza Herbal Dawakhana 3.png"))
        st.markdown(
            f"<div style='text-align:center'><img src='data:image/png;base64,{logo_b64}' width='130'/><h2>Raza Herbal Shifakhana</h2></div>",
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("🔐 Login"):
            valid_user = st.secrets["auth"]["username"]
            valid_pass = st.secrets["auth"]["password"]
            if username == valid_user and password == valid_pass:
                st.query_params["auth"] = AUTH_TOKEN
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

if LOGIN_ENABLED and st.query_params.get("auth") != AUTH_TOKEN:
    st.set_page_config(page_title="Raza Herbal Shifakhana", layout="centered")
    show_login()
    st.stop()
else:
    st.set_page_config(page_title="Raza Herbal Shifakhana", layout="wide")

logo_b64 = get_image_base64(os.path.join(BASE_DIR, "logo", "Raza Herbal Dawakhana 3.png"))
st.markdown(
    f"""
    <div style='display:flex; align-items:center; gap:12px; margin-top:-34px; margin-bottom:4px'>
        <img src='data:image/png;base64,{logo_b64}' width='50'/>
        <span style='font-size:25px; font-weight:600; line-height:1'>Raza Herbal Shifakhana</span>
    </div>
    """,
    unsafe_allow_html=True
)
st.divider()

st.subheader("🧾 Customer Order Entry")

st.components.v1.html(
    """
    <script>
    setTimeout(() => {
        const doc = window.parent.document;

        function getInputs() {
            return Array.from(doc.querySelectorAll('input[type="text"], input[type="number"]'));
        }

        function getSelectboxes() {
            return Array.from(doc.querySelectorAll('[data-baseweb="select"]'));
        }

        // Phone field numeric keypad
        setTimeout(() => {
            const inputs = getInputs();
            if (inputs.length > 2) {
                inputs[2].setAttribute('inputmode', 'numeric');
            }
        }, 600);

        // Select all on focus for number inputs
        doc.addEventListener('focus', function(e) {
            if (e.target.tagName === 'INPUT' && e.target.type === 'number') {
                e.target.select();
            }
        }, true);

        doc.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter') return;

            const active = doc.activeElement;
            const inputs = getInputs();
            const idx = inputs.indexOf(active);

            // Customer Name (0) -> Age (1)
            // Age (1) -> Phone (2)
            if (idx === 0 || idx === 1) {
                e.preventDefault();
                inputs[idx + 1].focus();
                return;
            }

            // Phone (2) -> Order Source dropdown
            if (idx === 2) {
                e.preventDefault();
                const selects = getSelectboxes();
                if (selects.length > 0) {
                    const inp = selects[0].querySelector('input');
                    if (inp) { inp.focus(); inp.click(); }
                    else selects[0].click();
                }
                return;
            }

            // Product fields: Name, Qty, Price, Discount -> next field or next product
            if (idx >= 3) {
                e.preventDefault();
                if (idx + 1 < inputs.length) {
                    inputs[idx + 1].focus();
                } else {
                    active.blur();
                    window.parent.document.querySelector('[data-testid="stAppViewContainer"]').scrollTo({top: 999999, behavior: 'smooth'});
                }
                return;
            }
        }, true);

        // Order Source select -> Payment Method dropdown
        let waitingForPayment = false;
        doc.addEventListener('click', function(e) {
            const option = e.target.closest('[role="option"]');
            if (!option) return;

            if (!waitingForPayment) {
                waitingForPayment = true;
                setTimeout(() => {
                    const freshSelects = getSelectboxes();
                    if (freshSelects.length > 1) {
                        const inp = freshSelects[1].querySelector('input');
                        if (inp) { inp.focus(); inp.click(); }
                        else freshSelects[1].click();
                    }
                }, 300);
            } else {
                waitingForPayment = false;
            }
        }, true);

    }, 500);
    </script>
    """,
    height=0
)

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
    age = st.number_input("Age", min_value=1, step=1, value=18, key=f"age_{st.session_state.form_key}")

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

to_remove = None

for pid in st.session_state.products:
    idx = st.session_state.products.index(pid)
    st.subheader(f"Product {idx + 1}")

    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

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

    remove_label = f"❌ Remove {pname.title() if pname.strip() else f'Product {idx + 1}'}"
    st.markdown("<div style='margin-top:2px'>", unsafe_allow_html=True)
    if st.button(remove_label, key=f"remove_{pid}", use_container_width=True):
        to_remove = pid
    st.markdown("</div>", unsafe_allow_html=True)

if to_remove:
    st.session_state.products.remove(to_remove)
    st.rerun()

if st.session_state.get("scroll_to_bottom"):
    st.session_state["scroll_to_bottom"] = False
    st.components.v1.html(
        """
        <script>
            window.parent.document.querySelector('[data-testid="stAppViewContainer"]').scrollTo({top: 999999, behavior: 'smooth'});
            setTimeout(() => {
                const inputs = window.parent.document.querySelectorAll('input[type="text"]');
                if (inputs.length > 0) inputs[inputs.length - 1].focus();
            }, 500);
        </script>
        """,
        height=0
    )

if st.button("➕ Add Product", use_container_width=True):
    st.session_state.products.append(str(uuid.uuid4()))
    st.session_state["scroll_to_bottom"] = True
    st.rerun()

# SUBMIT
if st.button("✅ Submit Order", use_container_width=True):

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
        timestamp = datetime.now(IST).strftime("%Y%m%d%H%M%S")
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
            header=not os.path.exists(orders_file) or os.path.getsize(orders_file) == 0,
            index=False
        )
        order_items_df.to_csv(
            order_items_file,
            mode='a',
            header=not os.path.exists(order_items_file) or os.path.getsize(order_items_file) == 0,
            index=False
        )

        try:
            ws_orders, ws_items = get_sheets()
            if ws_orders.row_count == 0 or ws_orders.cell(1, 1).value is None:
                ws_orders.append_row(ORDERS_SCHEMA)
            if ws_items.row_count == 0 or ws_items.cell(1, 1).value is None:
                ws_items.append_row(ORDER_ITEMS_SCHEMA)
            ws_orders.append_row([str(v) for v in orders_df.iloc[0]])
            for _, row in order_items_df.iterrows():
                ws_items.append_row([str(v) for v in row])
        except Exception as e:
            st.warning(f"⚠️ Sheets save failed: {e}")

        st.success("✅ Order Submitted & Data Saved!")
        st.info("📁 Data saved to CSV and Google Sheets")

        st.write("### Order Data")
        st.json(orders_data)

        st.write("### Order Items Data")
        st.json(order_items_data)

        # RESET FORM
        st.session_state.products = []
        st.session_state.form_key += 1
        st.session_state.show_success = True
        st.rerun()
