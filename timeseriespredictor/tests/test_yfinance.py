import yfinance as yf
dat = yf.Ticker("NQ=F")
print(dat.history(end="2024-12-31", start="2024-12-21"))


