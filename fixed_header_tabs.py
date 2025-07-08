import streamlit as st

def inject_fixed_header_with_tabs(app_title="Clearwater Post Trade Data Bot", subtitle="Your AI Assistant for Market Post Trade Data Analytics"):
    st.markdown(f"""
        <style>
            #fixed-header-container {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                background-color: white;
                z-index: 999;
                padding: 15px 20px 0 20px;
                border-bottom: 1px solid #eee;
            }}

            #fixed-header-title {{
                font-size: 1.5rem;
                font-weight: bold;
                color: #3f51b5;
            }}

            #fixed-header-subtitle {{
                font-size: 0.9rem;
                color: #555;
                margin-top: -5px;
            }}

            .main > div:first-child {{
                margin-top: 130px;  /* Add margin to avoid overlap */
            }}
        </style>

        <div id="fixed-header-container">
            <div id="fixed-header-title">🤖 {app_title}</div>
            <div id="fixed-header-subtitle">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)

    # JavaScript to observe sidebar changes (optional)
    st.markdown("""
    <script>
    // Make header responsive if sidebar toggles
    function adjustHeaderMargin() {
        const header = window.parent.document.getElementById("fixed-header-container");
        const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar && header) {
            const sidebarWidth = sidebar.offsetWidth;
            header.style.left = sidebarWidth + "px";
            header.style.width = `calc(100% - ${sidebarWidth}px)`;
        }
    }

    const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
    if (sidebar) {
        const observer = new MutationObserver(adjustHeaderMargin);
        observer.observe(sidebar, { attributes: true, childList: true, subtree: true });
    }
    window.addEventListener("resize", adjustHeaderMargin);
    setTimeout(adjustHeaderMargin, 1000);
    </script>
    """, unsafe_allow_html=True)
