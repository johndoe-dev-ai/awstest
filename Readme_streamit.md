Great! Here's a complete Streamlit Text-to-SQL sample app with a fixed header and subheader that adjust dynamically with sidebar movement, including reusable styling and scripts.


---

✅ Folder Structure:

text2sql_app/
├── app.py
└── fixed_header.py


---

🔁 fixed_header.py (Reusable Component)

import streamlit as st

def inject_fixed_header(title="Text-to-SQL Assistant", subtitle="Convert natural language to SQL effortlessly"):
    st.markdown(f"""
        <style>
            .fixed-header {{
                position: fixed;
                top: 0;
                left: 250px;
                width: calc(100% - 250px);
                background-color: white;
                padding: 10px 20px;
                z-index: 100;
                border-bottom: 1px solid #eee;
                font-weight: bold;
                font-size: 1.2rem;
                transition: left 0.3s ease, width 0.3s ease;
            }}
            .fixed-subheader {{
                position: fixed;
                top: 50px;
                left: 250px;
                width: calc(100% - 250px);
                background-color: white;
                padding: 5px 20px;
                z-index: 99;
                border-bottom: 1px solid #ccc;
                font-size: 0.9rem;
                transition: left 0.3s ease, width 0.3s ease;
            }}
            .main > div:first-child {{
                margin-top: 100px;
            }}
        </style>

        <div class="fixed-header">🧠 {title}</div>
        <div class="fixed-subheader">{subtitle}</div>
    """, unsafe_allow_html=True)

    # JS to auto-adjust on sidebar resize/toggle
    st.markdown("""
        <script>
        const updateHeader = () => {
            const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
            const header = window.parent.document.querySelector('.fixed-header');
            const subheader = window.parent.document.querySelector('.fixed-subheader');
            if (sidebar && header && subheader) {
                const sidebarWidth = sidebar.offsetWidth + 'px';
                header.style.left = sidebarWidth;
                subheader.style.left = sidebarWidth;
                header.style.width = `calc(100% - ${sidebarWidth})`;
                subheader.style.width = `calc(100% - ${sidebarWidth})`;
            }
        };
        const observer = new MutationObserver(updateHeader);
        const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            observer.observe(sidebar, { attributes: true, childList: true, subtree: true });
        }
        window.addEventListener("resize", updateHeader);
        setTimeout(updateHeader, 1000);
        </script>
    """, unsafe_allow_html=True)


---

🚀 app.py (Main App)

import streamlit as st
from fixed_header import inject_fixed_header

# Inject the fixed header
inject_fixed_header("Text-to-SQL App", "Write your natural language query and get instant SQL!")

# Sidebar
st.sidebar.title("Text-to-SQL Options")
st.sidebar.selectbox("Select Table", ["Orders", "Customers", "Sales"])
st.sidebar.radio("Mode", ["Query", "Logs", "Schema"])

# Main content
st.write("## Main Content Section")
st.write("Use this space for your app UI. Scroll down to test the fixed header.")

# Simulate long content
for i in range(30):
    st.write(f"Line {i+1}: Example output or response from SQL agent.")


---

🧪 How to Run

1. Save both files in a folder named text2sql_app.


2. In terminal or VSCode, navigate to the folder:



cd text2sql_app
streamlit run app.py


---

✅ Output:

Fixed header and subheader at the top.

Sidebar toggle/collapse will dynamically adjust header width and position.

Smooth UI for a production-grade look.


Would you like me to turn this into a Streamlit component or template repo that you can clone and reuse across apps?

