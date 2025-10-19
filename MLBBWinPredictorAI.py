import json
import os
from typing import List, Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

class MLBBWinPredictorAI:
    """Model AI untuk memprediksi probabilitas menang berdasarkan komposisi tim menggunakan Gemini AI."""

    def __init__(self, json_path: str = "Dataset.json", api_key: Optional[str] = None):
        """Load data hero statistics dari file JSON dan inisialisasi AI."""
        with open(json_path, 'r', encoding='utf-8') as f:
            self.hero_data = json.load(f)

        # dictionary untuk akses cepat berdasarkan nama hero
        self.hero_dict = {hero['hero_name'].lower(): hero for hero in self.hero_data}
        self.hero_names = [hero['hero_name'] for hero in self.hero_data]

        # Initialize AI model
        self.api_key = api_key
        self.llm = None

    def initialize_llm(self, api_key: str):
        """Initialize LLM dengan API key."""
        self.api_key = api_key
        os.environ["GOOGLE_API_KEY"] = api_key
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.3
        )

    def get_hero_stats(self, hero_name: str) -> Optional[Dict]:
        """Ambil statistik hero berdasarkan nama."""
        return self.hero_dict.get(hero_name.lower())

    def get_team_stats_summary(self, heroes: List[str]) -> str:
        """
        Buat ringkasan statistik tim dalam format text untuk AI.

        Args:
            heroes: List nama hero dalam tim

        Returns:
            String berisi ringkasan statistik tim
        """
        if not heroes:
            return "Tim tidak memiliki hero."

        valid_heroes = []
        for hero_name in heroes:
            hero = self.get_hero_stats(hero_name)
            if hero:
                valid_heroes.append(hero)

        if not valid_heroes:
            return "Tidak ada hero valid dalam tim."

        summary = f"Tim terdiri dari {len(valid_heroes)} hero:\n"
        for hero in valid_heroes:
            summary += f"- {hero['hero_name']}: Win Rate {hero['win_rate']}%, Pick Rate {hero['pick_rate']}%, Ban Rate {hero['ban_rate']}%\n"

        return summary

    def predict_win_probability_with_ai(self, team1_heroes: List[str], team2_heroes: List[str]) -> Dict:
        """
        Prediksi probabilitas menang menggunakan AI untuk kedua tim.

        Args:
            team1_heroes: List nama hero tim 1
            team2_heroes: List nama hero tim 2

        Returns:
            Dictionary dengan probabilitas dan analisis lengkap dari AI
        """
        if not self.llm:
            raise ValueError("AI model belum diinisialisasi. Gunakan initialize_llm() terlebih dahulu.")

        # Prepare context untuk AI
        team1_summary = self.get_team_stats_summary(team1_heroes)
        team2_summary = self.get_team_stats_summary(team2_heroes)

        # Create comprehensive prompt for AI
        prompt = f"""Sebagai expert analyst Mobile Legends Bang Bang, analisis pertandingan berikut dan berikan prediksi yang akurat.

DATA PERTANDINGAN:

TIM 1 (BIRU):
{team1_summary}

TIM 2 (MERAH):
{team2_summary}

TUGAS ANDA:
Berdasarkan data statistik hero di atas (win rate, pick rate, ban rate), berikan analisis lengkap dalam format JSON berikut:

{{
    "team1_win_probability": <angka 0-100>,
    "team2_win_probability": <angka 0-100>,
    "team1_strengths": ["kekuatan 1", "kekuatan 2", "kekuatan 3"],
    "team1_weaknesses": ["kelemahan 1", "kelemahan 2"],
    "team2_strengths": ["kekuatan 1", "kekuatan 2", "kekuatan 3"],
    "team2_weaknesses": ["kelemahan 1", "kelemahan 2"],
    "predicted_winner": "Team 1" atau "Team 2",
    "confidence_level": <angka 0-100>,
    "team_composition_score": {{
        "team1_score": <angka 0-100>,
        "team2_score": <angka 0-100>
    }}
}}

PETUNJUK ANALISIS:
1. Win Rate tinggi (>54%) = hero sangat kuat
2. Ban Rate tinggi (>20%) = hero meta/feared
3. Pick Rate tinggi (>5%) = hero popular/reliable
4. Pertimbangkan synergy antar hero
5. Pertimbangkan counter matchups
6. Analisis komposisi tim (tank, damage dealer, support, dll)

PENTING: Berikan HANYA output JSON, tanpa teks tambahan apapun. Pastikan JSON valid dan lengkap."""

        try:
            # Get AI response
            response = self.llm.invoke([HumanMessage(content=prompt)])
            ai_response = response.content.strip()

            # Parse JSON response
            if "```json" in ai_response:
                ai_response = ai_response.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_response:
                ai_response = ai_response.split("```")[1].split("```")[0].strip()

            analysis = json.loads(ai_response)

            # Validate and ensure all required fields exist
            required_fields = ["team1_win_probability", "team2_win_probability", "predicted_winner", "confidence_level"]
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")

            # result AI analysis
            result = {
                'team1': {
                    'heroes': team1_heroes,
                    'win_probability': float(analysis['team1_win_probability']),
                    'strengths': analysis.get('team1_strengths', []),
                    'weaknesses': analysis.get('team1_weaknesses', []),
                    'strategy': analysis.get('winning_strategy_team1', ''),
                    'composition_score': analysis.get('team_composition_score', {}).get('team1_score', 0)
                },
                'team2': {
                    'heroes': team2_heroes,
                    'win_probability': float(analysis['team2_win_probability']),
                    'strengths': analysis.get('team2_strengths', []),
                    'weaknesses': analysis.get('team2_weaknesses', []),
                    'strategy': analysis.get('winning_strategy_team2', ''),
                    'composition_score': analysis.get('team_composition_score', {}).get('team2_score', 0)
                },
                'analysis': {
                    'predicted_winner': analysis['predicted_winner'],
                    'confidence': float(analysis['confidence_level']),
                    'raw_ai_response': ai_response
                }
            }

            return result

        except json.JSONDecodeError as e:
            # Fallback: create basic analysis if JSON parsing fails
            return self._create_fallback_analysis(team1_heroes, team2_heroes, str(e))
        except Exception as e:
            raise Exception(f"Error dalam AI prediction: {str(e)}")

    def _create_fallback_analysis(self, team1_heroes: List[str], team2_heroes: List[str], error: str) -> Dict:
        """Create basic analysis jika AI response tidak bisa di-parse."""
        return {
            'team1': {
                'heroes': team1_heroes,
                'win_probability': 50.0,
                'strengths': ['Membutuhkan analisis lebih lanjut'],
                'weaknesses': ['Membutuhkan analisis lebih lanjut'],
                'strategy': 'Fokus pada objektif dan teamwork',
                'composition_score': 50
            },
            'team2': {
                'heroes': team2_heroes,
                'win_probability': 50.0,
                'strengths': ['Membutuhkan analisis lebih lanjut'],
                'weaknesses': ['Membutuhkan analisis lebih lanjut'],
                'strategy': 'Fokus pada objektif dan teamwork',
                'composition_score': 50
            },
            'analysis': {
                'predicted_winner': 'Draw',
                'confidence': 0,
                'key_matchups': ['Analisis tidak tersedia'],
                'game_phases': {},
                'error': error
            }
        }

    def get_hero_recommendations_with_ai(self, opponent_heroes: List[str], top_n: int = 5) -> List[Dict]:
        """
        Rekomendasikan hero untuk counter tim lawan menggunakan AI.

        Args:
            opponent_heroes: List hero tim lawan
            top_n: Jumlah rekomendasi yang akan diberikan

        Returns:
            List hero recommendations dari AI
        """
        if not self.llm:
            raise ValueError("AI model belum diinisialisasi. Gunakan initialize_llm() terlebih dahulu.")

        opponent_summary = self.get_team_stats_summary(opponent_heroes)

        # Create list of all available heroes for context
        all_heroes_summary = "HERO TERSEDIA:\n"
        for hero in self.hero_data[:50]:  # Limit untuk context size
            all_heroes_summary += f"- {hero['hero_name']}: WR {hero['win_rate']}%, PR {hero['pick_rate']}%, BR {hero['ban_rate']}%\n"

        prompt = f"""Sebagai expert analyst Mobile Legends Bang Bang, rekomendasikan {top_n} hero terbaik untuk counter tim lawan.

TIM LAWAN:
{opponent_summary}

{all_heroes_summary}

TUGAS ANDA:
Berikan {top_n} rekomendasi hero terbaik untuk menghadapi tim lawan dalam format JSON:

{{
    "recommendations": [
        {{
            "hero_name": "nama hero",
            "reason": "alasan kenapa hero ini bagus counter",
            "priority": "High/Medium/Low",
            "score": <angka 0-100>
        }}
    ]
}}

KRITERIA REKOMENDASI:
1. Hero yang bisa counter komposisi lawan
2. Hero dengan win rate tinggi
3. Hero meta (ban rate tinggi)
4. Hero dengan synergy baik
5. Hero yang reliable (pick rate)

PENTING: Berikan HANYA output JSON, tanpa teks tambahan."""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            ai_response = response.content.strip()

            # Clean response
            if "```json" in ai_response:
                ai_response = ai_response.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_response:
                ai_response = ai_response.split("```")[1].split("```")[0].strip()

            recommendations_data = json.loads(ai_response)
            recommendations = []

            for rec in recommendations_data.get('recommendations', [])[:top_n]:
                hero_name = rec['hero_name']
                hero_stats = self.get_hero_stats(hero_name)

                if hero_stats:
                    recommendations.append({
                        'hero_name': hero_name,
                        'win_rate': hero_stats['win_rate'],
                        'pick_rate': hero_stats['pick_rate'],
                        'ban_rate': hero_stats['ban_rate'],
                        'ai_reason': rec.get('reason', ''),
                        'priority': rec.get('priority', 'Medium'),
                        'recommendation_score': rec.get('score', 75)
                    })

            return recommendations if recommendations else self._get_fallback_recommendations(top_n)

        except Exception as e:
            # Fallback to top heroes by win rate
            return self._get_fallback_recommendations(top_n)

    def _get_fallback_recommendations(self, top_n: int) -> List[Dict]:
        """Get fallback recommendations based on win rate."""
        sorted_heroes = sorted(self.hero_data, key=lambda x: x['win_rate'], reverse=True)
        recommendations = []

        for hero in sorted_heroes[:top_n]:
            recommendations.append({
                'hero_name': hero['hero_name'],
                'win_rate': hero['win_rate'],
                'pick_rate': hero['pick_rate'],
                'ban_rate': hero['ban_rate'],
                'ai_reason': 'Hero dengan win rate tinggi',
                'priority': 'High',
                'recommendation_score': hero['win_rate']
            })

        return recommendations

    def chat_with_ai(self, question: str, context: Dict) -> str:
        """
        Chat dengan AI tentang strategi dan analisis.

        Args:
            question: Pertanyaan user
            context: Context dari prediction result

        Returns:
            Jawaban dari AI
        """
        if not self.llm:
            raise ValueError("AI model belum diinisialisasi.")

        # Build context
        context_str = f"""
TIM 1: {', '.join(context['team1']['heroes'])}
- Win Probability: {context['team1']['win_probability']}%
- Strengths: {', '.join(context['team1'].get('strengths', []))}
- Weaknesses: {', '.join(context['team1'].get('weaknesses', []))}

TIM 2: {', '.join(context['team2']['heroes'])}
- Win Probability: {context['team2']['win_probability']}%
- Strengths: {', '.join(context['team2'].get('strengths', []))}
- Weaknesses: {', '.join(context['team2'].get('weaknesses', []))}

Predicted Winner: {context['analysis']['predicted_winner']}
"""

        prompt = f"""Kamu adalah expert analyst Mobile Legends Bang Bang.

KONTEKS PERTANDINGAN:
{context_str}

PERTANYAAN USER:
{question}

Jawab pertanyaan dengan detail dan berikan saran praktis berdasarkan data yang ada."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content