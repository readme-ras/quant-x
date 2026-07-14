from graph import graph


state = {
    "company": "Apple",
    "ticker": "AAPL",

    "research": "",
    "financial_data": {},
    "news": [],

    "bull_report": "",
    "bear_report": "",

    "final_report": ""
}


result = graph.invoke(state)

print("\nResearch")
print(result["research"])

print("\nFinancials")
print(result["financial_data"])

print("\nNews")
print(result["news"])

print("\nBull Report")
print(result["bull_report"])

print("\nBear Report")
print(result["bear_report"])