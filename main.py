import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import locale
locale.setlocale(locale.LC_ALL, "en_GB.UTF-8")

def money(value: float | None, decimals=True) -> str | None:
    if value is None:
        return None
    if decimals:
        return locale.currency(value, grouping=True)
    else:
        return locale.currency(value, grouping=True)[:-3]

def read_csv(file_name, prefix):
    """Read an octopus energy CSV file
    """
    if file_name is not None:
        df = pd.read_csv(file_name)
        df = df.rename(columns={
            "Consumption (kwh)": f"{prefix}_kwh",
            " Estimated Cost Inc. Tax (p)": "cost_p",
            " Start": "start",
            " End": "end"
        })
        df[f"{prefix}_cost"] = df["cost_p"] / 100.0 
        df["date"] = pd.to_datetime(df["start"], utc=True)
        # year = df["date"].dt.year.astype("str")
        # month = df["date"].dt.month.astype("str")
        # df["month"] =  year + "-" + month
        return df.drop(columns=["start", "end", "cost_p"])

c = st.container(border=True)
c.header("Upload Octopus Smart Meter Data")
c.write("Download you Octopus energy smart meter data and upload it below.")
c.info("To download the data, log on to your Octopus online account, and follow these steps:\n\n 1. Go into `Menu`, then click `My Bills` followed by `My Energy`, and look for `Get your energy geek on` (or something similar).\n2. Set the date range as large as possible, and download data for both electricity and gas (separately).\n3. Rename the files to make it clearer which is which (by default, the files both get called `download.csv`)")

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

    # Read the data into tables
    e_df = read_csv(e_file, "elec")
    g_df = read_csv(g_file, "gas")

    # Join the data together to get the raw input
    df = e_df.merge(g_df, how="outer", on="date")
    
    # Get the monthly (calendar month) usage data
    month = df["date"].dt.month.astype(str)
    year = df["date"].dt.year.astype(str)
    df["month"] = year + "-" + month
    df_months = df.groupby("month")[["elec_kwh","elec_cost","gas_kwh", "gas_cost"]].sum()
    df_months["total_kwh"] = df_months["elec_kwh"] + df_months["gas_kwh"]
    df_months["total_cost"] = df_months["elec_cost"] + df_months["gas_cost"]
    df_months.index.name = "Month"
    
    d.dataframe(df_months, column_config={
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
                      data=convert_df(df_months),
                      file_name= "electricity_monthly.csv")
    plot_both(d, df_months)

    d = st.container(border=True)
    d.header(f"Billing Information")

    d.write("Input the date of the first initial balance. This is also the date that defines the billing period (from this day of the month, to one minus this day the next month)")
    billing_start_date = d.date_input("Initial balance start date")

    d.write("Input the balance on this date")
    starting_balance = d.number_input("Initial balance", format="%.2f")

    billing_period_start_day = billing_start_date.day

    if billing_period_start_day == 1:
        st.error("In the current implementation, it is not possible to have the billing period start on the first day of the month")

    billing_period_end_day = billing_period_start_day - 1
    
    d.info(f"From the information above, your initial balance was {money(starting_balance)} on {billing_start_date}. This defines a billing period from day {billing_period_start_day} of one month to day {billing_period_end_day} of the next month. This period will be referred to using the label 'year-month-{billing_period_start_day}'")

    d.write("Input the direct debit monthly payment")
    direct_debit= d.number_input("Direct debit", 100.0, format="%.2f")

    d.info(f"The day the direct debit is paid does not matter. It is assumed that one direct debit payment of {money(direct_debit)} is made during each billing period. During each billing period,\n\n **New Balance = Previous Balance + Direct Debit - Total Cost**.\n\nThe result is positive when the account is in credit.")
    
    # Remove data before the billing period start
    print(df["date"])
    df_filter = df[df["date"].dt.date >= billing_start_date]

    # Offset the date by the billing start date and group by months  
    offset_date = df_filter["date"].sub(pd.DateOffset(billing_period_start_day - 1))
    year = offset_date.dt.year.astype(str)
    month = offset_date.dt.month.astype(str)

    billing_period_name = year + "-" + month + "-" + str(billing_period_start_day)
    df_filter["billing_period"] = billing_period_name
    df_billing = df_filter.groupby("billing_period")[["elec_kwh","elec_cost","gas_kwh", "gas_cost"]].sum()

    # Add the direct debit as a constant amount in each billing period
    df_billing["direct_debit"] = direct_debit
    df_billing["direct_debit_cum"] = df_billing["direct_debit"].cumsum()
    df_billing["total_cost"] = df_billing["elec_cost"] + df_billing["gas_cost"]
    df_billing["total_kwh"] = df_billing["elec_kwh"] + df_billing["gas_kwh"]
    df_billing["total_cost_cum"] = df_billing["total_cost"].cumsum()
    df_billing["end_balance"] = starting_balance + df_billing["direct_debit_cum"] - df_billing["total_cost_cum"]
    df_billing["start_balance"] = df_billing["end_balance"].shift(1,fill_value=starting_balance)

    # Only keep columns of interest
    df_billing_reduced = df_billing.drop(columns=[
        "direct_debit_cum", "total_cost_cum"
    ])

    df_billing_reduced.index.name = "Period"
    
    # Group into billing periods
    num_format = "£ %.2f"
    kwh_format = "%.1f kWh"
    column_config = {
        "total_cost": st.column_config.NumberColumn("Total Cost",
                                                    format=num_format),
        "start_balance": st.column_config.NumberColumn("Previous Balance",
                                                    format=num_format),
        "direct_debit": st.column_config.NumberColumn("Direct Debit",
                                                    format=num_format),
        "end_balance": st.column_config.NumberColumn("New Balance",
                                          format=num_format),
        "elec_kwh": st.column_config.NumberColumn("Electricity Use",
                                                  format=kwh_format),
        "elec_cost": st.column_config.NumberColumn("Electricity Cost",
                                                   format=num_format),
        "gas_kwh": st.column_config.NumberColumn("Gas Use",
                                                 format=kwh_format),
        "gas_cost": st.column_config.NumberColumn("Gas Cost",
                                                  format=num_format),
        "total_kwh": st.column_config.NumberColumn("Total Use",
                                                   format=kwh_format),
    }
    d.dataframe(df_billing_reduced, column_config=column_config, column_order=column_config.keys(), use_container_width=True)
    
else:

    d.info("Table will be shown when electricity and gas files are uploaded.")
