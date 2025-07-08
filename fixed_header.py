import streamlit as st

def inject_fixed_header(title="Text-to-SQL Assistant", subtitle="Convert natural language to SQL effortlessly"):
    st.markdown(f"""
        <style>
            .fixed-header {{
                position: fixed;
                top: 0;
                background-color: white;
                padding: 10px 20px;
                z-index: 100;
                border-bottom: 1px solid #eee;
                font-weight: bold;
                font-size: 1.2rem;
            }}
            .fixed-subheader {{
                position: fixed;
                top: 50px;
                background-color: white;
                padding: 5px 20px;
                z-index: 99;
                border-bottom: 1px solid #ccc;
                font-size: 0.9rem;
            }}
            .main > div:first-child {{
                margin-top: 100px;
            }}
        </style>

        <div class="fixed-header" id="custom-header">🧠 {title}</div>
        <div class="fixed-subheader" id="custom-subheader">{subtitle}</div>

        <script>
        function updateHeaderPosition() {{
            const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
            const header = window.parent.document.getElementById("custom-header");
            const subheader = window.parent.document.getElementById("custom-subheader");

            if (sidebar && header && subheader) {{
                const sidebarWidth = sidebar.offsetWidth;
                header.style.left = sidebarWidth + 'px';
                subheader.style.left = sidebarWidth + 'px';
                header.style.width = 'calc(100% - ' + sidebarWidth + 'px)';
                subheader.style.width = 'calc(100% - ' + sidebarWidth + 'px)';
            }}
        }}

        const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        const observer = new MutationObserver(updateHeaderPosition);
        if (sidebar) {{
            observer.observe(sidebar, {{ attributes: true, childList: true, subtree: true }});
        }}
        window.addEventListener("resize", updateHeaderPosition);
        setTimeout(updateHeaderPosition, 500);
        </script>
    """, unsafe_allow_html=True)
