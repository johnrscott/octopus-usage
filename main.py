import streamlit as st
import pandas as pd

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
        print(df)
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

def show_usage(x, df):
    x.dataframe(df, column_config={
        "Cost (£)": st.column_config.NumberColumn("Cost", format="£ %.2f"),
        "Energy used (kWh)": st.column_config.NumberColumn("Usage", format="%.2f kWh")})
    
if (e_file is not None) and (g_file is not None):

    e_df = read_csv(e_file)
    g_df = read_csv(g_file)

    e_monthly = by_month(e_df)
    g_monthly = by_month(g_df)

    c = d.columns(2)

    x = c[0].container(border=True)
    x.subheader("Electricity usage")
    show_usage(x, e_monthly)
    
    x = c[1].container(border=True)
    x.subheader("Gas usage")
    show_usage(x, g_monthly)
    
    # Join electricity and gas monthly readings
    left = e_monthly.rename(columns={"Cost (£)": "Electricity (£)"})
    right = g_monthly.rename(columns={"Cost (£)": "Gas (£)"})

    b_monthly =left.merge(right,
                          left_index=True,
                          right_index=True,
                          how="outer")

    x = d.container(border=True)
    x.subheader("Total monthly cost over time")
    x.bar_chart(data=b_monthly, y=["Electricity (£)", "Gas (£)"])

else:

    d.info("Table will be shown when electricity and gas files are uploaded.")
