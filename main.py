import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def read_csv(file_name):
    """Read an octopus energy CSV file
    """
    if file_name is not None:
        df = pd.read_csv(file_name)
        df = df.rename(columns={
            "Consumption (kwh)": "Energy used (kWh)",
            " Estimated Cost Inc. Tax (p)": "cost_p",
            " Start": "start",
            " End": "end"
        })
        df["Cost (£)"] = df["cost_p"] / 100.0 
        df["date"] = pd.to_datetime(df["start"], utc=True)
        df["Month"] = df["date"].dt.year.astype("str") + "-" + df["date"].dt.month.astype("str")
        return df.drop(columns="end")

def by_month(df):
    """Return the total energy usage and cost by month
    """
    if df is not None:
        return df.groupby("Month")[["Energy used (kWh)","Cost (£)"]].sum()
    
c = st.container(border=True)
c.header("Upload Octopus Smart Meter Data")
c.write("Download CSV files of smart meter data from the Octopus website, and upload them here.")

cols = c.columns(2)

c = cols[0].container(border=True)
c.subheader("Electricity")
e_file = c.file_uploader("Upload your electricity file.")

c = cols[1].container(border=True)
c.subheader("Gas")
g_file = c.file_uploader("Upload your gas file.")

d = st.container(border=True)
d.header(f"Monthly Usage")

def plot_both(x, b_monthly):

    costs = {
        "Electricity": b_monthly["elec_cost"],
        "Gas":  b_monthly["gas_cost"]
    }

    fig, ax = plt.subplots()
    bottom = np.zeros(len(b_monthly))

    for boolean, weight_count in costs.items():
        p = ax.bar(b_monthly.index, weight_count, label=boolean, bottom=bottom)
        bottom += weight_count

    ax.legend(loc="upper right")
    ax.yaxis.set_major_formatter('£ {x:.2f}')
    
    x.pyplot(fig)

@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode("utf-8")
    
if (e_file is not None) and (g_file is not None):

    e_df = read_csv(e_file)
    g_df = read_csv(g_file)

    e_monthly = by_month(e_df)
    g_monthly = by_month(g_df)

    # Join electricity and gas monthly readings
    left = e_monthly.rename(columns={
        "Cost (£)": "elec_cost",
        "Energy used (kWh)": "elec_kwh",
    })
    right = g_monthly.rename(columns={
        "Cost (£)": "gas_cost",
        "Energy used (kWh)": "gas_kwh",
    })

    b_monthly = left.merge(right,
                           left_index=True,
                           right_index=True,
                           how="outer")

    b_monthly["total_kwh"] = b_monthly["elec_kwh"] + b_monthly["gas_kwh"]
    b_monthly["total_cost"] = b_monthly["elec_cost"] + b_monthly["gas_cost"]

    d.dataframe(b_monthly, column_config={
        "elec_kwh": st.column_config.NumberColumn(
            "Electricity Use", format="%.1f kWh"),
        "elec_cost": st.column_config.NumberColumn(
            "Electricity Cost", format="£ %.2f"),

        "gas_kwh": st.column_config.NumberColumn(
            "Gas Use", format="%.1f kWh"),
        "gas_cost": st.column_config.NumberColumn(
            "Gas Cost", format="£ %.2f"),

        "total_kwh": st.column_config.NumberColumn(
            "Total Use", format="%.1f kWh"),
        "total_cost": st.column_config.NumberColumn(
            "Total Cost", format="£ %.2f"),
        }, use_container_width=True)


    d.download_button(label='📥 Download monthly usage',
                      data=convert_df(e_monthly),
                      file_name= "electricity_monthly.csv")
    plot_both(d, b_monthly)
    
else:

    d.info("Table will be shown when electricity and gas files are uploaded.")
