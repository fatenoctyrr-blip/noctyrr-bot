import random
from dataclasses import dataclass, field

CHARACTERISTICS = {
    "kasb": ["shifokor", "muhandis", "oshpaz", "o'qituvchi", "dasturchi"],
    "sog'liq": ["a'lo", "yaxshi", "o'rtacha", "surunkali kasallik"],
    "yosh": ["19", "27", "34", "46", "62"],
    "xobbi": ["bog'dorchilik", "ovchilik", "musiqa", "robototexnika", "suzish"],
}


@dataclass
class BunkerPlayer:
    user_id: int
    display_name: str
    cards: dict[str, str] = field(default_factory=dict)
    active: bool = True


@dataclass
class BunkerState:
    chat_id: int
    round_no: int = 0
    players: dict[int, BunkerPlayer] = field(default_factory=dict)
    votes: dict[int, int] = field(default_factory=dict)

    def add_player(self, user_id: int, display_name: str) -> bool:
        if user_id in self.players:
            return False
        cards = {key: random.choice(values) for key, values in CHARACTERISTICS.items()}
        self.players[user_id] = BunkerPlayer(user_id, display_name, cards)
        return True

    def vote(self, voter_id: int, target_id: int) -> bool:
        if voter_id not in self.players or target_id not in self.players:
            return False
        if not self.players[voter_id].active or not self.players[target_id].active:
            return False
        self.votes[voter_id] = target_id
        return True

    def resolve_round(self) -> int | None:
        if not self.votes:
            return None
        tally: dict[int, int] = {}
        for target in self.votes.values():
            tally[target] = tally.get(target, 0) + 1
        removed = max(tally, key=tally.get)
        self.players[removed].active = False
        self.round_no += 1
        self.votes.clear()
        return removed

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "round_no": self.round_no,
            "players": {
                str(user_id): {
                    "user_id": player.user_id,
                    "display_name": player.display_name,
                    "cards": player.cards,
                    "active": player.active,
                }
                for user_id, player in self.players.items()
            },
            "votes": {str(voter): target for voter, target in self.votes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BunkerState":
        state = cls(chat_id=int(data["chat_id"]), round_no=int(data.get("round_no", 0)))
        state.players = {
            int(user_id): BunkerPlayer(
                user_id=int(player["user_id"]),
                display_name=player["display_name"],
                cards=player.get("cards", {}),
                active=player.get("active", True),
            )
            for user_id, player in data.get("players", {}).items()
        }
        state.votes = {int(voter): int(target) for voter, target in data.get("votes", {}).items()}
        return state