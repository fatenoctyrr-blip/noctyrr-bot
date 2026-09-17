from app.games.bunker import BunkerState
from app.games.mafia import MafiaPhase, MafiaState
from app.models import PointEntry
from app.services.contests import choose_random_winner, point_score


def test_mafia_requires_minimum_players():
    state = MafiaState(chat_id=-1, min_players=5)
    for user_id in range(4):
        assert state.add_player(user_id, f"User {user_id}")
    assert not state.start()
    assert state.phase == MafiaPhase.LOBBY


def test_mafia_assigns_core_roles():
    state = MafiaState(chat_id=-1, min_players=5)
    for user_id in range(5):
        state.add_player(user_id, f"User {user_id}")
    assert state.start()
    roles = {player.role for player in state.players.values()}
    assert {"mafia", "doctor", "detective", "citizen"} <= roles


def test_mafia_detects_citizen_win_after_mafia_elimination():
    state = MafiaState(chat_id=-1, min_players=5)
    for user_id in range(5):
        state.add_player(user_id, f"User {user_id}")
    assert state.start()
    mafia_id = next(user_id for user_id, player in state.players.items() if player.role == "mafia")
    state.phase = MafiaPhase.DAY
    for user_id in state.players:
        state.cast_vote(user_id, mafia_id)
    assert state.resolve_day() == mafia_id
    assert state.winner() == "fuqarolar"


def test_bunker_cards_are_generated_and_round_resolves():
    state = BunkerState(chat_id=-1)
    for user_id in range(3):
        state.add_player(user_id, f"User {user_id}")
    assert state.players[0].cards
    for user_id in range(3):
        assert state.vote(user_id, 2)
    assert state.resolve_round() == 2
    assert not state.players[2].active


def test_point_score_uses_admin_weights():
    entry = PointEntry(
        contest_id=1,
        user_id=2,
        reaction_points=2,
        stars_points=1,
        boost_points=3,
        comment_points=4,
        purchased_points=5,
    )
    assert point_score(
        entry,
        {"reaction": 1, "stars": 5, "boost": 2, "comment": 1, "purchased": 10},
    ) == 2 + 5 + 6 + 4 + 50


def test_random_winner_handles_empty_list():
    assert choose_random_winner([]) is None