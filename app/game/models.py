import json
import random
from datetime import datetime
from enum import IntEnum

from model_base import db_session, Models, ModelBase
from card.models import Card
from pony.orm import commit, Optional, PrimaryKey, Required, Set


CARDS_PER_PERSON = 4


class GameStatus(IntEnum):
    WAITING = 0
    STARTED = 1
    FINISHED = 2


class Game(Models.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str, unique=True, index=True)
    status = Required(GameStatus, default=GameStatus.WAITING.value)
    password = Optional(str, nullable=True)
    created_at = Required(datetime, default=datetime.utcnow)
    host = Required(int)  # Player_id of the host
    the_thing = Optional(int, nullable=True)  # Player_id of the thing
    chats = Required('Chat')
    cards = Set('Card', nullable=True, lazy=True)
    players = Set('Player')
    min_players = Required(int)
    max_players = Required(int)
    turns = Optional(str, nullable=True)  # Store turns as a JSON string
    deck = Optional(str, nullable=True)
    discard_pile = Optional(str, nullable=True)

    def get_turns(self):
        # Convert the JSON list into a python list
        return json.loads(self.turns) if self.turns else []

    def set_turns(self):
        turns_list = []

        for player in self.players:
            if not player.is_in_game(self.id):
                raise ValueError('Player must be in the game.')
            elif not player.is_alive:
                continue
            turns_list.append(player.id)

        # Shuffle the list
        random.shuffle(turns_list)

        # Get host position and put it last
        host_position = turns_list.index(self.host)
        turns_list.append(turns_list.pop(host_position))

        # Convert the List to JSON List
        json_list = json.dumps(turns_list)
        self.turns = json_list

    def next_turn(self):
        # The first turn goes to the last position and the second turn goes
        # first
        turns_list = self.get_turns()
        turns_list.append(turns_list.pop(0))

        # Convert the List to JSON List
        json_list = json.dumps(turns_list)
        self.turns = json_list

    def check_turn(self, player_id):
        turns = self.get_turns()
        return player_id == turns[0]

    def validate_the_thing_win(self):
        # count alive players in the game with a list comprehension
        alive_players = self.players.filter(is_alive=True, infected=False)
        if alive_players.count() == 1 and alive_players.first().id == self.the_thing:
            self.status = GameStatus.FINISHED.value
            return True
        return False

    def validate_humans_win(self):
        # Check if all but one player are dead
        # count alive players in the game with a list comprehension
        it_player = self.players.filter(id=self.the_thing).first()

        if it_player is None:
            raise ValueError('The thing player not found in the game.')

        if not it_player.is_alive:
            self.status = GameStatus.FINISHED.value
            return True
        return False

    def give_cards_to_users(self):
        player_it = random.randint(0, len(self.players) - 1)
        self.the_thing = player_it

        # We gonna give cards to each player 4 cards then 4 cards...
        # dont have time to think about a better approach.
        # i'm gonna upgrade the algorithm of this function later

        for i, player in enumerate(self.players):
            cards = self.cards.random(CARDS_PER_PERSON)
            if i == player_it:
                cards = list(cards)
                cards[0] = self.cards.select(number=0).first()

            self.cards.remove(cards)

            # This is needed bcs QueryResults are buggy and not documented...
            # https://github.com/ponyorm/pony/issues/369
            cards = list(cards)

            # Remove this after demo
            try:
                torch = ModelBase().get_first_record_by_value(Card,
                    name='Lanzallamas', number=self.max_players)
                if torch is not None:
                    cards[1] = torch
            except Exception:
                pass

            player.add_cards(cards)

    def clean_game(self):
        self.players = []
        self.cards = []
        self.chat = None

    def get_discard_pile(self):
        # JSON list -> Python list
        return json.loads(self.discard_pile) if self.discard_pile else []

    def set_discard_pile(self, new_discarded_card):

        discard_pile_list = self.get_discard_pile()

        discard_pile_list.append(new_discarded_card.id)

        # List -> Json List
        discard_pile_helper = json.dumps(discard_pile_list)
        self.discard_pile = discard_pile_helper

    def get_deck(self):
        # Convert the JSON list into a python list
        return json.loads(self.deck) if self.deck else []

    def set_deck(self, new_card_in_deck):
        # Get actual list
        deck_list = self.get_deck()

        # Get id from new_card
        new_card_in_deck_id = new_card_in_deck.id

        # Insert new element
        deck_list.append(new_card_in_deck_id)

        # Convert the List to JSON List
        deck_helper = json.dumps(deck_list)
        self.deck = deck_helper

    def next_card_in_deck(self):
        # JSON list to List and get first card.
        deck_list = self.get_deck()
        next_card_id = deck_list[0]

        # Retrieve the card in the set
        next_card = self.cards.select(id=next_card_id).first()

        return next_card

    def delete_first_card_in_deck(self):
        # JSON list to List and get first card.
        deck_list = self.get_deck()
        deck_list.pop(0)
        # Convert the List to JSON List
        deck_delete_helper = json.dumps(deck_list)
        self.deck = deck_delete_helper

    def assign_cards_to_game(self):

        amount_of_players = len(self.players)

        with db_session:
            get_cards = Card.select()
            get_cards = list(get_cards)
            for i in range(0, len(get_cards)):
                if get_cards[i].number is not None:
                    helper = False
                    helper = get_cards[i].number <= amount_of_players
                    if helper:
                        self.cards.add(get_cards[i])
        commit()

    def initial_repartition_of_cards(self):
        # This function makes the initial repartition of cards just as intended
        # in real life
        self.assign_cards_to_game()
        all_cards = self.cards
        the_thing_card = self.cards.select(number=0).first()

        # Reparticion inicial
        initial_repartition_amount = len(self.players) * 4 - 1

        # Separar n*4-1 cartas
        initial_deck_shuffle = [card for card in self.cards
                             if card.type not in
                             {0, 2, 3}][:initial_repartition_amount]

        # Mezclar
        random.shuffle(initial_deck_shuffle)

        # Anadir La Cosa a las n*4-1 cartas para hacerlas n*4 cartas.
        initial_deck_shuffle.append(the_thing_card)

        # Mezclar denuevo
        random.shuffle(initial_deck_shuffle)

        # Repartir 4 cartas a cada jugador
        for player in self.players:
            for i in range(0, 4):
                player.cards.add(initial_deck_shuffle[0])
                if initial_deck_shuffle[0].type == 3:
                    self.the_thing = player.id
                initial_deck_shuffle.pop(0)

        # Armar el mazo con las cartas restantes
        # (infectados + sobrantes de tipo 1 Stay Away!)
        infected_cards = [card for card in self.cards if card.type == 2]
        left_over_stayaway_cards = [card for card in all_cards
                             if card not in initial_deck_shuffle and card not in infected_cards and card.type != 0]

        initial_deck = infected_cards + left_over_stayaway_cards

        random.shuffle(initial_deck)

        for card in initial_deck:
            self.set_deck(card)
