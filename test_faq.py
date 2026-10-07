import asyncio
import json
from conftest import World
import pytest
from ua_bot.client import HeroBot
from ua_bot.commands import SPECS
from ua_bot.core import Actor
from ua_bot.faq import BUILTIN, CATEGORIES, response, search
from ua_bot.rules import GameError
from test_discord import interaction


def test_faq_is_available_before_character_creation_and_read_only(world):
    before=world.state
    result=world.call('faq',2)
    assert 'Choose a category' in result['text'] and 'Combat and teamwork' in result['text']
    assert world.state==before
    assert world.store.db.execute('SELECT count(*) FROM history').fetchone()[0]==0


def test_faq_covers_topics_and_each_id_resolves_to_one_answer():
    assert len({e.key for e in BUILTIN})==len(BUILTIN)
    assert all(e.category in CATEGORIES for e in BUILTIN)
    for entry in BUILTIN:
        assert search(entry.key,'all',{})==[entry]
    assert search('How do I get more energy?','all',{})[0].key=='energy'
    assert search('Can I stack Guard and Shield?','combat',{})[0].key=='guard-shield'
    assert search('what does plus ultra cost','all',{})[0].key=='plus-ultra'
    assert search('dice','rolls',{}) and len(search('dice','all',{}))<=5


def test_category_browsing_and_unknown_questions():
    text=response(category='combat')['text']
    assert 'capture:' in text and 'energy:' not in text
    assert 'has not added' in response(category='campaign')['text']
    result=response('zxyzzqq')
    assert 'no matching' in result['title'] and 'Try a short topic' in result['text']
    with pytest.raises(GameError):
        response(category='unknown')


def test_gm_custom_faq_add_update_delete_and_server_isolation(world):
    with pytest.raises(GameError):
        world.call('faq_add',2,key='session-times',question='When do we play?',answer='Saturday')
    world.call('configure',gm_role_id=900)
    gm=Actor(100,3,(900,))
    world.game.execute(gm,'faq_add',key='session-times',question='When do we play?',answer='Saturday at 6 PM Eastern.')
    result=world.call('faq',2,question='session-times')
    assert 'Saturday at 6 PM Eastern.' in result['text']
    assert 'session-times:' in world.call('faq',2,category='campaign')['text']
    other=world.game.execute(Actor(200,2),'faq',question='session-times')
    assert 'Saturday' not in other['text']
    world.call('faq_add',key='session-times',question='When do we play?',answer='Sunday at 6 PM Eastern.')
    assert len(world.state['faq'])==1 and 'Sunday' in world.call('faq',2,question='session-times')['text']
    world.call('faq_remove',key='session-times')
    assert not world.state['faq']
    with pytest.raises(GameError):
        world.call('faq_remove',key='session-times')


@pytest.mark.parametrize('values',[
    {'key':'energy','question':'Replace a core rule','answer':'Not allowed'},
    {'key':'not a key','question':'Question','answer':'Answer'},
    {'key':'bad-category','question':'Question','answer':'Answer','category':'all'},
    {'key':'empty','question':'Question','answer':''},
    {'key':'long','question':'Question','answer':'x'*2001},
])
def test_custom_faq_validation_rolls_back(world,values):
    before=world.state
    with pytest.raises(GameError):
        world.call('faq_add',**values)
    assert world.state==before


def test_faq_works_during_waiting_roll_and_never_changes_costs(world):
    world.create()
    world.call('check',2,stat='power',method='Lift')
    before=world.state
    assert 'costs 2 Health' in world.call('faq',2,question='plus-ultra')['text']
    assert world.state==before
    with pytest.raises(GameError):
        world.call('faq_add',key='new',question='Question',answer='Answer')


def test_custom_faq_persists_and_old_campaign_without_field_still_works(tmp_path):
    path=tmp_path/'faq.sqlite3'
    w=World(path)
    legacy=w.state
    legacy.pop('faq')
    w.store.save(100,legacy)
    assert 'restore 1 Energy' in w.call('faq',2,question='energy')['text']
    assert 'faq' not in w.state  # A lookup does not silently rewrite old saves.
    w.call('faq_add',key='dorm',question='Which dorm are we in?',answer='East Hall')
    w.store.close()
    again=World(path)
    assert 'East Hall' in again.call('faq',2,question='dorm')['text']
    again.store.close()


def test_public_faq_contains_no_private_controls(world):
    public=''.join(e.question+e.answer+e.tags for e in BUILTIN)
    assert 'rigger' not in public.lower()
    world.game.private.handle(1,'!Rigger next any 8',is_dm=True,guild_ids=[100])
    before=world.store.db.execute('SELECT remaining FROM rig_rules').fetchone()[0]
    assert 'no matching' in world.call('faq',2,question='Rigger')['title']
    assert world.store.db.execute('SELECT remaining FROM rig_rules').fetchone()[0]==before
    assert 'rig_rules' not in json.dumps(world.call('faq',2))


def test_faq_private_default_public_opt_in_and_autocomplete(world):
    async def run():
        bot=HeroBot(world.game)
        spec=next(s for s in SPECS if s.path=='faq')
        private=interaction(request=888)
        await bot.run_spec(private,spec,{'question':'energy','category':'all','share':False})
        private.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        assert 'restore 1 Energy' in private.edit_original_response.call_args.kwargs['content']
        shared=interaction(request=889)
        await bot.run_spec(shared,spec,{'question':'energy','category':'all','share':True})
        shared.response.defer.assert_awaited_once_with(ephemeral=False, thinking=True)
        assert 'restore 1 Energy' in shared.edit_original_response.call_args.kwargs['content']
        world.call('faq_add',key='classroom',question='Where is our classroom?',answer='Room 202')
        suggested=await bot.faq_autocomplete(interaction(),'classroom')
        assert suggested[0].value=='classroom'
        assert len(await bot.faq_autocomplete(interaction(),''))<=25
        assert all(len(c.name)<=100 and len(c.value)<=100 for c in suggested)
        await bot.close()
    asyncio.run(run())
