from datetime import datetime, timezone
import pytest
from ua_bot.core import Actor
from ua_bot.engine import Game
from ua_bot.storage import Store

GUILD = 100
OWNER = Actor(GUILD,1)


class Fixed:
    def __init__(self,value=5):
        self.value = value
    def randint(self,low,high):
        return max(low,min(self.value,high))
    def choice(self,values):
        return values[0]


class World:
    def __init__(self,path=':memory:'):
        self.now = datetime(2026,10,5,16,tzinfo=timezone.utc)
        self.store = Store(path)
        self.game = Game(self.store,1,rng=Fixed(5),clock=lambda:self.now)
    def call(self,operation,actor=1,**kw):
        return self.game.execute(Actor(GUILD,actor),operation,**kw)
    @property
    def state(self):
        return self.store.load(GUILD)
    def h(self,user=2):
        return self.state['characters'][str(user)]
    def create(self,user=2,moves=('heavy_hit','rescue_boost'),talent='heavy_hitter',reach='ranged'):
        self.call('hero_create',user,name=f'Student {user}',hero_name=f'Hero {user}',age=19,goal='Rescue people',cooperation='Support classmates')
        self.call('hero_quirk',user,name='Ice',ability='Create ice',ordinary='Ramps and attacks',reach=reach,cannot='Control weather',limits='Heat gives Pressure')
        self.call('hero_moves',user,first=moves[0],second=moves[1])
        self.call('hero_talent',user,talent=talent)
        self.call('hero_submit',user)
        self.call('approve',user=user)
    def battle(self,users=(2,3),enemy='rival',trait='none'):
        self.call('battle_create',name='Rescue',participants=','.join(map(str,users)),starting_zone='street')
        self.call('zone_add',name='lobby',connect_to='street')
        self.call('zone_add',name='roof',connect_to='lobby')
        self.call('enemy_add',name='Bruiser',template=enemy,zone='street',trait=trait)
        self.call('enemy_intent',enemy='e1',intention='Attack the heroes for announced damage.')
        self.call('battle_start')
    def end_heroes(self,users=(2,3)):
        for u in users:
            b=self.state['battle']
            if str(u) not in b['acted']:
                self.call('battle_skip',user=u,reason='Test round setup')
        self.call('battle_phase',phase='enemies')


@pytest.fixture
def world():
    w = World()
    yield w
    w.store.close()
