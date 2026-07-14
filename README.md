# 📈 QuantX - Multi-Agent Equity Research Analyst

QuantX is an AI-powered multi-agent equity research system that automates company analysis using Large Language Models (LLMs), financial market data, and news intelligence.

The system coordinates multiple specialized AI agents using **LangGraph** to produce comprehensive investment research reports.

---

## 🚀 Features

- 🔍 Web Research Agent
- 📊 Financial Analysis Agent
- 📰 News Intelligence Agent
- 🐂 Bullish Thesis Generation
- 🐻 Bearish Thesis Generation
- 🤖 Multi-Agent Workflow using LangGraph
- 📑 Automated Investment Report Generation

---

## 🏗️ Architecture

```
                User Query
                     │
                     ▼
              Orchestrator Agent
                     │
                     ▼
            Web Research Agent
                     │
                     ▼
          Financial Analysis Agent
                     │
                     ▼
              News Analysis Agent
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
   Bull Analysis Agent     Bear Analysis Agent
         │                       │
         └───────────┬───────────┘
                     ▼
              Final Investment Report
```

---

## 📂 Project Structure

```
quantx/
│
├── agents/
│   ├── orchestrator.py
│   ├── researcher.py
│   ├── financial.py
│   ├── news.py
│   ├── bull.py
│   └── bear.py
│
├── graph.py
├── state.py
├── main.py
│
├── tools/
│
├── requirements.txt
│
└── README.md
```

---

## 🤖 Agents

### 🎯 Orchestrator

Responsible for managing the execution flow between all agents.

---

### 🔍 Web Research Agent

Collects:

- Company overview
- Business model
- Recent developments
- Industry information

---

### 📊 Financial Agent

Fetches financial metrics such as:

- Current Price
- Market Capitalization
- Revenue
- EPS
- P/E Ratio
- Profit Margin
- Beta
- Dividend Yield

---

### 📰 News Agent

Analyzes recent news articles including:

- Headlines
- Summary
- Sentiment
- Market impact

---

### 🐂 Bull Agent

Generates the bullish investment thesis.

Focuses on:

- Growth potential
- Competitive advantage
- Financial strength
- Positive catalysts

---

### 🐻 Bear Agent

Generates the bearish investment thesis.

Focuses on:

- Risks
- Weaknesses
- Valuation concerns
- Market threats

---

## 🛠️ Technologies

- Python
- LangGraph
- LangChain
- Ollama / OpenAI Compatible LLM
- yFinance
- Tavily Search
- News APIs

---

## ⚙️ Installation

```bash
git clone https://github.com/yourusername/quantx.git

cd quantx

pip install -r requirements.txt
```

---

## ▶️ Run

```bash
python main.py
```

---

## 📊 Example Workflow

```
Input

Analyze Apple Inc.

↓

Research Agent

↓

Financial Agent

↓

News Agent

↓

Bull Agent

↓

Bear Agent

↓

Final Analysis
```

---

## 📌 Example Output

```
Company:
Apple Inc.

Financial Summary:
Revenue: ...
EPS: ...
Market Cap: ...

Bull Thesis:
...

Bear Thesis:
...

Investment Summary:
...
```

---

## 🔮 Future Enhancements

- Judge Agent
- Writer Agent
- Critic Agent
- SEC Filing Analysis
- RAG Pipeline
- Streamlit Dashboard
- Live Agent Visualization
- Portfolio Recommendation Engine
- Risk Scoring
- Valuation Models
- PDF Report Generation

---

## 👨‍💻 Author

**Rohan Ajith Shankar**

B.Tech Computer Science (AI & Data Engineering)

Lovely Professional University

Project: QuantX — Multi-Agent Equity Research Analyst