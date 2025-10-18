import os
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from MLBBWinPredictorAI import MLBBWinPredictorAI
import json

try:
    from langchain_core.messages import SystemMessage
    HAS_SYSTEM_MESSAGE = True
except ImportError:
    HAS_SYSTEM_MESSAGE = False

st.set_page_config(
    page_title="MLBB Win Predictor AI",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background-color: #f5f7fa;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .hero-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        margin: 5px;
    }
    .winner-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 1.5em;
        font-weight: bold;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎮 MLBB Win Predictor AI")
st.markdown("### Prediksi Probabilitas Menang dengan AI & Statistik Hero")
st.markdown("---")


def initialize_session_state():
    """Inisialisasi session state variables."""
    if "GOOGLE_API_KEY" not in st.session_state:
        st.session_state["GOOGLE_API_KEY"] = ""

    if "predictor" not in st.session_state:
        try:
            st.session_state["predictor"] = MLBBWinPredictorAI()
        except Exception as e:
            st.error(f"Error loading hero data: {str(e)}")
            st.stop()

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    if "prediction_result" not in st.session_state:
        st.session_state["prediction_result"] = None


def get_api_key_input():
    """Input untuk Google API Key."""
    if st.session_state.get("GOOGLE_API_KEY"):
        return True

    st.sidebar.markdown("### 🔑 Setup")
    st.sidebar.info("Masukkan Google API Key untuk mengaktifkan AI Analysis")

    api_key = st.sidebar.text_input(
        "Google API Key",
        type="password",
    )

    if st.sidebar.button("Submit API Key"):
        if api_key:
            st.session_state["GOOGLE_API_KEY"] = api_key
            os.environ["GOOGLE_API_KEY"] = api_key
            # Initialize AI predictor with API key
            if "predictor" in st.session_state:
                st.session_state["predictor"].initialize_llm(api_key)
            st.rerun()
        else:
            st.sidebar.error("API Key tidak boleh kosong!")

    return False


def load_llm():
    """Load LLM Gemini."""
    if "llm" not in st.session_state:
        if st.session_state.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = st.session_state["GOOGLE_API_KEY"]
            try:
                st.session_state["llm"] = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash-exp",
                    temperature=0.7
                )
            except Exception as e:
                st.error(f"Error loading LLM: {str(e)}")
                return None
    return st.session_state.get("llm")


def display_hero_stats(hero_name: str, predictor: MLBBWinPredictorAI):
    """Tampilkan statistik hero individual."""
    hero = predictor.get_hero_stats(hero_name)
    if hero:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Win Rate", f"{hero['win_rate']}%")
        with col2:
            st.metric("Pick Rate", f"{hero['pick_rate']}%")
        with col3:
            st.metric("Ban Rate", f"{hero['ban_rate']}%")


def display_team_stats(team_name: str, team_data: dict):
    """Tampilkan statistik tim dengan analisis AI."""
    st.markdown(f"### {team_name}")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"**Heroes:** {', '.join(team_data['heroes'])}")

        # Display AI-powered analysis
        if 'strengths' in team_data and team_data['strengths']:
            with st.expander("💪 Kekuatan Tim"):
                for strength in team_data['strengths']:
                    st.markdown(f"✅ {strength}")

        if 'weaknesses' in team_data and team_data['weaknesses']:
            with st.expander("⚠️ Kelemahan Tim"):
                for weakness in team_data['weaknesses']:
                    st.markdown(f"❌ {weakness}")

    with col2:
        st.markdown(f"<div class='stat-box'>"
                   f"<h2>{team_data['win_probability']}%</h2>"
                   f"<p>Win Probability (AI)</p>"
                   f"</div>", unsafe_allow_html=True)

        if 'composition_score' in team_data:
            st.metric("Composition Score", f"{team_data['composition_score']}/100")


