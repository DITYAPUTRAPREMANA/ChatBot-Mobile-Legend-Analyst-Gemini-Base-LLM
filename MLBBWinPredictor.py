import json
import numpy as np
from typing import List, Dict, Tuple, Optional

class MLBBWinPredictor:
    """Model untuk memprediksi probabilitas menang berdasarkan komposisi tim."""
    def __init__(self, json_path: str = "mlbb_hero_stats_ALL_Past_7_days.json"):
        """Load data hero statistics dari file JSON."""
        with open(json_path, 'r', encoding='utf-8') as f:
            self.hero_data = json.load(f)

        self.hero_dict = {hero['hero_name'].lower(): hero for hero in self.hero_data}
        self.hero_names = [hero['hero_name'] for hero in self.hero_data]

        self.avg_winrate = np.mean([h['win_rate'] for h in self.hero_data])
        self.avg_pickrate = np.mean([h['pick_rate'] for h in self.hero_data])
        self.avg_banrate = np.mean([h['ban_rate'] for h in self.hero_data])

    def get_hero_stats(self, hero_name: str) -> Optional[Dict]:
        """Ambil statistik hero berdasarkan nama."""
        return self.hero_dict.get(hero_name.lower())

    def calculate_team_score(self, heroes: List[str]) -> Dict:
        """
        Hitung skor tim berdasarkan komposisi hero.

        Args:
            heroes: List nama hero dalam tim (maks 5)

        Returns:
            Dictionary dengan statistik tim
        """
        if not heroes or len(heroes) == 0:
            return {
                'avg_winrate': 0,
                'avg_pickrate': 0,
                'avg_banrate': 0,
                'team_power': 0,
                'synergy_score': 0,
                'meta_relevance': 0
            }

        valid_heroes = []
        stats = []

        for hero_name in heroes:
            hero = self.get_hero_stats(hero_name)
            if hero:
                valid_heroes.append(hero)
                stats.append(hero)

        if not valid_heroes:
            return {
                'avg_winrate': 0,
                'avg_pickrate': 0,
                'avg_banrate': 0,
                'team_power': 0,
                'synergy_score': 0,
                'meta_relevance': 0
            }

        avg_winrate = np.mean([h['win_rate'] for h in valid_heroes])
        avg_pickrate = np.mean([h['pick_rate'] for h in valid_heroes])
        avg_banrate = np.mean([h['ban_rate'] for h in valid_heroes])

        team_power = (avg_winrate * 0.7) + (avg_banrate * 0.3)

        pickrate_variance = np.var([h['pick_rate'] for h in valid_heroes])
        synergy_score = 100 - min(pickrate_variance * 10, 50)

        meta_relevance = (avg_pickrate * 0.4) + (avg_banrate * 0.6)

        return {
            'avg_winrate': round(avg_winrate, 2),
            'avg_pickrate': round(avg_pickrate, 2),
            'avg_banrate': round(avg_banrate, 2),
            'team_power': round(team_power, 2),
            'synergy_score': round(synergy_score, 2),
            'meta_relevance': round(meta_relevance, 2),
            'hero_count': len(valid_heroes)
        }

    def predict_win_probability(self, team1_heroes: List[str], team2_heroes: List[str]) -> Dict:
        """
        Prediksi probabilitas menang untuk kedua tim.

        Args:
            team1_heroes: List nama hero tim 1
            team2_heroes: List nama hero tim 2

        Returns:
            Dictionary dengan probabilitas dan analisis
        """
        team1_stats = self.calculate_team_score(team1_heroes)
        team2_stats = self.calculate_team_score(team2_heroes)

        winrate_diff = team1_stats['avg_winrate'] - team2_stats['avg_winrate']
        winrate_factor = self._sigmoid(winrate_diff / 10) * 50

        power_diff = team1_stats['team_power'] - team2_stats['team_power']
        power_factor = self._sigmoid(power_diff / 10) * 30

        synergy_diff = team1_stats['synergy_score'] - team2_stats['synergy_score']
        synergy_factor = self._sigmoid(synergy_diff / 20) * 10

        meta_diff = team1_stats['meta_relevance'] - team2_stats['meta_relevance']
        meta_factor = self._sigmoid(meta_diff / 5) * 10

        team1_probability = winrate_factor + power_factor + synergy_factor + meta_factor
        team2_probability = 100 - team1_probability

        return {
            'team1': {
                'heroes': team1_heroes,
                'win_probability': round(team1_probability, 2),
                'stats': team1_stats
            },
            'team2': {
                'heroes': team2_heroes,
                'win_probability': round(team2_probability, 2),
                'stats': team2_stats
            },
            'analysis': {
                'winrate_advantage': 'Team 1' if winrate_diff > 0 else 'Team 2',
                'power_advantage': 'Team 1' if power_diff > 0 else 'Team 2',
                'synergy_advantage': 'Team 1' if synergy_diff > 0 else 'Team 2',
                'meta_advantage': 'Team 1' if meta_diff > 0 else 'Team 2',
                'predicted_winner': 'Team 1' if team1_probability > 50 else 'Team 2',
                'confidence': round(abs(team1_probability - 50) * 2, 2)  # 0-100 scale
            }
        }

    def _sigmoid(self, x: float) -> float:
        """Fungsi sigmoid untuk normalisasi."""
        return 1 / (1 + np.exp(-x))

    def get_hero_recommendations(self, opponent_heroes: List[str], top_n: int = 5) -> List[Dict]:
        """
        Rekomendasikan hero untuk counter tim lawan.

        Args:
            opponent_heroes: List hero tim lawan
            top_n: Jumlah rekomendasi yang akan diberikan

        Returns:
            List hero recommendations dengan scoring
        """
        opponent_stats = self.calculate_team_score(opponent_heroes)
        opponent_avg_winrate = opponent_stats['avg_winrate']

        recommendations = []

        for hero in self.hero_data:
            winrate_score = hero['win_rate']
            meta_score = (hero['pick_rate'] * 0.3) + (hero['ban_rate'] * 0.7)

            total_score = (winrate_score * 0.6) + (meta_score * 0.4)

            recommendations.append({
                'hero_name': hero['hero_name'],
                'win_rate': hero['win_rate'],
                'pick_rate': hero['pick_rate'],
                'ban_rate': hero['ban_rate'],
                'recommendation_score': round(total_score, 2)
            })

        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)

        return recommendations[:top_n]

    def format_analysis_for_llm(self, prediction: Dict) -> str:
        """Format prediksi untuk dikirim ke LLM sebagai context."""
        team1 = prediction['team1']
        team2 = prediction['team2']
        analysis = prediction['analysis']

        prompt = f"""Analisis Pertandingan Mobile Legends:

TIM 1:
- Hero: {', '.join(team1['heroes'])}
- Probabilitas Menang: {team1['win_probability']}%
- Rata-rata Winrate: {team1['stats']['avg_winrate']}%
- Team Power: {team1['stats']['team_power']}
- Synergy Score: {team1['stats']['synergy_score']}
- Meta Relevance: {team1['stats']['meta_relevance']}

TIM 2:
- Hero: {', '.join(team2['heroes'])}
- Probabilitas Menang: {team2['win_probability']}%
- Rata-rata Winrate: {team2['stats']['avg_winrate']}%
- Team Power: {team2['stats']['team_power']}
- Synergy Score: {team2['stats']['synergy_score']}
- Meta Relevance: {team2['stats']['meta_relevance']}

ANALISIS:
- Keunggulan Winrate: {analysis['winrate_advantage']}
- Keunggulan Power: {analysis['power_advantage']}
- Keunggulan Synergy: {analysis['synergy_advantage']}
- Keunggulan Meta: {analysis['meta_advantage']}
- Prediksi Pemenang: {analysis['predicted_winner']}
- Confidence Level: {analysis['confidence']}%

Berdasarkan data statistik di atas, berikan analisis mendalam tentang:
1. Kekuatan dan kelemahan masing-masing tim
2. Strategi yang sebaiknya digunakan masing-masing tim
3. Hero mana yang menjadi key player di setiap tim
4. Rekomendasi untuk meningkatkan peluang menang
"""
        return prompt

