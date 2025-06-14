from flask import Flask, render_template, jsonify, request
import random
import time



app = Flask(__name__, template_folder='templates_game')

# Funkcja do wczytania pytan z pliku
def load_questions_from_file(filename):
    questions = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                # Zakladajac, ze kazda linia w pliku to jedno pytanie w formacie JSON
                text, points = line.strip().split(';')  # Format: "text;punkty"
                questions.append({"text": text.strip(), "points": int(points.strip())})
    except FileNotFoundError:
        print(f"Plik {filename} nie zostal znaleziony.")
    except Exception as e:
        print(f"Wystapil blad podczas wczytywania pytan: {e}")
    return questions

# Domyslne identyfikatory druzyn
team_ids = ['team1', 'team2', 'team3', 'team4']
question_pool = {}

for team in team_ids:
    filename = f'templates_game/question_pool_{team}.txt'
    question_pool[team] = load_questions_from_file(filename)
	
team_questions = {team: [] for team in team_ids}
team_names = {team: team.upper() for team in team_ids}
team_scores = {team: 0 for team in team_ids}
wrong_questions = {team: [] for team in team_ids}
question_start_time = {}  # klucz: team, wartosc: timestamp (float)

# Przydziel losowe pytania
def assign_initial_questions():
    global question_pool, team_questions
    for team in team_ids:
        if len(question_pool[team]) >= 1:
            q = random.choice(question_pool[team])
            team_questions[team].append(q)
            question_pool[team].remove(q)

assign_initial_questions()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_questions')
def get_questions():
    return jsonify({
        'questions': team_questions,
        'names': team_names
    })

@app.route('/next_question/<team>', methods=['POST'])
def next_question(team):
    # Upewniamy sie, ze druzyna istnieje i ma jeszcze pytania w swojej puli
    if team not in question_pool or not question_pool[team]:
        # Sprawdzenie, czy wszystkie druzyny wyczerpaly swoje pytania (opcjonalne)
        all_answered = all(len(pool) == 0 for pool in question_pool.values())
        return jsonify({'question': None, 'finished': all_answered})

    # Przydziel pytanie z indywidualnej puli
    next_q = random.choice(question_pool[team])
    question_pool[team].remove(next_q)
    team_questions[team].append(next_q)

    question_start_time[team] = time()  # Zapisujemy moment przydzielenia pytania
	
    return jsonify({'question': next_q, 'finished': False})


@app.route('/set_team_names', methods=['POST'])
def set_team_names():
    data = request.json
    for team_id, name in data.items():
        if team_id in team_names:
            team_names[team_id] = name.strip() or team_id.upper()
    return jsonify({"status": "ok", "names": team_names})

@app.route('/game_results')
def game_results():
    results = {}
    for team in team_scores:
        results[team] = {
            "score": team_scores[team],
            "wrong_questions": wrong_questions.get(team, []),
			"teamName": team_names.get(team, team.upper())
        }
    return jsonify(results)

@app.route('/correct_answer/<team>', methods=['POST'])
def correct_answer(team):
    if team in team_questions and team in team_scores:
        last_question = team_questions[team][-1] if team_questions[team] else None
        if last_question:
            team_scores[team] += last_question.get("points", 0)
        return jsonify({"status": "ok", "new_score": team_scores[team]})
    return jsonify({"status": "error"}), 400

@app.route('/answer/<team>', methods=['POST'])
def answer(team):
    data = request.json
    correct = data.get("correct", False)

    # Oblicz czas odpowiedzi
    from time import time
    now = time()
    start = question_start_time.get(team)
    time_taken = now - start if start else None

    last_question = team_questions[team][-1] if team_questions[team] else None

    if correct:
        if last_question:
            team_scores[team] += last_question.get("points", 0)

        # Dodaj bonus 2 pkt, jesli odpowiedz < 120 sekund
        if time_taken is not None and time_taken < 120:
            team_scores[team] += 2
			
    else:
        if last_question and last_question not in wrong_questions[team]:
            wrong_questions[team].append(last_question)

    # Przydziel kolejne pytanie i zresetuj timer
    if question_pool.get(team):
        next_q = random.choice(question_pool[team])
        question_pool[team].remove(next_q)
        team_questions[team].append(next_q)
        question_start_time[team] = time()
        return jsonify({'question': next_q, 'finished': False})
    else:
        return jsonify({'question': None, 'finished': True})


@app.route('/wrong_questions')
def get_wrong_questions():
    return jsonify(wrong_questions)


if __name__ == '__main__':
    app.run(debug=True)