def main():
    """Main application."""
    initialize_session_state()
    predictor = st.session_state["predictor"]

    # Sidebar
    with st.sidebar:

        has_api_key = get_api_key_input()

        st.markdown("---")
        if st.button("🗑️ Reset Chat", type="secondary"):
            st.session_state["chat_history"] = []
            st.session_state["prediction_result"] = None
            st.rerun()

    # Main content - Tab layout
    tab1, tab2, tab3 = st.tabs(["🎯 Win Predictor", "💬 AI Analysis", "📚 Hero Database"])

    with tab1:
        st.markdown("## Team Composition")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔵 Team 1")
            team1_heroes = st.multiselect(
                "Select Team 1 Heroes (max 5)",
                options=predictor.hero_names,
                max_selections=5,
                key="team1"
            )

        with col2:
            st.markdown("### 🔴 Team 2")
            team2_heroes = st.multiselect(
                "Select Team 2 Heroes (max 5)",
                options=predictor.hero_names,
                max_selections=5,
                key="team2"
            )

        st.markdown("---")

        if st.button("🎲 Predict Win Probability with AI", type="primary", use_container_width=True):
            if not team1_heroes and not team2_heroes:
                st.warning("Please select heroes for at least one team!")
            elif not st.session_state.get("GOOGLE_API_KEY"):
                st.error("⚠️ Please enter your Google API Key in the sidebar first!")
                st.info("AI Prediction membutuhkan API key untuk analisis mendalam")
            else:
                with st.spinner("🤖 AI sedang menganalisis komposisi tim..."):
                    try:
                        # Ensure AI is initialized
                        if not predictor.llm:
                            predictor.initialize_llm(st.session_state["GOOGLE_API_KEY"])

                        prediction = predictor.predict_win_probability_with_ai(team1_heroes, team2_heroes)
                        st.session_state["prediction_result"] = prediction
                        st.success("✅ Analisis AI selesai!")
                    except Exception as e:
                        st.error(f"Error dalam AI prediction: {str(e)}")
                        st.info("Pastikan API key Anda valid dan memiliki kuota")

        # Display prediction results
        if st.session_state.get("prediction_result"):
            prediction = st.session_state["prediction_result"]

            st.markdown("## 📊 Prediction Results")

            # Winner announcement
            winner = prediction['analysis']['predicted_winner']
            confidence = prediction['analysis']['confidence']
            st.markdown(f"<div class='winner-box'>"
                       f"🏆 Predicted Winner: {winner}<br>"
                       f"Confidence: {confidence}%"
                       f"</div>", unsafe_allow_html=True)

            # Team stats
            col1, col2 = st.columns(2)

            with col1:
                display_team_stats("🔵 Team 1", prediction['team1'])

            with col2:
                display_team_stats("🔴 Team 2", prediction['team2'])

            analysis = prediction['analysis']

            # AI-Powered Recommendations
            if team2_heroes:
                st.markdown("---")
                st.markdown("## 💡 AI Hero Recommendations")
                st.markdown("🤖 Top heroes dari AI untuk counter Team 2:")

                with st.spinner("AI sedang menganalisis counter picks..."):
                    try:
                        recommendations = predictor.get_hero_recommendations_with_ai(team2_heroes, top_n=5)

                        for i, hero in enumerate(recommendations, 1):
                            with st.expander(f"{i}. {hero['hero_name']} - {hero.get('priority', 'Medium')} Priority (Score: {hero['recommendation_score']})"):
                                # Stats
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Win Rate", f"{hero['win_rate']}%")
                                with col2:
                                    st.metric("Pick Rate", f"{hero['pick_rate']}%")
                                with col3:
                                    st.metric("Ban Rate", f"{hero['ban_rate']}%")

                                # AI Reasoning
                                if 'ai_reason' in hero and hero['ai_reason']:
                                    st.markdown("**🤖 AI Analysis:**")
                                    st.info(hero['ai_reason'])
                    except Exception as e:
                        st.error(f"Error getting AI recommendations: {str(e)}")

    with tab2:
        st.markdown("## 🤖 AI-Powered Chat & Analysis")

        if not has_api_key:
            st.warning("⚠️ Please enter your Google API Key in the sidebar to use AI Chat")
            st.info("AI Chat membutuhkan API key untuk memberikan analisis dan jawaban")
        else:
            if not st.session_state.get("prediction_result"):
                st.info("👆 Please make a prediction in the 'Win Predictor' tab first!")
            else:

                for message in st.session_state["chat_history"]:
                    if isinstance(message, HumanMessage):
                        with st.chat_message("user"):
                            st.markdown(message.content)
                    elif isinstance(message, AIMessage):
                        with st.chat_message("assistant"):
                            st.markdown(message.content)

                if len(st.session_state["chat_history"]) == 0:
                    if st.button("🚀 Generate Full AI Analysis", type="primary"):
                        with st.spinner("🤖 AI is analyzing the match..."):
                            try:
                                prediction = st.session_state["prediction_result"]
                                question = "Berikan analisis lengkap tentang pertandingan ini, termasuk strategi detail, tips, dan prediksi jalannya permainan."

                                ai_response = predictor.chat_with_ai(question, prediction)

                                st.session_state["chat_history"].append(HumanMessage(content=question))
                                st.session_state["chat_history"].append(AIMessage(content=ai_response))
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                user_question = st.chat_input("Tanyakan apapun tentang strategies, counters, atau team composition...")

                if user_question:
                    st.session_state["chat_history"].append(HumanMessage(content=user_question))

                    with st.spinner("🤖 AI is thinking..."):
                        try:
                            prediction = st.session_state["prediction_result"]
                            ai_response = predictor.chat_with_ai(user_question, prediction)

                            st.session_state["chat_history"].append(AIMessage(content=ai_response))
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

    with tab3:
        st.markdown("## 📚 Hero Statistics Database")

        search_query = st.text_input("🔍 Search Hero", placeholder="Enter hero name...")

        col1, col2 = st.columns([1, 3])
        with col1:
            sort_by = st.selectbox("Sort by:", ["Win Rate", "Pick Rate", "Ban Rate"])

        heroes_to_display = predictor.hero_data.copy()

        if search_query:
            heroes_to_display = [h for h in heroes_to_display
                                if search_query.lower() in h['hero_name'].lower()]

        sort_key = {
            "Win Rate": "win_rate",
            "Pick Rate": "pick_rate",
            "Ban Rate": "ban_rate"
        }[sort_by]

        heroes_to_display.sort(key=lambda x: x[sort_key], reverse=True)

        st.markdown(f"Showing {len(heroes_to_display)} heroes")
        for i in range(0, len(heroes_to_display), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(heroes_to_display):
                    hero = heroes_to_display[i + j]
                    with col:
                        with st.container():
                            st.markdown(f"### {hero['hero_name']}")
                            st.metric("Win Rate", f"{hero['win_rate']}%")
                            st.metric("Pick Rate", f"{hero['pick_rate']}%")
                            st.metric("Ban Rate", f"{hero['ban_rate']}%")
                            st.markdown("---")


if __name__ == "__main__":
    main()