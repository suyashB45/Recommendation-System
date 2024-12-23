import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Streamlit app title
st.title("Stock Analysis and Recommendations")

# Sidebar for user input
st.sidebar.header("Stock Name")

# Input for stock symbols
symbols = st.sidebar.text_input(
    "Enter Stock Symbols (comma-separated):",
    placeholder="Enter your stock "
)

# Input for budget
budget = st.sidebar.number_input(
    "Enter your budget (Rs):",
    min_value=1.0,
    value=1000.0,
    step=1.0
)

# Button to fetch stock data
if st.sidebar.button("Fetch Stock Data"):
    if not symbols:
        st.warning("Please enter at least one stock symbol.")
    else:
        stock_list = [symbol.strip().upper() for symbol in symbols.split(",")]

        # Display stock descriptions and additional info
        st.subheader("Stock Information and Descriptions")
        stock_details = []

        for stock in stock_list:
            try:
                ticker = yf.Ticker(stock)
                info = ticker.info
                description = info.get("longBusinessSummary", "Description not available")
                market_cap = info.get("marketCap", "N/A")
                current_price = info.get("currentPrice", "N/A")
                stock_pe = info.get("trailingPE", "N/A")
                book_value = info.get("bookValue", "N/A")
                dividend_yield = info.get("dividendYield", "N/A")
                roce = info.get("returnOnEquity", "N/A")
                roe = info.get("returnOnAssets", "N/A")
                face_value = info.get("regularMarketPrice", "N/A")

                # Append stock details
                stock_details.append({
                    "Stock": stock,
                    "Market Cap (Rs)": market_cap,
                    "Current Price (Rs)": current_price,
                    "Stock P/E": stock_pe,
                    "Book Value": book_value,
                    "Dividend Yield (%)": dividend_yield * 100 if dividend_yield != "N/A" else "N/A",
                    "ROCE (%)": roce * 100 if roce != "N/A" else "N/A",
                    "ROE (%)": roe * 100 if roe != "N/A" else "N/A",
                    "Face Value (Rs)": face_value,
                    "Description": description
                })

            except Exception:
                st.warning(f"Details for {stock} could not be retrieved.")

        # Convert to DataFrame for display and add sequential numbering
        stock_details_df = pd.DataFrame(stock_details,index=range(1, len(stock_details) + 1))
        st.write(stock_details_df)

        # Fetch stock data for analysis
        try:
            stock_data = yf.download(stock_list, period="1mo", interval="1d")

            if 'Close' not in stock_data.columns:
                st.error("Unable to fetch closing price data. Please check the stock symbols.")
            else:
                table_data = []
                recommendation_counts = {"Buy": 0, "Sell": 0, "Hold": 0}

                for stock in stock_list:
                    if stock not in stock_data['Close'].columns:
                        st.warning(f"Data for {stock} is unavailable. Skipping...")
                        continue

                    prices = stock_data['Close'][stock]
                    if prices.isnull().all():
                        st.warning(f"No price data available for {stock}. Skipping...")
                        continue

                    # Extracting required data
                    latest_price = prices.iloc[-1]
                    opening_price = stock_data['Open'][stock].iloc[-1]
                    max_price = stock_data['High'][stock].max()
                    min_price = stock_data['Low'][stock].min()

                    # Calculate moving averages
                    sma_20 = prices.rolling(window=20).mean()
                    sma_50 = prices.rolling(window=50).mean()

                    # Determine buy/sell/hold signals
                    buy_signals = (sma_20 > sma_50) & (sma_20.shift() <= sma_50.shift())
                    sell_signals = (sma_20 < sma_50) & (sma_20.shift() >= sma_50.shift())

                    if buy_signals.iloc[-1]:
                        recommendation = "Buy"
                        reason = "Short-term moving average (SMA 20) crossed above long-term moving average (SMA 50)."
                    elif sell_signals.iloc[-1]:
                        recommendation = "Sell"
                        reason = "Short-term moving average (SMA 20) crossed below long-term moving average (SMA 50)."
                    else:
                        recommendation = "Hold"
                        reason = "No significant crossover in moving averages to suggest a Buy or Sell action."

                    # Update recommendation counts
                    recommendation_counts[recommendation] += 1

                    # Calculate quantity that can be bought
                    qty_to_buy = int(budget // latest_price)

                    # Append data for table
                    table_data.append({
                        "Stock": stock,
                        "Open (Rs)": round(opening_price, 2),
                        "Close (Rs)": round(latest_price, 2),
                        "Max (Rs)": round(max_price, 2),
                        "Min (Rs)": round(min_price, 2),
                        "Recommendation": recommendation,
                        "Reason": reason,
                        "Qty to Buy": qty_to_buy
                    })

                    # Plot stock price and moving averages
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=prices.index, y=prices,
                        mode='lines', name='Price'
                    ))
                    fig.add_trace(go.Scatter(
                        x=sma_20.index, y=sma_20,
                        mode='lines', name='SMA 20'
                    ))
                    fig.add_trace(go.Scatter(
                        x=sma_50.index, y=sma_50,
                        mode='lines', name='SMA 50'
                    ))

                    fig.add_trace(go.Scatter(
                        x=prices.index[buy_signals],
                        y=prices[buy_signals],
                        mode='markers', name='Buy Signal',
                        marker=dict(color='green', size=10, symbol='triangle-up')
                    ))
                    fig.add_trace(go.Scatter(
                        x=prices.index[sell_signals],
                        y=prices[sell_signals],
                        mode='markers', name='Sell Signal',
                        marker=dict(color='red', size=10, symbol='triangle-down')
                    ))

                    fig.update_layout(
                        title=f"{stock} Price and Moving Averages",
                        xaxis_title="Date",
                        yaxis_title="Price (Rs)"
                    )

                    st.plotly_chart(fig)

                # Prepare the table data with sequential numbering
                table_data_df = pd.DataFrame(table_data,range(1,len(table_data)+1))
                # Display recommendations and distribution
                st.subheader("Stock Performance and Recommendations")
                # Display table below the charts
                st.write(table_data_df)

                # Two pie charts (Buy/Sell & Stocks Distribution) above the table
                col1, col2 = st.columns(2)
                with col1:
                    fig_pie_recommendation = px.pie(
                        names=list(recommendation_counts.keys()),
                        values=list(recommendation_counts.values()),
                        title="Recommendation Distribution",
                        labels={"value": "Count", "names": "Recommendation"}
                    )
                    st.plotly_chart(fig_pie_recommendation)

                with col2:
                    fig_pie_stock = px.pie(
                        names=table_data_df['Stock'],
                        values=table_data_df['Qty to Buy'],
                        title="Stock Quantity Distribution",
                        labels={"value": "Quantity", "names": "Stock"}
                    )
                    st.plotly_chart(fig_pie_stock)

        except Exception as e:
            st.error(f"An error occurred while fetching stock data: {e}")