from statsnba.resources import StatsNBABoxscore
from events import NBAEvent


class NBATeam(object):
    def __init__(self):
        pass

    def __eq__(self, other_team):
        pass


class NBAPlayer(object):
    STARTER_POSITION = 'starters'
    BENCH_POSITION = 'bench'

    def __init__(self, player_stats):
        self.name = player_stats['PLAYER_NAME']
        self.team_abbr = player_stats['TEAM_ABBREVIATION']
        self.start_position = player_stats['START_POSITION']
        self.id = player_stats['PLAYER_ID']
        self._player_stats = player_stats

    def __getattr__(self, item):
        return self._player_stats[item]

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        return self.name == other.name and self.team_abbr == other.team_abbr

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def __repr__(self):
        return 'NBAPlayer({}, {})'.format(self.name, self.team_abbr)

    def __str__(self):
        return self.name

    @property
    def starter_or_bench(self):
        if self.start_position:
            return 'starters'
        return 'bench'


class NBAGame(object):
    def __init__(self, game_id, loader=None):
        if loader:
            self._loader = loader
        else:
            from statsnba.loaders import WebLoader
            self._loader = WebLoader()
        self.game_id = game_id
        self._boxscore = self._loader.get_boxscore(game_id)
        self._pbp = self._loader.get_playbyplay(game_id)
        self._players = set(map(lambda p: NBAPlayer(player_stats=p), self._boxscore['resultSets']['PlayerStats']))
        self._playbyplay = []

    def __repr__(self):
        return 'NBAGame(game_id={g.game_id}, home_team={g.home_team}, away_team={g.away_team})'.format(g=self)

    @property
    def home_team(self):
        return self._boxscore['resultSets']['TeamStats'][0]['TEAM_ABBREVIATION']

    @property
    def away_team(self):
        return self._boxscore['resultSets']['TeamStats'][1]['TEAM_ABBREVIATION']

    def _select_players(self, team, starter_or_bench):
        selected = []
        for p in self._players:
            if p.team_abbr == getattr(self, team) and p.starter_or_bench == starter_or_bench:
                selected.append(p)
        return set(selected)

    @property
    def home_boxscore(self):
        return self._boxscore['resultSets']['TeamStats'][0]

    @property
    def away_boxscore(self):
        return self._boxscore['resultSets']['TeamStats'][1]

    @property
    def home_starters(self):
        return self._select_players(team='home_team', starter_or_bench='starters')

    @property
    def home_bench(self):
        return self._select_players(team='home_team', starter_or_bench='bench')

    @property
    def away_starters(self):
        return self._select_players(team='away_team', starter_or_bench='starters')

    @property
    def away_bench(self):
        return self._select_players(team='away_team', starter_or_bench='bench')

    @property
    def playbyplay(self):
        if self._playbyplay:
            return self._playbyplay
        """Playbyplay is the collection of events"""
        self._playbyplay = PlayByPlay(self)
        return self._playbyplay

    @property
    def game_length(self):
        from datetime import timedelta
        period = int(self._pbp['resultSets']['PlayByPlay'][-1]['PERIOD'])
        if period > 4:
            return timedelta(minutes=((period-4) * 5 + 12 * 4))
        else:
            return timedelta(minutes=48)

    def find_players_in_range(self, start_range, end_range):
        box = StatsNBABoxscore()
        range_boxscore = box.find_boxscore_in_range(self.game_id, start_range, end_range)
        return set(map(NBAPlayer, range_boxscore['resultSets']['PlayerStats']))

    def _find_player(self, player_name):
        """use player's name and team to find the player"""
        for p in self._players:
            if p.name == player_name:
                return p
        raise Exception('%s is not found in this game' % player_name)


class PlayByPlay(list):
    def __init__(self, game):
        self.game = game
        """Playbyplay is the collection of events"""
        on_court_players = game.home_starters | game.away_starters
        pbp = []
        for i, p in enumerate(game._pbp['resultSets']['PlayByPlay']):
            ev = NBAEvent(i, game=game, on_court_players=on_court_players)
            on_court_players = ev.on_court_players
            pbp.append(ev)
        super(PlayByPlay, self).__init__(pbp)


class PlayByPlayStats(object):
    """Class to compute boxscore stats directly from playbyplay data."""

    def __init__(self, playbyplay):
        """Initialize with a segment of playbyplays, can be a game or a segment of game"""
        self.pbp = playbyplay

    def to_dict(self):
        pass


class NBAMatchup(object):
    def __init__(self, **kargs):
        self.__dict__.update(kargs)

    @classmethod
    def create_matchups(cls, pbps):
        matchups = []
        matchup_num = 1
        start_play_id = end_play_id = pbps[0].play_id
        start_idx = end_idx = 0
        for i, event in enumerate(pbps[1:], start=1):
            end_play_id = event.play_id
            if event.players != pbps[i-1].players:
                matchups.append(dict(start_play_id=start_play_id, end_play_id=end_play_id, matchup_num=matchup_num))
                matchup_num += 1
                start_play_id = pbps[i+1].play_id
            if i == len(pbps) - 1:
                matchups.append(dict(start_play_id=start_play_id, end_play_id=end_play_id, matchup_num=matchup_num))
        return matchups

__all__ = ['NBAEvent', 'NBAGame', 'NBAPlayer', 'NBATeam', 'NBAMatchup']
