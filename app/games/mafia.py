import random
from dataclasses import dataclass, field
from enum import StrEnum


class MafiaPhase(StrEnum):
    LOBBY = "lobby"
    NIGHT = "night"
    DAY = "day"
    FINISHED = "finished"


@dataclass
class MafiaPlayer:
    user_id: int
    display_name: str
    role: str | None = None
    alive: bool = True


@dataclass
class MafiaState:
    chat_id: int
    min_players: int = 5
    phase: MafiaPhase = MafiaPhase.LOBBY
    players: dict[int, MafiaPlayer] = field(default_factory=dict)
    votes: dict[int, int] = field(default_factory=dict)

    def add_player(self, user_id: int, display_name: str) -> bool:
        if self.phase != MafiaPhase.LOBBY or user_id in self.players:
            return False
        self.players[user_id] = MafiaPlayer(user_id, display_name)
        return True

    def start(self) -> bool:
        if len(self.players) < self.min_players:
            return False
        alive = list(self.players.values())
        mafia_count = max(1, len(alive) // 4)
        random.shuffle(alive)
        for player in alive[:mafia_count]:
            player.role = "mafia"
        if len(alive) > mafia_count:
            alive[mafia_count].role = "doctor"
        if len(alive) > mafia_count + 1:
            alive[mafia_count + 1].role = "detective"
        for player in alive:
            player.role = player.role or "citizen"
        self.phase = MafiaPhase.NIGHT
        return True

    def cast_vote(self, voter_id: int, target_id: int) -> bool:
        if self.phase not in {MafiaPhase.DAY, MafiaPhase.NIGHT}:
            return False
        if voter_id not in self.players or target_id not in self.players:
            return False
        if not self.players[voter_id].alive or not self.players[target_id].alive:
            return False
        self.votes[voter_id] = target_id
        return True

    def resolve_day(self) -> int | None:
        if not self.votes:
            return None
        tally: dict[int, int] = {}
        for target in self.votes.values():
            tally[target] = tally.get(target, 0) + 1
        eliminated = max(tally, key=tally.get)
        self.players[eliminated].alive = False
        self.votes.clear()
        self.phase = MafiaPhase.DAY
        return eliminated

    def winner(self) -> str | None:
        """Return the winner after an elimination, if the game is over."""
        alive = [player for player in self.players.values() if player.alive]
        mafia = sum(player.role == "mafia" for player in alive)
        citizens = len(alive) - mafia
        if mafia == 0:
            return "fuqarolar"
        if mafia >= citizens:
            return "mafia"
        return None

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "min_players": self.min_players,
            "phase": self.phase.value,
            "players": {
                str(user_id): {
                    "user_id": player.user_id,
                    "display_name": player.display_name,
                    "role": player.role,
                    "alive": player.alive,
                }
                for user_id, player in self.players.items()
            },
            "votes": {str(voter): target for voter, target in self.votes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MafiaState":
        state = cls(
            chat_id=int(data["chat_id"]),
            min_players=int(data.get("min_players", 5)),
            phase=MafiaPhase(data.get("phase", MafiaPhase.LOBBY.value)),
        )
        state.players = {
            int(user_id): MafiaPlayer(
                user_id=int(player["user_id"]),
                display_name=player["display_name"],
                role=player.get("role"),
                alive=player.get("alive", True),
            )
            for user_id, player in data.get("players", {}).items()
        }
        state.votes = {int(voter): int(target) for voter, target in data.get("votes", {}).items()}
        return state