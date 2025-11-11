import pandas as pd
import numpy as np
import random
from faker import Faker
from datetime import datetime, timedelta

print("--- Starting to generate 10,000 rows of data... ---")

# --- 1. SETUP ---
# Initialize the Faker library
fake = Faker()

# Set the number of rows
NUM_ROWS = 10000

# --- 2. DEFINE LISTS FOR CATEGORIES ---
regions = ['North America', 'Europe', 'Asia-Pacific', 'South America', 'Africa']
segments = ['Consumer', 'Corporate', 'Home Office', 'Small Business']
shipping_modes = ['Same Day', 'First Class', 'Standard Class', 'Second Class']
product_categories = ['Technology', 'Office Supplies', 'Furniture']

sub_categories = {
    'Technology': ['Phones', 'Laptops', 'Accessories', 'Copiers'],
    'Office Supplies': ['Paper', 'Binders', 'Labels', 'Storage', 'Art'],
    'Furniture': ['Chairs', 'Tables', 'Bookcases', 'Furnishings']
}

# --- 3. GENERATE THE DATA ---
data = []
for i in range(1, NUM_ROWS + 1):
    # Order Info
    order_id = f"ORD-{2024 + random.randint(-2, 0)}-{100000 + i}"
    order_date = fake.date_time_between(start_date='-3y', end_date='now')
    
    # Customer Info
    customer_id = f"CUS-{1000 + random.randint(1, 5000)}"
    customer_name = fake.name()
    customer_email = fake.email()
    customer_age = random.randint(18, 70)
    segment = random.choice(segments)
    
    # Location Info
    country = fake.country()
    region = random.choice(regions)

    # Product Info
    category = random.choice(product_categories)
    sub_category = random.choice(sub_categories[category])
    product_id = f"PROD-{category[:3].upper()}-{random.randint(100, 999)}"
    product_name = f"{sub_category} Model {random.choice(['X', 'Pro', 'Basic', 'Plus'])}"
    
    # Sales & Profit Info
    quantity = random.randint(1, 10)
    # Give a base price
    base_price = random.uniform(20.0, 1000.0)
    # Make discounts more realistic (mostly 0)
    discount = random.choices([0.0, 0.1, 0.15, 0.2, 0.5], weights=[0.6, 0.1, 0.1, 0.1, 0.1], k=1)[0]
    
    sales = (base_price * quantity) * (1 - discount)
    # Make profit a function of sales
    profit = sales * random.uniform(-0.1, 0.3) # Some items can have a loss
    
    # Shipping
    shipping_mode = random.choice(shipping_modes)

    # Add all 18 columns to our data list
    data.append([
        order_id, order_date, customer_id, customer_name, customer_email,
        customer_age, segment, country, region, product_id, category,
        sub_category, product_name, sales, quantity, discount, profit, shipping_mode
    ])

# --- 4. CREATE PANDAS DATAFRAME ---
# Define the column names
columns = [
    'OrderID', 'OrderDate', 'CustomerID', 'CustomerName', 'CustomerEmail',
    'CustomerAge', 'CustomerSegment', 'Country', 'Region', 'ProductID', 'Category',
    'SubCategory', 'ProductName', 'Sales', 'Quantity', 'Discount', 'Profit', 'ShippingMode'
]

df = pd.DataFrame(data, columns=columns)

# --- 5. SAVE TO CSV ---
file_name = 'sample_sales_data.csv'
df.to_csv(file_name, index=False)

print(f"--- SUCCESS! ---")
print(f"Created file: {file_name} with {len(df)} rows.")