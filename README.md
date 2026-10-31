\# 💸 PaisaFlow



\*\*PaisaFlow\*\* is a personal finance management web application built with Flask and Python. It helps users track expenses, plan budgets, and manage their finances through a simple and user-friendly dashboard.



The goal of PaisaFlow is to make everyday financial management easier by bringing essential money management tools together in one place.



\## ✨ Features



\* \*\*Expense Tracking:\*\* Add and manage daily expenses.

\* \*\*Budget Management:\*\* Set budgets and monitor spending.

\* \*\*Smart Budget Generator:\*\* Plan income using the 50/30/20 budgeting rule.

\* \*\*Financial Calculators:\*\* Calculate EMI, Fixed Deposits (FD), and Recurring Deposits (RD).

\* \*\*Nearby ATM Finder:\*\* Locate nearby ATMs using an interactive map.

\* \*\*Financial Dashboard:\*\* View important financial information in one place.

\* \*\*User Authentication:\*\* Register and log in to a personal account.



\## 🛠️ Technologies Used



\### Backend



\* Python

\* Flask

\* SQLite

\* Google Gemini API



\### Frontend



\* HTML5

\* CSS3

\* JavaScript



\### Maps



\* Leaflet.js

\* OpenStreetMap



\## 🚀 Getting Started



\### 1. Clone the repository



```bash

git clone https://github.com/omprakash9462/PaisaFlow.git

cd PaisaFlow

```



\### 2. Create and activate a virtual environment



```bash

python -m venv env

```



\*\*Windows (Git Bash):\*\*



```bash

source env/Scripts/activate

```



\*\*macOS/Linux:\*\*



```bash

source env/bin/activate

```



\### 3. Install dependencies



```bash

pip install -r requirements.txt

```



\### 4. Configure environment variables



Create a `.env` file in the project root and add your Gemini API key:



```env

GEMINI\_API\_KEY=your\_gemini\_api\_key

```



Replace `your\_gemini\_api\_key` with your own API key.



\### 5. Run the application



```bash

python app.py

```



Open the local URL shown in your terminal, usually `http://127.0.0.1:5000`.



\## 📁 Project Structure



```text

PaisaFlow/

├── app.py

├── templates/

├── static/

├── requirements.txt

├── .env.example

├── .gitignore

└── README.md

```


## 🎯 Project Impact

PaisaFlow aims to make personal financial management more accessible by helping users understand their spending habits, organize their budgets, and make informed financial decisions.

By bringing expense tracking, budgeting, financial calculators, and ATM discovery into one platform, PaisaFlow reduces the need to switch between multiple tools for everyday financial tasks.

## 💡 Benefits

* **Better Expense Awareness:** Helps users track where their money goes.
* **Improved Budget Planning:** Supports structured income allocation through the 50/30/20 budgeting rule.
* **Financial Goal Setting:** Helps users plan savings and manage monthly expenses.
* **Convenience:** Provides multiple personal finance tools through a single dashboard.
* **Accessibility:** Offers a simple interface for users who are new to budgeting and financial planning.
* **Informed Decisions:** Provides financial calculations to help users explore different savings and borrowing scenarios.

## 🔮 Future Integrations

The following features are potential future enhancements and are not currently implemented:

* **AI-Powered Financial Insights:** Personalized spending summaries and budgeting suggestions using transaction history.
* **Expense Categorization:** Automatically classify expenses into categories using machine learning.
* **Recurring Expense Detection:** Identify recurring payments and subscriptions.
* **Savings Goal Tracker:** Set savings targets and monitor progress over time.
* **Interactive Charts:** Add richer visualizations of spending trends and monthly comparisons.
* **Exportable Reports:** Download financial summaries in CSV or PDF format.
* **Banking Integration:** Explore secure integrations with supported financial data providers.
* **Mobile-Friendly Experience:** Further improve the interface for mobile devices.

## 🔐 Security and Privacy

* API keys and other sensitive configuration values should be stored in environment variables.
* The `.env` file and local database are excluded from version control.
* Users should keep their API keys private and avoid sharing credentials.
* Financial information should be handled responsibly and accessed only by authorized users.

## 📌 Disclaimer

PaisaFlow is an educational personal finance project. Its calculators and budgeting tools provide estimates and organizational assistance, not professional financial advice. Users should verify important financial decisions with qualified professionals or relevant financial institutions.




> The `.env` file and local SQLite database are excluded from version control. Create your own `.env` file before running the application.



