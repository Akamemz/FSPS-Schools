# FCPS School Breakfast Program Dashboard

An interactive data dashboard to analyze **Fairfax County Public Schools (FCPS)** breakfast and lunch program metrics — including **costs, food waste, and meal sales** — across schools and regions.

Built with **Streamlit**, **Plotly**, and **Folium**, this dashboard is designed to help school administrators, policymakers, and the public uncover insights and improve the delivery of nutritional programs.

---

## 🚀 Project Overview

This project transforms messy production and sales data into a rich visual analytics experience. From parsing PDFs and HTMLs to interactive maps and charts, the app provides clarity around:

- **Cost per school and menu item**
- **Food waste by item, school, and day**
- **Meal sales volume and trends**
- **Budget vs. actual spending deviations**
- **Regional and geographic patterns**

The goal is to support transparency, efficiency, and equity in the FCPS School Nutrition Program.

---

## 🔧 Data Pipeline

- **PDF Sales Reports** → parsed using `PyPDF2` / `pdfplumber`
- **HTML Production Reports** → scraped using `BeautifulSoup`
- Unified into clean **CSV datasets** for dashboard use
- Data schema designed for easy merging and filtering

> 📊 _Sample visuals and schema available in the `/images` folder._

---

## 📊 Dashboards

### 🏭 Production Dashboard

Focuses on **cost** and **waste** metrics:

- Total and average **meal costs** by school and item
- Waste heatmaps: top wasted foods, costliest schools
- **Deviation** between planned vs. actual spending
- **Cost per student** by region
- **Interactive school maps** with Folium overlays

### 📈 Sales Dashboard

Provides **Exploratory Data Analysis (EDA)** of meal sales across FCPS using:

#### 🧮 Filtering & Aggregation Options:

- By **school**, **meal type**, **day/month**, and **date range**
- By **Free**, **Reduced**, **Full-price**, or **Adult** categories
- Choose **chart types**: stacked/grouped bars

#### 📌 Metrics Calculated:

- Total meals served
- School-level **sales proportion** of system-wide volume
- **Daily variation** (standard deviation) of sales
- Monthly, daily, and weekday trends

#### 📊 Visualization Highlights:

- Most and least active schools in terms of volume
- High vs. low **consistency** in meal demand
- Interactive **top 5 school metrics** and school comparison table
- Export **filtered data** as CSV directly from UI

---

## 🛠️ Tech Stack

- **Streamlit** — front-end and app framework
- **Plotly** — charting and interactive plots
- **Folium** — interactive map layers
- **Pandas, NumPy** — data wrangling
- **PyPDF2, pdfplumber, BeautifulSoup** — PDF/HTML parsing

---

## 📌 Use Cases

- 📍 **FCPS Admins**: monitor and optimize resource usage
- 📈 **Analysts**: detect inefficiencies or overbudget items
- 💡 **Policymakers**: evaluate school nutrition performance
- 🧑‍💻 **Public/Community**: access transparent school data

---

## 📁 Repo Structure

```
.
├── demo/
│   ├── pages/                    # Streamlit multipage app scripts
│   ├── images/                   # Visual assets used in the app
│   ├── About.py                  # Landing/about page
│   ├── FCPS-logo.png             # FCPS branding
│   ├── gw-logo.png               # GWU branding
│   └── requirements.txt          # Project dependencies
├── preprocess/                   # Data transformation and merging scripts
│   ├── html-processing/
│   ├── pdf-processing/
│   └── Readme.md
├── visualization/               # All EDA and plotting scripts
│   ├── cost/
│   ├── sales/
│   └── combined/
├── data/                        # Data storage (raw & processed)
│   ├── FairfaxCounty/
│   ├── preprocessed-data/
│   └── data-downloader.sh
├── README.md
```

---
