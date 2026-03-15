from flask import Flask, render_template, request, jsonify
import chess
import random

app = Flask(__name__)

# Global board state
board = chess.Board()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move', methods=['POST'])
def move():
    data = request.get_json()
    move_uci = data.get('move')
    mode = data.get('mode', 'pvp') # 'pvp' or 'ai'
    
    try:
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            board.push(move)
            
            # If AI mode is active and it's now Black's turn, make a random move
            ai_move_made = None
            if mode == 'ai' and not board.is_game_over():
                legal_moves = list(board.legal_moves)
                if legal_moves:
                    ai_move_made = random.choice(legal_moves)
                    board.push(ai_move_made)

            return jsonify({
                'fen': board.fen(),
                'turn': 'White' if board.turn == chess.WHITE else 'Black',
                'game_over': board.is_game_over(),
                'status': board.result(),
                'ai_move': ai_move_made.uci() if ai_move_made else None
            })
        else:
            return jsonify({'error': 'Illegal move'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/reset', methods=['POST'])
def reset():
    board.reset()
    return jsonify({'fen': board.fen(), 'turn': 'White'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
