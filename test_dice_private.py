import json
from datetime import timedelta
import pytest
from conftest import Fixed, World
from ua_bot.core import Actor
from ua_bot.dice import parse_faces, roll_expression, stat_roll
from ua_bot.rules import GameError


def dm(world, text, user=1, is_dm=True, guilds=(100,)):
    return world.game.private.handle(user, text, is_dm=is_dm, guild_ids=guilds)


def test_arbitrary_numbered_pools_modifiers_and_keep():
    r = roll_expression('2d17 + 1d8 - 3', {}, Fixed(7))
    assert r['total'] == 18
    assert r['groups'][0]['rolls'] == [7, 7]
    assert roll_expression('2d1000000000', {}, Fixed(999999999))['total'] == 1999999998
    assert roll_expression('2d17', {}, Fixed(7), 'high')['total'] == 7
    assert roll_expression('2d1', {}, Fixed(7), 'low')['total'] == 1


def test_custom_weighted_and_text_dice():
    assert parse_faces('[0,1,1,5]') == [0,1,1,5]
    r = roll_expression('2d[weather]', {'weather':['sun','rain','rain','storm']}, Fixed())
    assert r['total'] is None and r['groups'][0]['rolls'] == ['sun','sun']
    assert roll_expression('2d[luck]-1', {'luck':[-3,0,0,10]}, Fixed())['total'] == -7


@pytest.mark.parametrize('expression', ['0d6','101d6','1d0','1d1000000001','d6*2','__import__("os")',
                                          'd6 d8','4','1d[missing]','d6+1000000001'])
def test_invalid_or_unbounded_expressions_rejected(expression):
    with pytest.raises(GameError):
        roll_expression(expression, {}, Fixed())


@pytest.mark.parametrize('faces', ['[]','[true]','[null]','[1.5]','{"a":2}','["'+('a'*41)+'"]'])
def test_invalid_custom_faces_rejected(faces):
    with pytest.raises(GameError):
        parse_faces(faces)


def test_text_modifiers_and_keep_rejected():
    custom = {'weather':['sun']}
    for expression, keep in [('d[weather]+1','all'), ('-d[weather]','all'), ('2d[weather]','high'), ('d6+d8','low')]:
        with pytest.raises(GameError):
            roll_expression(expression, custom, Fixed(), keep)


def test_edge_pressure_cancel_regardless_sources():
    assert stat_roll(10, True, True, Fixed())['mode'] == 'normal'
    assert len(stat_roll(10, True, True, Fixed())['rolls']) == 1
    assert stat_roll(10, True, False, Fixed())['mode'] == 'edge'
    assert stat_roll(10, False, True, Fixed())['mode'] == 'pressure'

